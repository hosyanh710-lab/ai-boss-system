"""Quy tắc phân loại hóa đơn và đánh giá rủi ro người bán (không cần mạng)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

# Trường "tthai" (trạng thái hóa đơn) trên cổng hoadondientu.gdt.gov.vn
TINH_CHAT = {
    1: "Hóa đơn gốc",
    2: "Hóa đơn thay thế",
    3: "Hóa đơn điều chỉnh",
    4: "Bị thay thế",
    5: "Bị điều chỉnh",
    6: "Bị hủy",
}

TRANG_THAI_NCC = {
    "chua_tra": "Chưa tra cứu",
    "dang_hd": "Đang hoạt động",
    "tam_ngung": "Tạm ngừng kinh doanh",
    "ngung_chua_dong": "Ngừng HĐ, chưa đóng MST",
    "cham_dut": "Đã chấm dứt hiệu lực MST",
    "khong_tai_dc": "Không hoạt động tại địa chỉ đăng ký",
}

# Trạng thái mà hóa đơn lập SAU ngày này là rủi ro cao
_NGUNG = {"tam_ngung", "ngung_chua_dong", "cham_dut", "khong_tai_dc"}


def tinh_chat(tthai) -> str:
    try:
        return TINH_CHAT.get(int(tthai), f"Khác ({tthai})")
    except (TypeError, ValueError):
        return "Không rõ"


def muc_rui_ro(status: str | None, ngay_ngung: str | None, ngay_lap: str | None) -> str:
    """Trả về 'cao' | 'trung_binh' | 'thap' | 'chua_ro'."""
    if not status or status == "chua_tra":
        return "chua_ro"
    if status == "dang_hd":
        return "thap"
    if status in _NGUNG:
        if ngay_ngung and ngay_lap and ngay_lap > ngay_ngung:
            return "cao"
        return "trung_binh"
    return "chua_ro"


def parse_portal_date(value: str | None) -> str | None:
    """Cổng trả ngày dạng ISO ('2026-07-15T00:00:00Z') → 'YYYY-MM-DD'."""
    if not value:
        return None
    return str(value)[:10]


def chia_thang(tu: date, den: date) -> list[tuple[date, date]]:
    """Chia khoảng ngày thành các đoạn trong cùng một tháng (cổng giới hạn ~1 tháng/lần tra)."""
    if den < tu:
        raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
    doan = []
    cur = tu
    while cur <= den:
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = min(den, next_month - timedelta(days=1))
        doan.append((cur, end))
        cur = end + timedelta(days=1)
    return doan


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()
