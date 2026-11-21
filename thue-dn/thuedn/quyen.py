"""Ba cấp tài khoản và quy tắc phân quyền.

- Admin: toàn quyền, kể cả tạo / sửa / khóa / xóa tài khoản Admin khác.
- Quản trị: như Admin, nhưng KHÔNG được đụng tới tài khoản Admin (sửa, khóa, xóa)
  và không được tạo hay nâng ai lên Admin.
- Người sử dụng: chỉ dùng phần mềm (tải hóa đơn, xem, xuất file, phân loại, kiểm tra đối tác);
  không thêm / xóa công ty, không đổi cài đặt, không quản lý tài khoản.
"""
from __future__ import annotations

import re

VAI_TRO = {"admin": "Admin", "quan_tri": "Quản trị", "nguoi_dung": "Người sử dụng"}

# quyền → các vai trò có quyền đó
QUYEN = {
    "su_dung": {"admin", "quan_tri", "nguoi_dung"},   # dùng phần mềm hằng ngày
    "quan_ly": {"admin", "quan_tri"},                 # thêm / xóa công ty, Google Drive, cài đặt, danh sách rủi ro
    "tai_khoan": {"admin", "quan_tri"},               # quản lý tài khoản (trong giới hạn bên dưới)
}


def co_quyen(vai_tro: str | None, quyen: str) -> bool:
    return vai_tro in QUYEN.get(quyen, set())


def quan_ly_duoc(nguoi_lam: str, doi_tuong: str) -> bool:
    """Người có vai trò `nguoi_lam` có được sửa / khóa / xóa tài khoản vai trò `doi_tuong` không."""
    if nguoi_lam == "admin":
        return True
    if nguoi_lam == "quan_tri":
        return doi_tuong != "admin"
    return False


def gan_duoc(nguoi_lam: str, vai_tro_moi: str) -> bool:
    """Có được tạo tài khoản / đổi tài khoản sang vai trò `vai_tro_moi` không."""
    if vai_tro_moi not in VAI_TRO:
        return False
    return quan_ly_duoc(nguoi_lam, vai_tro_moi)


def kiem_tra_mat_khau(mk: str) -> str | None:
    """Trả về lỗi, hoặc None nếu mật khẩu đạt."""
    if len(mk) < 8 or not re.search(r"[A-Za-zÀ-ỹ]", mk) or not re.search(r"\d", mk):
        return "Mật khẩu tối thiểu 8 ký tự, có cả chữ và số"
    return None
