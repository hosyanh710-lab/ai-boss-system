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


def phieu_kiem_tra(mst: str, checks, mua: dict | None) -> bytes:
    """Phiếu kiểm tra đối tác: toàn bộ lịch sử tra cứu, làm bằng chứng đã thẩm định."""
    from .rules import DS_RUI_RO, KET_LUAN

    wb = Workbook()
    ws = wb.active
    ws.title = "Phiếu kiểm tra"
    last = checks[0] if checks else None
    ws.append(["PHIẾU KIỂM TRA ĐỐI TÁC"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    info = [
        ("Mã số thuế", mst),
        ("Tên", last["ten"] if last else ""),
        ("Kết luận gần nhất", KET_LUAN.get(last["ket_luan"], "") if last else "Chưa kiểm tra"),
        ("Ngày kiểm tra gần nhất", last["checked_at"] if last else ""),
        ("Trạng thái MST", TRANG_THAI_NCC.get(last["status"], "") if last else ""),
        ("Ngày thành lập", last["ngay_thanh_lap"] if last else ""),
        ("Địa chỉ", last["dia_chi"] if last else ""),
        ("Người đại diện", last["nguoi_dai_dien"] if last else ""),
        ("Ngành nghề", last["nganh_nghe"] if last else ""),
    ]
    if mua and mua["so_hd"]:
        info.append(("Đã mua", f"{mua['so_hd']} hóa đơn, {mua['tong']:,.0f} đ, từ {mua['dau']} đến {mua['cuoi']}"))
    for k, v in info:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 70

    hs = wb.create_sheet("Lịch sử kiểm tra")
    hs.append(["Ngày kiểm tra", "Kết luận", "Trạng thái MST", "Ngày ngừng", "Ngày thành lập",
               "Ngành nghề khớp", "Danh sách rủi ro", "Nguồn", "Lý do", "Ghi chú"])
    for c in hs[1]:
        c.font = Font(bold=True)
    nguon = {"cqt": "Cơ quan thuế", "tong_hop": "Trang tổng hợp", "nhap_tay": "Nhập tay"}
    for c in checks:
        ds = ", ".join(DS_RUI_RO.get(x, x) for x in (c["ds_rui_ro"] or "").split(",") if x)
        hs.append([c["checked_at"], KET_LUAN.get(c["ket_luan"]), TRANG_THAI_NCC.get(c["status"]),
                   c["ngay_ngung"], c["ngay_thanh_lap"],
                   {1: "Khớp", 0: "Không khớp"}.get(c["nganh_khop"], "Chưa xem"), ds,
                   nguon.get(c["nguon"], c["nguon"]), c["ly_do"], c["ghi_chu"]])
        if c["ket_luan"] == "khong_nen":
            for cell in hs[hs.max_row]:
                cell.fill = RED
    _fit(hs)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
