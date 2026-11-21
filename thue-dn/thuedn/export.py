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
               "Tính chất"]
HEADERS_VAO_RUI_RO = ["Trạng thái người bán", "Mức rủi ro"]
HEADERS_RA = ["Doanh nghiệp", "MST DN", "Ngày lập", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số HĐ",
              "MST người mua", "Tên người mua", "Tiền chưa thuế", "Tiền thuế", "Tổng thanh toán",
              "Tính chất"]
# Sheet Mua vào, Bán ra: hóa đơn điều chỉnh / thay thế nằm CÙNG HÀNG với hóa đơn bị điều chỉnh / thay thế
HEADERS_RA_DC = ["Ký hiệu HĐ ĐC/TT", "Số HĐ ĐC/TT", "Ngày HĐ ĐC/TT", "Nội dung điều chỉnh",
                 "Tiền chưa thuế ĐC/TT", "Tiền thuế ĐC/TT", "Tổng thanh toán ĐC/TT"]
HEADERS_RA_END = ["Tổng sau điều chỉnh (tạm tính)", "Đánh giá"]
MUC_RUI_RO = {"cao": "CAO", "trung_binh": "Trung bình", "thap": "Thấp", "chua_ro": "Chưa rõ"}
RED = PatternFill("solid", fgColor="F8D7DA")


def dinh_dang_so(c) -> None:
    """Số nguyên (kể cả 2000.0 đọc từ CSDL): 2.000; số lẻ: 12,5. Tránh dấu phân cách thừa ở cuối."""
    if isinstance(c.value, float) and c.value.is_integer():
        c.value = int(c.value)
    c.number_format = "#,##0" if isinstance(c.value, int) else "#,##0.###"


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
                  find_goc=None, find_adjusting=None, items: dict | None = None,
                  tong_hop: list[dict] | None = None, items_for=None) -> bytes:
    """find_goc(inv) → HĐ gốc của một HĐ điều chỉnh / thay thế (tìm trong toàn bộ dữ liệu đã tải);
    find_adjusting(goc) → các HĐ điều chỉnh / thay thế trỏ tới HĐ gốc đó."""
    invoices = list(invoices)
    wb = Workbook()
    wb.remove(wb.active)
    ws_vao = _sheet(wb, "Mua vào", HEADERS_VAO + HEADERS_RA_DC + HEADERS_RA_END[:1] + HEADERS_VAO_RUI_RO
                    + HEADERS_RA_END[1:])
    ws_ra = _sheet(wb, "Bán ra", HEADERS_RA + HEADERS_RA_DC + HEADERS_RA_END)
    find_goc = find_goc or (lambda i: None)
    find_adjusting = find_adjusting or (lambda g: [])
    _sheet_lien_ket(wb, invoices, company_names, find_goc, find_adjusting)
    items = items or {}
    for title, d in (("Chi tiết bán ra", "ra"), ("Chi tiết mua vào", "vao")):
        _sheet_chi_tiet(wb, title, [i for i in invoices if i["direction"] == d], items, company_names,
                        find_goc, find_adjusting, items_for)
    if tong_hop is not None:
        _sheet_tong_hop(wb, tong_hop, invoices, items, company_names)

    _sheet_hd(ws_vao, [i for i in invoices if i["direction"] == "vao"], company_names, find_goc,
              find_adjusting, suppliers)
    _sheet_hd(ws_ra, [i for i in invoices if i["direction"] == "ra"], company_names, find_goc,
              find_adjusting, None)

    for ws in (ws_vao, ws_ra):
        # chỉ cột số tiền có dấu phân cách hàng nghìn; số hóa đơn giữ nguyên (1021, không phải 1.021)
        cot_so_hd = {c.column for c in ws[1] if str(c.value).startswith("Số HĐ")}
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, (int, float)) and c.column not in cot_so_hd:
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


def _noi_dung(adj) -> str:
    """Loại điều chỉnh theo dấu số tiền (CẦN KIỂM TRA với dữ liệu thật) + nội dung đọc từ XML."""
    if adj["tthai"] == 2:
        loai = "Thay thế"
    else:
        tien = adj["tgtttbso"] or 0
        loai = "Điều chỉnh giảm" if tien < 0 else "Điều chỉnh tăng" if tien > 0 else "Điều chỉnh thông tin"
    nd = adj["noi_dung"] if "noi_dung" in adj.keys() else None
    return f"{loai}: {nd}" if nd else loai


_THU_TU_RUI_RO = {"cao": 3, "trung_binh": 2, "thap": 1, "chua_ro": 0}


def _sheet_hd(ws, invoices, names, find_goc, find_adjusting, suppliers) -> None:
    """Sheet Mua vào (suppliers != None, thêm cột rủi ro người bán) hoặc Bán ra.

    Mỗi hàng: một hóa đơn; nếu bị điều chỉnh / thay thế thì cùng hàng ghi HĐ điều chỉnh /
    thay thế. Một HĐ bị điều chỉnh nhiều lần: mỗi lần một hàng, từ hàng thứ 2 để trống số tiền HĐ
    gốc để cộng cột không bị trùng. HĐ điều chỉnh / thay thế không lặp lại thành hàng riêng."""
    mua_vao = suppliers is not None
    n_goc = len(HEADERS_VAO if mua_vao else HEADERS_RA)
    in_ky = {i["id"] for i in invoices}
    da_ghi: set = set()

    def ghi(goc, adj, tong_sau, danh_gia, canh_bao, an_tien_goc=False, goc_tam=None):
        base = goc if goc is not None else adj
        g = goc if goc is not None else goc_tam
        dn = names.get(base["company_mst"], base["company_mst"])
        if g is not None:
            row = [dn, base["company_mst"], g["tdlap"], g["khmshdon"], g["khhdon"], _int(g["shdon"])]
            row += [base["nbmst"], base["nbten"]] if mua_vao else [base["nmmst"], base["nmten"]]
            row += [None] * 3 if an_tien_goc or goc is None else [goc["tgtcthue"], goc["tgtthue"], goc["tgtttbso"]]
            row.append(tinh_chat(goc["tthai"]) if goc is not None else None)
        else:
            # chưa biết HĐ gốc: vẫn ghi đối tác để lọc theo người bán / người mua
            doi_tac = [base["nbmst"], base["nbten"]] if mua_vao else [base["nmmst"], base["nmten"]]
            row = [dn, base["company_mst"], None, None, None, None] + doi_tac + [None] * (n_goc - 8)
        if adj is not None:
            row += [adj["khhdon"], _int(adj["shdon"]), adj["tdlap"], _noi_dung(adj),
                    adj["tgtcthue"], adj["tgtthue"], adj["tgtttbso"]]
        else:
            row += [None] * len(HEADERS_RA_DC)
        row.append(tong_sau)
        muc = None
        if mua_vao:
            s = suppliers.get(base["nbmst"])
            status = s["status"] if s else None
            # HĐ gốc hoặc HĐ điều chỉnh lập sau ngày người bán ngừng hoạt động đều là rủi ro
            ngay = [h["tdlap"] for h in (goc, adj) if h is not None]
            muc = max((muc_rui_ro(status, s["ngay_ngung"] if s else None, d) for d in ngay),
                      key=_THU_TU_RUI_RO.get)
            row += [TRANG_THAI_NCC.get(status or "chua_tra"), MUC_RUI_RO[muc]]
        row.append(danh_gia)
        ws.append(row)
        for c in ws[ws.max_row][n_goc:n_goc + len(HEADERS_RA_DC)]:
            c.fill = BLUE
        if canh_bao:
            for c in ws[ws.max_row]:
                c.fill = YELLOW
        if muc == "cao":
            for c in ws[ws.max_row]:
                c.fill = RED

    def nhom(goc, adjs, goc_ngoai_ky=False):
        """Ghi HĐ gốc cùng các HĐ điều chỉnh / thay thế của nó."""
        tong = goc["tgtttbso"] or 0
        for k, a in enumerate(adjs):
            da_ghi.add(a["id"])
            if a["tthai"] == 3:
                tong += a["tgtttbso"] or 0
                dg = f"Đã điều chỉnh lần {k + 1}" if len(adjs) > 1 else "Đã điều chỉnh"
            else:
                tong = a["tgtttbso"] or 0
                dg = "Đã thay thế"
            if goc_ngoai_ky:
                dg += "; HĐ gốc thuộc kỳ khác (ngoài kỳ đang lọc)"
            if a["id"] not in in_ky:
                dg += "; HĐ ĐC/TT thuộc kỳ khác (ngoài kỳ đang lọc)"
            if goc["tthai"] not in (4, 5):
                dg += "; trạng thái HĐ gốc trên cổng thuế chưa cập nhật"
            ghi(goc, a, tong, dg, False, an_tien_goc=k > 0)

    for inv in invoices:
        if inv["id"] in da_ghi:
            continue
        if inv["tthai"] in (2, 3):
            continue                                   # ghi cùng hàng HĐ gốc, xử lý sau
        da_ghi.add(inv["id"])
        adjs = find_adjusting(inv)
        if adjs:
            nhom(inv, adjs)
        elif inv["tthai"] in (4, 5):
            ghi(inv, None, None, "Bị điều chỉnh / thay thế nhưng chưa có HĐ ĐC/TT trong dữ liệu đã tải", True)
        elif inv["tthai"] == 6:
            ghi(inv, None, None, "Hóa đơn đã hủy", False)
        else:
            ghi(inv, None, inv["tgtttbso"], "Bình thường", False)

    # HĐ điều chỉnh / thay thế trong kỳ mà HĐ gốc không nằm trong kỳ hoặc chưa tải
    for inv in invoices:
        if inv["id"] in da_ghi or inv["tthai"] not in (2, 3):
            continue
        if not inv["goc_shdon"]:
            da_ghi.add(inv["id"])
            ghi(None, inv, None, "Chưa có thông tin HĐ gốc (tải kèm XML để lấy)", True)
            continue
        goc = find_goc(inv)
        if goc is not None:
            nhom(goc, [a for a in find_adjusting(goc)], goc_ngoai_ky=goc["id"] not in in_ky)
        else:
            da_ghi.add(inv["id"])
            tam = {"tdlap": inv["goc_tdlap"], "khmshdon": inv["goc_khmshdon"], "khhdon": inv["goc_khhdon"],
                   "shdon": inv["goc_shdon"]}
            ghi(None, inv, None, "HĐ gốc chưa có trong dữ liệu đã tải (tải thêm kỳ của HĐ gốc)", True,
                goc_tam=tam)


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


# ---- Sheet chi tiết hàng hóa: mỗi hàng một dòng hàng hóa / dịch vụ của một hóa đơn ----
HEADERS_CT = ["Doanh nghiệp", "MST DN", "Ngày lập", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số HĐ",
              "MST đối tác", "Tên đối tác", "Tính chất HĐ", "HĐ gốc (nếu là HĐ ĐC/TT)",
              "STT dòng", "Mã hàng", "Tên hàng hóa, dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
              "Tỷ lệ CK (%)", "Tiền chiết khấu", "Thành tiền chưa thuế", "Thuế suất",
              "Tiền thuế (tính theo thuế suất)", "Tính chất dòng",
              "SL sau điều chỉnh", "Thành tiền sau điều chỉnh", "Tính vào tổng", "Ghi chú"]
GREY_ROW = PatternFill("solid", fgColor="E7E9ED")


def _tien_thue(thanh_tien, thue_suat):
    """Tiền thuế dòng = thành tiền × thuế suất. XML không ghi tiền thuế theo từng dòng."""
    if thanh_tien is None or not thue_suat:
        return None
    ts = str(thue_suat).strip().rstrip("%")
    try:
        return round(thanh_tien * float(ts) / 100)
    except ValueError:
        return 0 if thue_suat.upper() in ("KCT", "KKKNT") else None


def _sau_dieu_chinh(goc_lines, adj_groups) -> tuple[dict, dict]:
    """Ghép dòng của HĐ điều chỉnh với dòng HĐ gốc theo mã hàng (không có mã thì theo tên).

    Trả về: {stt dòng gốc: (SL sau ĐC, thành tiền sau ĐC, ghi chú)} và
            {(id HĐ điều chỉnh, stt dòng): ghi chú (bắt đầu bằng '!' nếu cần xem tay)}."""
    from .rules import ma_key

    theo_key: dict = {}
    for d in goc_lines:
        theo_key.setdefault(ma_key(d["ma_hang"], d["ten_hang"]), []).append(d)
    sau = {d["stt"]: [d["so_luong"] or 0, d["thanh_tien"] or 0, []] for d in goc_lines}
    ghep: dict = {}
    for adj, lines in adj_groups:
        for d in lines:
            if d["tinh_chat"] == "Ghi chú, diễn giải" or (d["thanh_tien"] in (None, 0) and not d["so_luong"]):
                ghep[(adj["id"], d["stt"])] = "Dòng ghi chú / điều chỉnh thông tin, không có số tiền"
                continue
            khop = theo_key.get(ma_key(d["ma_hang"], d["ten_hang"]), [])
            if len(khop) != 1:
                ghep[(adj["id"], d["stt"])] = ("!Không ghép được với dòng nào của HĐ gốc (mã / tên hàng khác)"
                                              if not khop else
                                              "!Mặt hàng có nhiều dòng trên HĐ gốc, cần ghép tay")
                continue
            g = khop[0]
            sau[g["stt"]][0] += d["so_luong"] or 0
            sau[g["stt"]][1] += d["thanh_tien"] or 0
            sau[g["stt"]][2].append(f"HĐ {adj['khhdon']} số {_int(adj['shdon'])}")
            ghep[(adj["id"], d["stt"])] = f"Ghép với dòng {g['stt']} của HĐ gốc"
    ket_qua = {stt: (v[0], v[1], "Đã điều chỉnh bởi " + ", ".join(v[2])) for stt, v in sau.items() if v[2]}
    return ket_qua, ghep


def _sheet_chi_tiet(wb: Workbook, title: str, invoices, items: dict, names,
                    find_goc=None, find_adjusting=None, items_for=None) -> None:
    """Mỗi hàng một dòng hàng hóa. Dòng của HĐ điều chỉnh / thay thế nằm ngay dưới dòng HĐ gốc.

    Tính vào tổng = Không: HĐ bị thay thế, bị hủy, hoặc HĐ thuộc kỳ khác (chỉ hiện để đối chiếu)."""
    find_goc = find_goc or (lambda i: None)
    find_adjusting = find_adjusting or (lambda g: [])
    items = dict(items)
    ws = _sheet(wb, title, HEADERS_CT)
    so_cot = {HEADERS_CT.index(h) + 1 for h in ("Số HĐ", "STT dòng")}
    in_ky = {i["id"] for i in invoices}
    da_ghi: set = set()

    def dong_cua(inv):
        if inv["id"] not in items and items_for is not None:
            items.update(items_for([inv["id"]]))
        return items.get(inv["id"], [])

    def ghi_hd(inv, sau=None, ghep=None, ghi_chu_hd=None):
        da_ghi.add(inv["id"])
        vao = inv["direction"] == "vao"
        goc = (_ten_hd(inv["goc_khmshdon"], inv["goc_khhdon"], inv["goc_shdon"], inv["goc_tdlap"])
               if inv["goc_shdon"] else None)
        dau = [names.get(inv["company_mst"], inv["company_mst"]), inv["company_mst"], inv["tdlap"],
               inv["khmshdon"], inv["khhdon"], _int(inv["shdon"]),
               inv["nbmst"] if vao else inv["nmmst"], inv["nbten"] if vao else inv["nmten"],
               tinh_chat(inv["tthai"]), goc]
        if inv["id"] not in in_ky:
            tinh, ly_do = "Không", "HĐ thuộc kỳ khác, chỉ hiện để đối chiếu"
        elif inv["tthai"] == 4:
            tinh, ly_do = "Không", "HĐ đã bị thay thế"
        elif inv["tthai"] == 6:
            tinh, ly_do = "Không", "HĐ đã bị hủy"
        else:
            tinh, ly_do = "Có", None
        dong = dong_cua(inv)
        if not dong:
            ws.append(dau + [None] * 14 + [tinh, "; ".join(x for x in (
                ly_do, ghi_chu_hd, "Chưa có chi tiết hàng hóa (tải kèm XML để lấy)") if x)])
            for c in ws[ws.max_row]:
                c.fill = YELLOW
            return
        for d in dong:
            sl_sau = tt_sau = None
            notes = [ly_do, ghi_chu_hd]
            if sau and d["stt"] in sau:
                sl_sau, tt_sau, n = sau[d["stt"]]
                notes.append(n)
            canh_bao = False
            if ghep and (inv["id"], d["stt"]) in ghep:
                n = ghep[(inv["id"], d["stt"])]
                canh_bao = n.startswith("!")
                notes.append(n.lstrip("!"))
            ws.append(dau + [d["stt"], d["ma_hang"], d["ten_hang"], d["dvt"], d["so_luong"], d["don_gia"],
                             d["tl_ck"], d["tien_ck"], d["thanh_tien"], d["thue_suat"],
                             _tien_thue(d["thanh_tien"], d["thue_suat"]), d["tinh_chat"],
                             sl_sau, tt_sau, tinh, "; ".join(x for x in notes if x) or None])
            fill = YELLOW if canh_bao else GREY_ROW if tinh == "Không" else None
            if fill:
                for c in ws[ws.max_row]:
                    c.fill = fill

    def nhom(goc, ghi_chu_goc=None):
        """HĐ gốc, rồi ngay dưới là các HĐ điều chỉnh / thay thế của nó."""
        adjs = find_adjusting(goc)
        dc = [(a, dong_cua(a)) for a in adjs if a["tthai"] == 3]
        sau, ghep = _sau_dieu_chinh(dong_cua(goc), dc) if dc else ({}, {})
        ghi_hd(goc, sau=sau, ghi_chu_hd=ghi_chu_goc)
        for a in adjs:
            if a["id"] in da_ghi:
                continue
            ghi_hd(a, ghep=ghep, ghi_chu_hd="Thay thế toàn bộ HĐ gốc" if a["tthai"] == 2 else None)

    thu_tu = sorted(invoices, key=lambda i: (i["company_mst"], i["tdlap"] or "", i["khhdon"] or "",
                                             _int(i["shdon"]) if str(i["shdon"]).isdigit() else 0))
    for inv in thu_tu:
        if inv["id"] in da_ghi:
            continue
        if inv["tthai"] not in (2, 3):
            nhom(inv)
            continue
        # HĐ điều chỉnh / thay thế mà HĐ gốc thuộc kỳ khác (hiện cả nhóm tại vị trí này) hoặc chưa tải
        goc = find_goc(inv) if inv["goc_shdon"] else None
        if goc is not None and goc["id"] not in da_ghi:
            nhom(goc)
        if inv["id"] not in da_ghi:
            ghi_hd(inv, ghi_chu_hd=("HĐ gốc chưa có trong dữ liệu đã tải" if inv["goc_shdon"]
                                    else "Chưa có thông tin HĐ gốc"))
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, (int, float)) and c.column not in so_cot:
                dinh_dang_so(c)
    _fit(ws)
    ws.auto_filter.ref = ws.dimensions


# ---- Sheet tổng hợp để hạch toán: phần 1 theo loại, phần 2 theo mã hàng ----
HEADERS_TH_LOAI = ["Doanh nghiệp", "Chiều", "Phân loại", "TK gợi ý", "Số mặt hàng",
                   "Thành tiền chưa thuế", "Tiền thuế", "Tổng cộng"]
HEADERS_TH_MA = ["Doanh nghiệp", "Chiều", "Phân loại", "TK gợi ý", "MST người bán", "Tên người bán",
                 "Mã hàng", "Tên hàng hóa, dịch vụ", "ĐVT", "Số HĐ", "Số lượng", "Đơn giá bình quân",
                 "Thành tiền chưa thuế", "Tiền thuế", "Tổng cộng", "Phân loại"]


def _sheet_tong_hop(wb: Workbook, tong_hop: list[dict], invoices, items: dict, names) -> None:
    ws = wb.create_sheet("Tổng hợp hạch toán")
    bold = Font(bold=True)
    ws.append(["TỔNG HỢP THEO LOẠI ĐỂ HẠCH TOÁN"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append(["Không tính hóa đơn bị thay thế và bị hủy. Hóa đơn điều chỉnh được cộng theo số tiền ghi trên "
               "hóa đơn. Tài khoản chỉ là gợi ý; sửa phân loại ở trang Phân loại hàng hóa."])
    ws.append([])
    ws.append(HEADERS_TH_LOAI)
    for c in ws[ws.max_row]:
        c.font, c.fill = bold, GREY
    loai: dict = {}
    for r in tong_hop:
        k = (r["company_mst"], r["chieu"], r["ten_phan_loai"], r["tai_khoan"])
        v = loai.setdefault(k, [0, 0, 0])
        v[0] += 1
        v[1] += r["thanh_tien"]
        v[2] += r["tien_thue"]
    for (dn, chieu, ten, tk), (n, tt, thue) in loai.items():
        ws.append([names.get(dn, dn), "Mua vào" if chieu == "vao" else "Bán ra", ten, tk, n, tt, thue, tt + thue])

    # hóa đơn chưa có chi tiết hàng hóa: báo riêng để đối chiếu tổng
    thieu = [i for i in invoices if not items.get(i["id"]) and (i["tthai"] or 1) not in (4, 6)]
    if thieu:
        tien = sum(i["tgtcthue"] or 0 for i in thieu)
        ws.append([None, None, f"{len(thieu)} hóa đơn chưa có chi tiết hàng hóa (chưa tính ở trên)", None, None,
                   tien, None, None])
        for c in ws[ws.max_row]:
            c.fill = YELLOW

    ws.append([])
    ws.append(["CHI TIẾT THEO MÃ HÀNG"])
    ws.cell(ws.max_row, 1).font = Font(bold=True, size=13)
    ws.append(HEADERS_TH_MA[:-1] + ["Xác nhận phân loại"])
    dau = ws.max_row
    for c in ws[dau]:
        c.font, c.fill = bold, GREY
    for r in tong_hop:
        vao = r["chieu"] == "vao"
        ws.append([names.get(r["company_mst"], r["company_mst"]), "Mua vào" if vao else "Bán ra",
                   r["ten_phan_loai"], r["tai_khoan"], r["key_mst"] if vao else None, r["nguoi_ban"],
                   r["ma_hang"], r["ten_hang"], r["dvt"], r["so_hd"], r["so_luong"], r["don_gia_bq"],
                   r["thanh_tien"], r["tien_thue"], r["thanh_tien"] + r["tien_thue"],
                   "Đã xác nhận" if r["da_xac_nhan"] else "Tự gợi ý, cần xem"])
        if not r["da_xac_nhan"]:
            ws.cell(ws.max_row, len(HEADERS_TH_MA)).fill = YELLOW
    ws.auto_filter.ref = f"A{dau}:{get_column_letter(len(HEADERS_TH_MA))}{max(ws.max_row, dau)}"
    for row in ws.iter_rows(min_row=4):
        for c in row:
            if isinstance(c.value, (int, float)):
                dinh_dang_so(c)
    for i, w in enumerate([28, 10, 30, 9, 13, 28, 12, 34, 9, 8, 12, 14, 18, 14, 16, 20], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


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
