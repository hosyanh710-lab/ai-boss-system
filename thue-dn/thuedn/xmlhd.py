"""Đọc file XML hóa đơn điện tử (chuẩn Thông tư 78) lấy thông tin hóa đơn liên quan.

Hóa đơn điều chỉnh / thay thế có khối TTChung/TTHDLQuan:
  TCHDon        tính chất: 1 = thay thế, 2 = điều chỉnh
  KHMSHDCLQuan  ký hiệu mẫu số HĐ bị điều chỉnh / bị thay thế
  KHHDCLQuan    ký hiệu HĐ
  SHDCLQuan     số HĐ
  NLHDCLQuan    ngày lập HĐ
  GChu          ghi chú (lý do điều chỉnh / thay thế, nếu người bán ghi)
Nội dung điều chỉnh lấy từ GChu; nếu trống thì lấy tên hàng hóa, dịch vụ (THHDVu) trên hóa đơn.
"""
from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def hd_lien_quan_tu_xml(xml_bytes: bytes) -> dict | None:
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if _local(el.tag) == "TTHDLQuan":
            f = {_local(c.tag): (c.text or "").strip() for c in el}
            if not f.get("SHDCLQuan"):
                return None
            return {
                "noi_dung": f.get("GChu") or _ten_hang(root),
                "tinh_chat": {"1": "thay_the", "2": "dieu_chinh"}.get(f.get("TCHDon", "")),
                "goc_khmshdon": f.get("KHMSHDCLQuan") or None,
                "goc_khhdon": f.get("KHHDCLQuan") or None,
                "goc_shdon": f.get("SHDCLQuan").lstrip("0") or "0",
                "goc_tdlap": (f.get("NLHDCLQuan") or "")[:10] or None,
            }
    return None


def _ten_hang(root) -> str | None:
    ten = [(e.text or "").strip() for e in root.iter() if _local(e.tag) == "THHDVu" and (e.text or "").strip()]
    if not ten:
        return None
    return "; ".join(ten[:3]) + (f" (+{len(ten) - 3} dòng)" if len(ten) > 3 else "")


# Tính chất dòng hàng hóa (TChat) theo Thông tư 78
TCHAT_DONG = {"1": "Hàng hóa, dịch vụ", "2": "Khuyến mại", "3": "Chiết khấu thương mại", "4": "Ghi chú, diễn giải"}


def _so(v: str | None):
    if v in (None, ""):
        return None
    try:
        f = float(v.replace(",", ""))
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def hang_hoa_tu_xml(xml_bytes: bytes) -> list[dict]:
    """Các dòng hàng hóa, dịch vụ (DSHHDVu/HHDVu) của một hóa đơn."""
    root = ET.fromstring(xml_bytes)
    out = []
    for el in root.iter():
        if _local(el.tag) != "HHDVu":
            continue
        f = {_local(c.tag): (c.text or "").strip() for c in el}
        out.append({
            "stt": _so(f.get("STT")) or len(out) + 1,
            "tinh_chat": TCHAT_DONG.get(f.get("TChat", ""), f.get("TChat") or None),
            "ma_hang": f.get("MHHDVu") or None,
            "ten_hang": f.get("THHDVu") or None,
            "dvt": f.get("DVTinh") or None,
            "so_luong": _so(f.get("SLuong")),
            "don_gia": _so(f.get("DGia")),
            "tl_ck": _so(f.get("TLCKhau")),
            "tien_ck": _so(f.get("STCKhau")),
            "thanh_tien": _so(f.get("ThTien")),
            "thue_suat": f.get("TSuat") or None,
        })
    return out


def doc_zip(zip_bytes: bytes) -> tuple[dict | None, list[dict]]:
    """Từ file .zip cổng thuế trả về: (thông tin HĐ liên quan, các dòng hàng hóa)."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    data = z.read(name)
                    hang = hang_hoa_tu_xml(data)
                    if hang or b"TTChung" in data:
                        return hd_lien_quan_tu_xml(data), hang
    except (zipfile.BadZipFile, ET.ParseError):
        pass
    return None, []


def hd_lien_quan_tu_zip(zip_bytes: bytes) -> dict | None:
    """File cổng thuế trả về là .zip chứa XML hóa đơn."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                if name.lower().endswith(".xml"):
                    found = hd_lien_quan_tu_xml(z.read(name))
                    if found:
                        return found
    except (zipfile.BadZipFile, ET.ParseError):
        return None
    return None
