"""Đọc file Excel "DANH SÁCH HÓA ĐƠN" do cổng hoadondientu xuất (nút Xuất hóa đơn).

Dùng cho hóa đơn khởi tạo từ máy tính tiền: tra danh sách trên cổng phải gõ captcha cho mỗi
trang 50 hóa đơn, còn xuất Excel thì một captcha lấy cả tháng.

Cột được nhận theo tên tiêu đề (không theo vị trí), tiêu đề có thể gộp 2 dòng
(ví dụ "Thông tin người mua" / "MST", "Tên người mua").
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime

from openpyxl import load_workbook

TRANG_THAI = [  # (từ khóa trong cột "Trạng thái hóa đơn", mã tthai của cổng) — xét từ cụ thể tới chung
    ("bị thay thế", 4), ("bi thay the", 4), ("bị điều chỉnh", 5), ("bi dieu chinh", 5),
    ("hủy", 6), ("huy", 6), ("thay thế", 2), ("thay the", 2), ("điều chỉnh", 3), ("dieu chinh", 3),
    ("mới", 1), ("moi", 1), ("gốc", 1), ("goc", 1),
]


def _khong_dau(s) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip().lower()


def _cot(ten: str) -> str | None:
    t = _khong_dau(ten)
    if "mau so" in t:
        return "khmshdon"
    if "ky hieu" in t:
        return "khhdon"
    if t.startswith("so hoa don") or t == "so hd":
        return "shdon"
    if "ngay lap" in t:
        return "tdlap"
    if "nguoi mua" in t or "khach hang" in t:
        if "mst" in t or "ma so thue" in t:
            return "nmmst"
        if "ten" in t:
            return "nmten"
        return None
    if "chua thue" in t:
        return "tgtcthue"
    if "thanh toan" in t:
        return "tgtttbso"
    if "tien thue" in t or t == "thue gtgt":
        return "tgtthue"
    if "trang thai" in t:
        return "tthai_chu"
    return None


def _so(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if re.fullmatch(r"-?[\d.]+,\d+", s) or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "").replace(",", ".")          # 1.234.567,5 kiểu Việt Nam
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(v) -> str | None:
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    s = str(v or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else None


def _ma(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return str(int(s)) if s.isdigit() else s or None       # số HĐ lưu không có số 0 ở đầu, giống cổng


def _mst(v) -> str | None:
    """MST giữ nguyên số 0 đầu (Excel lưu dạng số thì mất số 0: 312345678 → 0312345678)."""
    if v is None or str(v).strip() == "":
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s.zfill(10) if s.isdigit() and len(s) < 10 else s


def tthai_tu_chu(chu) -> int | None:
    t = _khong_dau(chu)
    for tu_khoa, ma in TRANG_THAI:
        if _khong_dau(tu_khoa) in t:
            return ma
    return None


def doc_danh_sach(content: bytes, nbmst: str, nbten: str | None) -> list[dict]:
    """Trả về các dòng giống dữ liệu cổng trả qua API (để dùng chung portal.normalize)."""
    ws = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    dong_tieu_de = next((i for i, r in enumerate(rows[:30])
                         if any(_cot(c or "") == "shdon" for c in r)), None)
    if dong_tieu_de is None:
        raise ValueError("Không thấy dòng tiêu đề có cột 'Số hóa đơn' trong file Excel của cổng")
    tieu_de = [str(c or "") for c in rows[dong_tieu_de]]
    bat_dau = dong_tieu_de + 1
    # Tiêu đề 2 tầng: dòng dưới là tên cột con (không có số hóa đơn)
    if bat_dau < len(rows):
        duoi = rows[bat_dau]
        i_so = next(i for i, c in enumerate(tieu_de) if _cot(c) == "shdon")
        if duoi[i_so] in (None, "") and any(isinstance(c, str) and c.strip() for c in duoi):
            cha = ""
            ghep = []
            for i, c in enumerate(tieu_de):
                cha = c or cha
                con = duoi[i] if i < len(duoi) else None
                ghep.append(f"{cha} {con}" if con else (c or ""))
            tieu_de, bat_dau = ghep, bat_dau + 1
    cot = {}
    for i, c in enumerate(tieu_de):
        k = _cot(c)
        if k and k not in cot:
            cot[k] = i
    thieu = [k for k in ("khhdon", "shdon", "tdlap") if k not in cot]
    if thieu:
        raise ValueError(f"File Excel của cổng thiếu cột {', '.join(thieu)}; tiêu đề: {tieu_de}")

    ket_qua = []
    for r in rows[bat_dau:]:
        lay = {k: (r[i] if i < len(r) else None) for k, i in cot.items()}
        so = _ma(lay.get("shdon"))
        if not so or not str(so).isdigit():
            continue                                         # dòng trống / dòng tổng cộng
        kh = str(lay.get("khhdon") or "").strip()
        ms = _ma(lay.get("khmshdon"))
        if not ms and kh[:1].isdigit():                      # "1C26MAA": mẫu số dính đầu ký hiệu
            ms, kh = kh[0], kh[1:]
        ngay = _ngay(lay.get("tdlap"))
        ket_qua.append({
            "nbmst": nbmst, "nbten": nbten,
            "nmmst": _mst(lay.get("nmmst")), "nmten": lay.get("nmten"),
            "khmshdon": int(ms) if ms and ms.isdigit() else (ms or 1), "khhdon": kh, "shdon": int(so),
            "tdlap": f"{ngay}T00:00:00" if ngay else None,
            "tgtcthue": _so(lay.get("tgtcthue")), "tgtthue": _so(lay.get("tgtthue")),
            "tgtttbso": _so(lay.get("tgtttbso")),
            "tthai": tthai_tu_chu(lay.get("tthai_chu")) or 1,
            "nguon": "excel-cong",
        })
    return ket_qua
