"""Kết nối cổng hoadondientu.gdt.gov.vn.

Cổng KHÔNG có API công khai. Các địa chỉ dưới đây là địa chỉ mà chính trang web
của cổng gọi khi tra cứu (xem bằng F12 → Network trên trình duyệt). Nếu cổng đổi,
chỉ cần sửa trong file này.

Đối chiếu với mã trang hoadondientu.gdt.gov.vn ngày 22/11/2026: cổng đã bỏ cổng :30000,
mọi địa chỉ nay nằm dưới https://hoadondientu.gdt.gov.vn/api/...
- Tra cứu "query" = hóa đơn điện tử thường. "sco-query" = hóa đơn khởi tạo từ máy tính tiền:
  trang web đòi nhập captcha riêng cho MỖI lần tìm kiếm nên công cụ chưa tải loại này.
- Mua vào: trang bắt buộc chọn "Kết quả kiểm tra" (ttxly) là 5, 6 hoặc 8.
- Trang gửi kèm header End-Point (đường dẫn trang) và Action (tên thao tác); gửi y như vậy.
"""
from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Iterator
from urllib.parse import quote

import requests

try:  # dùng kho chứng chỉ của Windows / macOS (cần khi có phần mềm diệt virus quét HTTPS, ví dụ Avast)
    import truststore
    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover
    pass

log = logging.getLogger("thuedn.portal")

BASE = "https://hoadondientu.gdt.gov.vn/api"
URL_CAPTCHA = BASE + "/captcha"
URL_LOGIN = BASE + "/security-taxpayer/authenticate"
URL_SOLD = BASE + "/query/invoices/sold"
URL_PURCHASE = BASE + "/query/invoices/purchase"
URL_XML = BASE + "/query/invoices/export-xml"
END_POINT = "/tra-cuu/tra-cuu-hoa-don"

# Hóa đơn mua vào phải tra theo từng "Kết quả kiểm tra" (ttxly):
# 5 = đã cấp mã, 6 = CQT đã nhận không mã, 8 = CQT đã nhận hóa đơn có mã khởi tạo từ máy tính tiền
PURCHASE_TTXLY = (5, 6, 8)
PAGE_SIZE = 50
TIMEOUT = 60
# Cổng trả 429 "Too Many Requests" khi gọi khoảng 3 lần/giây (đo ngày 22/11/2026):
# giãn mỗi lần gọi tối thiểu KHOANG_CACH giây, gặp 429 thì chờ rồi thử lại.
KHOANG_CACH = 1.2
CHO_KHI_429 = (5, 15, 30, 60)


class PortalError(Exception):
    pass


@dataclass
class Captcha:
    key: str
    svg: str

    @property
    def data_uri(self) -> str:
        return "data:image/svg+xml;base64," + base64.b64encode(self.svg.encode("utf-8")).decode()


class PortalSession:
    def __init__(self, verify_ssl: bool = True):
        self.http = requests.Session()
        self.http.headers["User-Agent"] = "Mozilla/5.0"
        self.verify = verify_ssl
        self.token: str | None = None
        self._lan_goi_cuoi = 0.0

    @property
    def logged_in(self) -> bool:
        return self.token is not None

    def _send(self, method: str, url: str, action: str = "", **kw) -> requests.Response:
        for lan, cho in enumerate((*CHO_KHI_429, None)):
            con_lai = self._lan_goi_cuoi + KHOANG_CACH - time.monotonic()
            if con_lai > 0:
                time.sleep(con_lai)
            headers = {"request-id": str(uuid.uuid4()), "End-Point": END_POINT, "Action": quote(action)}
            try:
                r = self.http.request(method, url, headers=headers, timeout=TIMEOUT, verify=self.verify, **kw)
            except requests.RequestException as e:
                log.warning("%s %s -> lỗi mạng: %s", method, url, e)
                raise PortalError(f"Không kết nối được cổng thuế: {e}") from e
            finally:
                self._lan_goi_cuoi = time.monotonic()
            # Chỉ ghi địa chỉ, tham số tra cứu và mã trả về; không ghi mật khẩu, captcha, token.
            log.info("%s %s %s -> %s", method, url, kw.get("params") or "", r.status_code)
            if r.status_code == 429 and cho is not None:
                cho = _so_giay(r.headers.get("Retry-After"), cho)
                log.info("  cổng báo gọi quá nhanh, chờ %s giây rồi thử lại (lần %s)", cho, lan + 1)
                time.sleep(cho)
                continue
            if r.status_code >= 400:
                log.info("  nội dung trả về: %s", r.text[:300])
            return r
        return r

    def get_captcha(self) -> Captcha:
        r = self._send("GET", URL_CAPTCHA)
        if r.status_code != 200:
            raise PortalError(f"Không lấy được captcha (mã {r.status_code})")
        data = _json(r)
        if "key" not in data or "content" not in data:
            raise PortalError(f"Captcha trả về không đúng dạng: {r.text[:100]}")
        return Captcha(key=data["key"], svg=data["content"])

    def login(self, mst: str, password: str, captcha_key: str, captcha_value: str) -> None:
        r = self._send(
            "POST", URL_LOGIN, action="Đăng nhập",
            json={"username": mst, "password": password, "cvalue": captcha_value, "ckey": captcha_key},
        )
        data = _json(r)
        token = data.get("token")
        if r.status_code != 200 or not token:
            raise PortalError(data.get("message") or f"Đăng nhập thất bại (mã {r.status_code})")
        self.token = token
        self.http.headers["Authorization"] = f"Bearer {token}"
        self.http.headers["Accept-Language"] = "vi"

    # ---- tra cứu ----
    def _query(self, url: str, search: str, action: str) -> Iterator[dict]:
        state = None
        while True:
            params = {"sort": "tdlap:desc", "size": PAGE_SIZE, "search": search}
            if state:
                params["state"] = state
            r = self._send("GET", url, action=action, params=params)
            if r.status_code == 401:
                self.token = None
                raise PortalError("Phiên đăng nhập hết hạn, cần nhập lại captcha")
            data = _json(r)
            if r.status_code != 200:
                raise PortalError(data.get("message") or f"Lỗi tra cứu (mã {r.status_code})")
            rows = data.get("datas") or []
            log.info("  %s hóa đơn (tổng %s)", len(rows), data.get("total"))
            yield from rows
            state = data.get("state")
            if not rows or not state:
                break

    @staticmethod
    def _search(tu: date, den: date, extra: str = "") -> str:
        s = f"tdlap=ge={tu:%d/%m/%Y}T00:00:00;tdlap=le={den:%d/%m/%Y}T23:59:59"
        return s + (f";{extra}" if extra else "")

    def sold(self, tu: date, den: date) -> Iterator[dict]:
        yield from self._query(URL_SOLD, self._search(tu, den), "Tìm kiếm (hóa đơn bán ra)")

    def purchase(self, tu: date, den: date) -> Iterator[dict]:
        for ttxly in PURCHASE_TTXLY:
            yield from self._query(URL_PURCHASE, self._search(tu, den, f"ttxly=={ttxly}"),
                                   "Tìm kiếm (hóa đơn mua vào)")

    def export_xml(self, inv: dict) -> bytes:
        """Trả về file .zip cổng thuế cung cấp cho một hóa đơn (chứa XML)."""
        params = {k: inv[k] for k in ("nbmst", "khhdon", "shdon", "khmshdon")}
        r = self._send("GET", URL_XML, action="Xuất xml", params=params)
        if r.status_code != 200 or not r.content.startswith(b"PK"):
            log.warning("  XML %s-%s không phải file zip: %s", inv.get("khhdon"), inv.get("shdon"), r.content[:150])
            raise PortalError(f"Không tải được XML hóa đơn {inv.get('khhdon')}-{inv.get('shdon')}")
        return r.content


def _so_giay(retry_after: str | None, mac_dinh: float) -> float:
    try:
        return min(max(float(retry_after), 1), 120) if retry_after else mac_dinh
    except ValueError:
        return mac_dinh


def _json(r: requests.Response) -> dict:
    try:
        data = r.json()
        return data if isinstance(data, dict) else {"datas": data}
    except ValueError:
        return {"message": r.text[:200]}


def normalize(row: dict) -> dict:
    """Chuyển một dòng cổng thuế trả về thành dữ liệu lưu trong máy."""
    from .rules import parse_portal_date

    return {
        "nbmst": row.get("nbmst"),
        "nbten": row.get("nbten"),
        "nmmst": row.get("nmmst"),
        "nmten": row.get("nmten"),
        "khmshdon": row.get("khmshdon"),
        "khhdon": row.get("khhdon"),
        "shdon": row.get("shdon"),
        "tdlap": parse_portal_date(row.get("tdlap")),
        "tgtcthue": row.get("tgtcthue"),
        "tgtthue": row.get("tgtthue"),
        "tgtttbso": row.get("tgtttbso"),
        "tthai": row.get("tthai"),
        # Hóa đơn gốc bị điều chỉnh / thay thế. Tên trường theo danh sách cổng thuế trả về;
        # CẦN KIỂM TRA với dữ liệu thật. File XML (TTHDLQuan) sẽ ghi đè nếu tải XML.
        "goc_khmshdon": _first(row, "khmshdgoc", "khmshdongoc"),
        "goc_khhdon": _first(row, "khhdgoc", "khhdongoc"),
        "goc_shdon": _first(row, "shdgoc", "shdongoc"),
        "goc_tdlap": parse_portal_date(_first(row, "tdlhdgoc", "tdlapgoc")),
        "raw": row,
    }


def _first(row: dict, *keys):
    for k in keys:
        if row.get(k) not in (None, ""):
            return row[k]
    return None
