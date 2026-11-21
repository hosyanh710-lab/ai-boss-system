"""Đẩy file lên Google Drive của từng công ty (mỗi công ty một tài khoản Google riêng).

Quyền xin: drive.file — công cụ CHỈ thấy và sửa file do chính nó tạo, không đọc được file khác trên Drive.
Kèm openid + email để biết đang đăng nhập email nào, chống đẩy nhầm sang Drive của công ty khác.

Cần một OAuth client loại "Web application" tạo trên Google Cloud Console, với
Authorized redirect URI: http://127.0.0.1:5000/google/callback
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
SCOPES = "openid email https://www.googleapis.com/auth/drive.file"
FOLDER_MIME = "application/vnd.google-apps.folder"
TIMEOUT = 60

http = requests.Session()


class DriveError(Exception):
    pass


def _check(r: requests.Response, viec: str) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400:
        err = data.get("error")
        msg = err.get("message") if isinstance(err, dict) else data.get("error_description") or err
        raise DriveError(f"{viec} thất bại ({r.status_code}): {msg or r.text[:200]}")
    return data


def auth_url(client_id: str, redirect_uri: str, state: str, login_hint: str | None) -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": SCOPES,
         "access_type": "offline", "prompt": "consent select_account", "state": state,
         "include_granted_scopes": "false"}
    if login_hint:
        q["login_hint"] = login_hint
    return AUTH_URL + "?" + urlencode(q)


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    r = http.post(TOKEN_URL, data={"code": code, "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": redirect_uri, "grant_type": "authorization_code"},
                  timeout=TIMEOUT)
    return _check(r, "Lấy quyền Google")


def access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    r = http.post(TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret,
                                   "refresh_token": refresh_token, "grant_type": "refresh_token"},
                  timeout=TIMEOUT)
    return _check(r, "Làm mới quyền Google")["access_token"]


def email_of(token: str) -> str:
    r = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    email = _check(r, "Đọc email tài khoản Google").get("email")
    if not email:
        raise DriveError("Google không trả về email của tài khoản")
    return email.lower()


def revoke(refresh_token: str) -> None:
    try:
        http.post(REVOKE_URL, data={"token": refresh_token}, timeout=TIMEOUT)
    except requests.RequestException:
        pass


def _find(token: str, name: str, parent: str | None, folder: bool) -> str | None:
    esc = name.replace("\\", "\\\\").replace("'", "\\'")
    q = [f"name = '{esc}'", "trashed = false",
         f"mimeType {'=' if folder else '!='} '{FOLDER_MIME}'"]
    q.append(f"'{parent}' in parents" if parent else "'root' in parents")
    r = http.get(FILES_URL, params={"q": " and ".join(q), "fields": "files(id,name)", "spaces": "drive"},
                 headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    files = _check(r, "Tìm thư mục trên Drive").get("files", [])
    return files[0]["id"] if files else None


def ensure_folder(token: str, name: str, parent: str | None = None) -> str:
    fid = _find(token, name, parent, folder=True)
    if fid:
        return fid
    meta = {"name": name, "mimeType": FOLDER_MIME}
    if parent:
        meta["parents"] = [parent]
    r = http.post(FILES_URL, params={"fields": "id"}, json=meta,
                  headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    return _check(r, "Tạo thư mục trên Drive")["id"]


def upload(token: str, name: str, parent: str, content: bytes, mime: str) -> str:
    """Tải file lên thư mục; nếu đã có file cùng tên (do công cụ tạo) thì ghi đè nội dung."""
    fid = _find(token, name, parent, folder=False)
    boundary = "thuedn-boundary-7f3a"
    meta = {"name": name} if fid else {"name": name, "parents": [parent]}
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: {mime}\r\n\r\n").encode() + content + f"\r\n--{boundary}--".encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": f"multipart/related; boundary={boundary}"}
    if fid:
        r = http.patch(f"{UPLOAD_URL}/{fid}", params={"uploadType": "multipart", "fields": "id"},
                       data=body, headers=headers, timeout=TIMEOUT)
    else:
        r = http.post(UPLOAD_URL, params={"uploadType": "multipart", "fields": "id"},
                      data=body, headers=headers, timeout=TIMEOUT)
    return _check(r, f"Tải {name} lên Drive")["id"]
