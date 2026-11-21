"""Kết nối cổng hoadondientu.gdt.gov.vn.

Cổng KHÔNG có API công khai. Các địa chỉ dưới đây là địa chỉ mà chính trang web
của cổng gọi khi tra cứu (xem bằng F12 → Network trên trình duyệt). Nếu cổng đổi,
chỉ cần sửa trong file này.

CẦN KIỂM TRA TRÊN MÁY ANH: các địa chỉ và tham số chưa được chạy thử với cổng thật.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
from typing import Iterator

import requests

BASE = "https://hoadondientu.gdt.gov.vn:30000"
URL_CAPTCHA = BASE + "/captcha"
URL_LOGIN = BASE + "/security-taxpayer/authenticate"
URL_SOLD = BASE + "/query/invoices/sold"
URL_PURCHASE = BASE + "/query/invoices/purchase"
URL_XML = BASE + "/query/invoices/export-xml"

# Hóa đơn mua vào phải tra theo từng trạng thái xử lý:
# 5 = đã cấp mã, 6 = CQT đã nhận không mã, 8 = từ máy tính tiền
PURCHASE_TTXLY = (5, 6, 8)
PAGE_SIZE = 50
TIMEOUT = 60


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

    @property
    def logged_in(self) -> bool:
        return self.token is not None

    def get_captcha(self) -> Captcha:
        r = self.http.get(URL_CAPTCHA, timeout=TIMEOUT, verify=self.verify)
        r.raise_for_status()
        data = r.json()
        return Captcha(key=data["key"], svg=data["content"])

    def login(self, mst: str, password: str, captcha_key: str, captcha_value: str) -> None:
        r = self.http.post(
            URL_LOGIN,
            json={"username": mst, "password": password, "cvalue": captcha_value, "ckey": captcha_key},
            timeout=TIMEOUT, verify=self.verify,
        )
        data = _json(r)
        token = data.get("token")
        if r.status_code != 200 or not token:
            raise PortalError(data.get("message") or f"Đăng nhập thất bại (mã {r.status_code})")
        self.token = token
        self.http.headers["Authorization"] = f"Bearer {token}"

    # ---- tra cứu ----
    def _query(self, url: str, search: str) -> Iterator[dict]:
        state = None
        while True:
            params = {"sort": "tdlap:desc", "size": PAGE_SIZE, "search": search}
            if state:
                params["state"] = state
            r = self.http.get(url, params=params, timeout=TIMEOUT, verify=self.verify)
            if r.status_code == 401:
                self.token = None
                raise PortalError("Phiên đăng nhập hết hạn, cần nhập lại captcha")
            data = _json(r)
            if r.status_code != 200:
                raise PortalError(data.get("message") or f"Lỗi tra cứu (mã {r.status_code})")
            rows = data.get("datas") or []
            yield from rows
            state = data.get("state")
            if not rows or not state:
                break

    @staticmethod
    def _search(tu: date, den: date, extra: str = "") -> str:
        s = f"tdlap=ge={tu:%d/%m/%Y}T00:00:00;tdlap=le={den:%d/%m/%Y}T23:59:59"
        return s + (f";{extra}" if extra else "")

    def sold(self, tu: date, den: date) -> Iterator[dict]:
        yield from self._query(URL_SOLD, self._search(tu, den))

    def purchase(self, tu: date, den: date) -> Iterator[dict]:
        for ttxly in PURCHASE_TTXLY:
            yield from self._query(URL_PURCHASE, self._search(tu, den, f"ttxly=={ttxly}"))

    def export_xml(self, inv: dict) -> bytes:
        """Trả về file .zip cổng thuế cung cấp cho một hóa đơn (chứa XML)."""
        params = {k: inv[k] for k in ("nbmst", "khhdon", "shdon", "khmshdon")}
        r = self.http.get(URL_XML, params=params, timeout=TIMEOUT, verify=self.verify)
        if r.status_code != 200:
            raise PortalError(f"Không tải được XML hóa đơn {inv.get('khhdon')}-{inv.get('shdon')}")
        return r.content


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
        "raw": row,
    }
