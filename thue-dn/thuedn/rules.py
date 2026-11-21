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


# ---- Kiểm tra đối tác trước khi ký hợp đồng / trước khi nhận hóa đơn ----
KET_LUAN = {
    "nen_ky": "Có thể giao dịch",
    "can_xem": "Cần xem thêm",
    "khong_nen": "Không nên giao dịch",
    "chua_du": "Chưa đủ thông tin",
}
DS_RUI_RO = {"rui_ro_cao": "DN rủi ro cao về thuế", "no_thue": "Bị công khai nợ thuế"}
THANG_DN_MOI = 12          # DN thành lập dưới 12 tháng: cần xem thêm
NGAY_TRA_LAI = 30          # nhà cung cấp đang giao dịch: tra lại sau 30 ngày


def so_thang(tu: date, den: date) -> int:
    return (den.year - tu.year) * 12 + den.month - tu.month - (1 if den.day < tu.day else 0)


def danh_gia_doi_tac(status: str, ngay_thanh_lap: str | None, nganh_khop: int | None,
                     ds_rui_ro: list[str], nguon: str | None, hom_nay: date) -> tuple[str, list[str]]:
    """Trả về (kết luận, danh sách lý do). Lý do nặng nhất quyết định kết luận."""
    khong_nen, can_xem = [], []

    if status in _NGUNG:
        khong_nen.append(f"Trạng thái MST: {TRANG_THAI_NCC[status]}")
    for loai in ds_rui_ro:
        khong_nen.append(f"Có trong danh sách: {DS_RUI_RO.get(loai, loai)}")

    if ngay_thanh_lap:
        thang = so_thang(to_date(ngay_thanh_lap), hom_nay)
        if thang < THANG_DN_MOI:
            can_xem.append(f"Doanh nghiệp mới thành lập {max(thang, 0)} tháng")
    else:
        can_xem.append("Chưa nhập ngày thành lập")
    if nganh_khop == 0:
        can_xem.append("Ngành nghề đăng ký không khớp hàng hóa / dịch vụ mua")
    elif nganh_khop is None:
        can_xem.append("Chưa đối chiếu ngành nghề")
    if nguon == "tong_hop":
        can_xem.append("Kết quả lấy từ trang tổng hợp, cần xác nhận trên trang cơ quan thuế")

    if khong_nen:
        return "khong_nen", khong_nen + can_xem
    if status == "chua_tra" or not status:
        return "chua_du", ["Chưa tra trạng thái MST"] + can_xem
    if can_xem:
        return "can_xem", can_xem
    return "nen_ky", ["Đang hoạt động, đã hoạt động trên 12 tháng, ngành nghề khớp, không có trong danh sách rủi ro"]


def parse_danh_sach_mst(text: str) -> list[tuple[str, str]]:
    """Đọc danh sách dán vào: mỗi dòng 'MST' hoặc 'MST, tên' hoặc 'MST<tab>tên'.

    Bỏ dòng tiêu đề và dòng không bắt đầu bằng MST hợp lệ (10 số, hoặc 10 số-3 số).
    """
    import re

    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d{10}(?:-\d{3})?)\s*[,;\t|]?\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return list(out.items())
