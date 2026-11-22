"""Tạo hoặc đổi vai trò một tài khoản ngay trên máy, không cần mở trình duyệt.

Cách dùng (trong thư mục thue-dn):
    .venv\\Scripts\\python tao_tai_khoan.py <email> <admin|quan_tri|nguoi_dung> [họ tên]

Mật khẩu được hỏi trực tiếp (gõ không hiện ra màn hình), không ghi vào lệnh hay file nào.
Email đã có tài khoản: đổi vai trò, mở khóa và (nếu nhập) đặt lại mật khẩu.
"""
from __future__ import annotations

import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

from thuedn.quyen import VAI_TRO, kiem_tra_mat_khau
from thuedn.storage import Storage

DATA_DIR = Path(os.environ.get("THUEDN_DATA", Path(__file__).parent / "data"))


def tao_hoac_cap_nhat(store: Storage, email: str, vai_tro: str, ho_ten: str, mat_khau: str | None) -> str:
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("Email không hợp lệ")
    if vai_tro not in VAI_TRO:
        raise ValueError(f"Vai trò phải là một trong: {', '.join(VAI_TRO)}")
    if mat_khau is not None and (loi := kiem_tra_mat_khau(mat_khau)):
        raise ValueError(loi)
    u = store.user_by_email(email)
    if u is None:
        if mat_khau is None:
            raise ValueError("Tài khoản mới cần mật khẩu")
        store.add_user(email, ho_ten, generate_password_hash(mat_khau), vai_tro, "tao_tai_khoan.py",
                       datetime.now().strftime("%Y-%m-%d %H:%M"))
        return f"Đã tạo {email}: {VAI_TRO[vai_tro]}"
    thay = {"vai_tro": vai_tro, "hoat_dong": 1}
    if ho_ten:
        thay["ho_ten"] = ho_ten
    if mat_khau is not None:
        thay["pw_hash"] = generate_password_hash(mat_khau)
    store.update_user(u["id"], **thay)
    return f"Đã cập nhật {email}: {VAI_TRO[vai_tro]}" + (", đặt lại mật khẩu" if mat_khau else "")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    email, vai_tro, ho_ten = argv[1], argv[2], " ".join(argv[3:])
    store = Storage(DATA_DIR)
    co_san = store.user_by_email(email) is not None
    goi_y = " (Enter để giữ mật khẩu cũ)" if co_san else ""
    mk = getpass.getpass(f"Mật khẩu cho {email}{goi_y}: ")
    if co_san and not mk:
        mk = None
    elif mk != getpass.getpass("Nhập lại mật khẩu: "):
        print("Hai lần nhập mật khẩu không khớp")
        return 1
    try:
        print(tao_hoac_cap_nhat(store, email, vai_tro, ho_ten, mk))
    except ValueError as e:
        print(f"Lỗi: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
