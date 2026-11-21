"""Xuất bảng kê Excel và gom XML thành .zip."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .rules import TRANG_THAI_NCC, muc_rui_ro, tinh_chat

HEADERS_VAO = ["Doanh nghiệp", "MST DN", "Ngày lập", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số HĐ",
               "MST người bán", "Tên người bán", "Tiền chưa thuế", "Tiền thuế", "Tổng thanh toán",
               "Tính chất", "Trạng thái người bán", "Mức rủi ro"]
HEADERS_RA = ["Doanh nghiệp", "MST DN", "Ngày lập", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số HĐ",
              "MST người mua", "Tên người mua", "Tiền chưa thuế", "Tiền thuế", "Tổng thanh toán",
              "Tính chất"]
MUC_RUI_RO = {"cao": "CAO", "trung_binh": "Trung bình", "thap": "Thấp", "chua_ro": "Chưa rõ"}
RED = PatternFill("solid", fgColor="F8D7DA")


def _sheet(wb: Workbook, title: str, headers: list[str]):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    return ws


def _fit(ws) -> None:
    for i, col in enumerate(ws.columns, start=1):
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[get_column_letter(i)].width = min(max(10, width + 2), 45)


def bang_ke_excel(invoices, suppliers: dict, company_names: dict[str, str]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    ws_vao = _sheet(wb, "Mua vào", HEADERS_VAO)
    ws_ra = _sheet(wb, "Bán ra", HEADERS_RA)
    ws_dc = _sheet(wb, "Điều chỉnh - thay thế", ["Chiều"] + HEADERS_RA)

    for inv in invoices:
        dn = company_names.get(inv["company_mst"], inv["company_mst"])
        common = [dn, inv["company_mst"], inv["tdlap"], inv["khmshdon"], inv["khhdon"], inv["shdon"]]
        money = [inv["tgtcthue"], inv["tgtthue"], inv["tgtttbso"]]
        tc = tinh_chat(inv["tthai"])
        if inv["direction"] == "vao":
            s = suppliers.get(inv["nbmst"])
            status = s["status"] if s else None
            muc = muc_rui_ro(status, s["ngay_ngung"] if s else None, inv["tdlap"])
            ws_vao.append(common + [inv["nbmst"], inv["nbten"]] + money +
                          [tc, TRANG_THAI_NCC.get(status or "chua_tra"), MUC_RUI_RO[muc]])
            if muc == "cao":
                for c in ws_vao[ws_vao.max_row]:
                    c.fill = RED
            doi_tac = [inv["nbmst"], inv["nbten"]]
        else:
            ws_ra.append(common + [inv["nmmst"], inv["nmten"]] + money + [tc])
            doi_tac = [inv["nmmst"], inv["nmten"]]
        if inv["tthai"] not in (1, None):
            ws_dc.append(["Mua vào" if inv["direction"] == "vao" else "Bán ra"]
                         + common + doi_tac + money + [tc])

    for ws in (ws_vao, ws_ra, ws_dc):
        _fit(ws)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def zip_xml(invoices, base_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for inv in invoices:
            p = inv["xml_path"]
            if p and (base_dir / p).exists():
                z.write(base_dir / p, arcname=p)
    return buf.getvalue()
