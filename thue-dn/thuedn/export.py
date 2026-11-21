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
# Thêm vào sheet Bán ra: hóa đơn liên quan, để không phải mở sheet Điều chỉnh - thay thế
HEADERS_RA_LQ = ["Điều chỉnh / thay thế cho HĐ", "Bị điều chỉnh / thay thế bởi HĐ",
                 "Tổng sau điều chỉnh (tạm tính)", "Ghi chú HĐ liên quan"]
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


def bang_ke_excel(invoices, suppliers: dict, company_names: dict[str, str],
                  find_goc=None, find_adjusting=None) -> bytes:
    """find_goc(inv) → HĐ gốc của một HĐ điều chỉnh / thay thế (tìm trong toàn bộ dữ liệu đã tải);
    find_adjusting(goc) → các HĐ điều chỉnh / thay thế trỏ tới HĐ gốc đó."""
    invoices = list(invoices)
    wb = Workbook()
    wb.remove(wb.active)
    ws_vao = _sheet(wb, "Mua vào", HEADERS_VAO)
    ws_ra = _sheet(wb, "Bán ra", HEADERS_RA + HEADERS_RA_LQ)
    find_goc = find_goc or (lambda i: None)
    find_adjusting = find_adjusting or (lambda g: [])
    _sheet_lien_ket(wb, invoices, company_names, find_goc, find_adjusting)

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
        else:
            lq, note = _lien_quan(inv, find_goc, find_adjusting)
            ws_ra.append(common + [inv["nmmst"], inv["nmten"]] + money + [tc] + lq)
            if note:
                for c in ws_ra[ws_ra.max_row]:
                    c.fill = YELLOW

    for ws in (ws_vao, ws_ra):
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, (int, float)):
                    c.number_format = "#,##0"
        _fit(ws)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---- Sheet nối HĐ gốc với HĐ điều chỉnh / thay thế: mỗi hàng một HĐ điều chỉnh / thay thế,
#      cột HĐ gốc trước, cột HĐ điều chỉnh / thay thế sau ----
LK_INFO = ["Doanh nghiệp", "MST DN", "Chiều", "MST đối tác", "Tên đối tác", "Loại", "Lần"]
LK_HD = ["Ký hiệu mẫu", "Ký hiệu", "Số HĐ", "Ngày lập", "Tiền chưa thuế", "Tiền thuế", "Tổng thanh toán"]
LK_GOC = LK_HD + ["Trạng thái HĐ gốc"]
LK_END = ["Tổng sau điều chỉnh (tạm tính)", "Ghi chú"]
YELLOW = PatternFill("solid", fgColor="FFF3CD")
GREY = PatternFill("solid", fgColor="EEF0F3")
BLUE = PatternFill("solid", fgColor="DCE8F7")
ORANGE = PatternFill("solid", fgColor="FBE3D0")


def _ten_hd(khmshdon, khhdon, shdon, tdlap) -> str:
    ngay = f" ngày {'/'.join(reversed(str(tdlap)[:10].split('-')))}" if tdlap else ""
    return f"{khmshdon or ''}{khhdon or ''} số {_int(shdon)}{ngay}"


def _lien_quan(inv, find_goc, find_adjusting) -> tuple[list, bool]:
    """4 cột HĐ liên quan cho một dòng hóa đơn, và có cần tô vàng không."""
    cho = bi = tong = None
    notes = []
    if inv["tthai"] in (2, 3):
        if not inv["goc_shdon"]:
            notes.append("Chưa có thông tin HĐ gốc (tải kèm XML để lấy)")
        else:
            goc = find_goc(inv)
            cho = _ten_hd(inv["goc_khmshdon"], inv["goc_khhdon"], inv["goc_shdon"], inv["goc_tdlap"])
            if goc is None:
                notes.append("HĐ gốc chưa có trong dữ liệu đã tải")
    if inv["tthai"] in (4, 5):
        adjs = find_adjusting(inv)
        if adjs:
            bi = "; ".join(_ten_hd(a["khmshdon"], a["khhdon"], a["shdon"], a["tdlap"]) for a in adjs)
            if inv["tthai"] == 5:
                tong = (inv["tgtttbso"] or 0) + sum(a["tgtttbso"] or 0 for a in adjs if a["tthai"] == 3)
            else:
                tong = adjs[-1]["tgtttbso"]
        else:
            notes.append("Chưa có HĐ điều chỉnh / thay thế trong dữ liệu đã tải")
    return [cho, bi, tong, "; ".join(notes) or None], bool(notes)


def _hd_cols(inv) -> list:
    if inv is None:
        return [None] * len(LK_HD)
    return [inv["khmshdon"], inv["khhdon"], _int(inv["shdon"]), inv["tdlap"],
            inv["tgtcthue"], inv["tgtthue"], inv["tgtttbso"]]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return v


def _sheet_lien_ket(wb: Workbook, invoices, names, find_goc, find_adjusting) -> None:
    ws = wb.create_sheet("Điều chỉnh - thay thế")
    n_info, n_hd, n_goc = len(LK_INFO), len(LK_HD), len(LK_GOC)
    # hàng 1: nhóm cột, hàng 2: tên cột
    groups = [("THÔNG TIN CHUNG", n_info, GREY),
              ("HÓA ĐƠN GỐC (BỊ ĐIỀU CHỈNH / BỊ THAY THẾ)", n_goc, ORANGE),
              ("HÓA ĐƠN ĐIỀU CHỈNH / THAY THẾ", n_hd, BLUE),
              ("", len(LK_END), GREY)]
    col = 1
    for title, width, fill in groups:
        ws.cell(1, col, title).font = Font(bold=True)
        ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + width - 1)
        for c in range(col, col + width):
            ws.cell(1, c).fill = fill
            ws.cell(2, c).fill = fill
        col += width
    for i, h in enumerate(LK_INFO + LK_GOC + LK_HD + LK_END, start=1):
        ws.cell(2, i, h).font = Font(bold=True)
    ws.freeze_panes = f"{get_column_letter(n_info + 1)}3"

    entries = []          # (khóa sắp xếp, hd điều chỉnh/thay thế hoặc None, hd gốc hoặc None, ghi chú)
    done = set()

    def add(adj, goc, note=""):
        if adj is not None:
            if adj["id"] in done:
                return
            done.add(adj["id"])
        base = adj if adj is not None else goc
        key = (base["company_mst"], base["direction"], base["nbmst"] if base["direction"] == "vao" else base["nmmst"],
               goc["khhdon"] if goc is not None else (adj["goc_khhdon"] or ""),
               _int(goc["shdon"]) if goc is not None else _int(adj["goc_shdon"] or 0),
               adj["tdlap"] if adj is not None else "", adj["id"] if adj is not None else 0)
        entries.append((tuple("" if k is None else str(k).zfill(12) if isinstance(k, int) else str(k) for k in key),
                        adj, goc, note))

    for inv in invoices:
        if inv["tthai"] in (2, 3):
            goc = find_goc(inv) if inv["goc_shdon"] else None
            if not inv["goc_shdon"]:
                note = "Chưa có thông tin HĐ gốc (tải kèm XML để lấy)"
            elif goc is None:
                note = "HĐ gốc chưa có trong dữ liệu đã tải (tải thêm kỳ của HĐ gốc)"
            else:
                note = ""
            add(inv, goc, note)
    for inv in invoices:
        if inv["tthai"] in (4, 5):
            adjs = find_adjusting(inv)
            if not adjs:
                add(None, inv, "Chưa có HĐ điều chỉnh / thay thế trong dữ liệu đã tải")
            for a in adjs:
                add(a, inv, "HĐ điều chỉnh / thay thế nằm ngoài kỳ đang lọc")

    entries.sort(key=lambda e: e[0])
    lan: dict = {}
    cong_don: dict = {}
    for _, adj, goc, note in entries:
        base = adj if adj is not None else goc
        vao = base["direction"] == "vao"
        doi_tac = [base["nbmst"], base["nbten"]] if vao else [base["nmmst"], base["nmten"]]
        loai = {2: "Thay thế", 3: "Điều chỉnh"}.get(adj["tthai"]) if adj is not None else None
        so_lan = None
        tong_sau = None
        if adj is not None and goc is not None:
            k = goc["id"]
            lan[k] = lan.get(k, 0) + 1
            so_lan = lan[k]
            if adj["tthai"] == 3:
                cong_don[k] = cong_don.get(k, goc["tgtttbso"] or 0) + (adj["tgtttbso"] or 0)
                tong_sau = cong_don[k]
            else:
                tong_sau = adj["tgtttbso"]
        ws.append([names.get(base["company_mst"], base["company_mst"]), base["company_mst"],
                   "Mua vào" if vao else "Bán ra", *doi_tac, loai, so_lan,
                   *_hd_cols(goc),
                   tinh_chat(goc["tthai"]) if goc is not None else None,
                   *_hd_cols(adj),
                   tong_sau, note or None])
        if note and not note.startswith("HĐ điều chỉnh / thay thế nằm ngoài"):
            for c in ws[ws.max_row]:
                c.fill = YELLOW
        # khi chưa tìm thấy HĐ gốc trong dữ liệu, vẫn ghi ký hiệu / số gốc đọc được
        if adj is not None and goc is None and adj["goc_shdon"]:
            start = n_info + 1
            for off, v in enumerate([adj["goc_khmshdon"], adj["goc_khhdon"], _int(adj["goc_shdon"]),
                                     adj["goc_tdlap"]]):
                ws.cell(ws.max_row, start + off, v)
    for row in ws.iter_rows(min_row=3):
        for c in row:
            if isinstance(c.value, (int, float)) and c.column not in (n_info, n_info + 3, n_info + n_goc + 3):
                c.number_format = "#,##0"
    _fit(ws)
    ws.column_dimensions["A"].width = 30


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
