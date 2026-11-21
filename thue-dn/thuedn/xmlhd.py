"""Đọc file XML hóa đơn điện tử (chuẩn Thông tư 78) lấy thông tin hóa đơn liên quan.

Hóa đơn điều chỉnh / thay thế có khối TTChung/TTHDLQuan:
  TCHDon        tính chất: 1 = thay thế, 2 = điều chỉnh
  KHMSHDCLQuan  ký hiệu mẫu số HĐ bị điều chỉnh / bị thay thế
  KHHDCLQuan    ký hiệu HĐ
  SHDCLQuan     số HĐ
  NLHDCLQuan    ngày lập HĐ
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
                "tinh_chat": {"1": "thay_the", "2": "dieu_chinh"}.get(f.get("TCHDon", "")),
                "goc_khmshdon": f.get("KHMSHDCLQuan") or None,
                "goc_khhdon": f.get("KHHDCLQuan") or None,
                "goc_shdon": f.get("SHDCLQuan").lstrip("0") or "0",
                "goc_tdlap": (f.get("NLHDCLQuan") or "")[:10] or None,
            }
    return None


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
