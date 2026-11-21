"""Tạo file Excel chứng từ đã hạch toán sẵn để nhập khẩu vào MISA (ASP / AMIS Kế toán).

Mỗi dòng hàng hóa của hóa đơn là một dòng chứng từ: TK Nợ / TK Có / TK thuế lấy từ phân loại hàng hóa.
Các dòng cùng hóa đơn có cùng Số chứng từ để MISA gộp thành một chứng từ.

TÊN CỘT là bản tạm, đặt theo mẫu nhập khẩu thường gặp của MISA. Khi có file mẫu nhập khẩu thật từ
MISA ASP của anh/chị, chỉ cần sửa COT_MUA_HANG / COT_BAN_HANG bên dưới cho đúng tên và thứ tự cột.
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .export import dinh_dang_so
from .rules import bang_phan_loai, goi_y_phan_loai, ma_key, tinh_chat

# (tên cột trong file nhập MISA, khóa dữ liệu)
COT_MUA_HANG = [
    ("Ngày hạch toán (*)", "ngay_ht"), ("Ngày chứng từ (*)", "ngay_ct"), ("Số chứng từ (*)", "so_ct"),
    ("Mã nhà cung cấp", "ma_dt"), ("Tên nhà cung cấp", "ten_dt"), ("Mã số thuế", "mst_dt"),
    ("Diễn giải", "dien_giai"), ("Mẫu số HĐ", "mau_hd"), ("Ký hiệu HĐ", "ky_hieu"), ("Số hóa đơn", "so_hd"),
    ("Ngày hóa đơn", "ngay_hd"), ("Mã hàng (*)", "ma_hang"), ("Tên hàng", "ten_hang"), ("Mã kho", "kho"),
    ("TK nợ (*)", "tk_no"), ("TK có (*)", "tk_co"), ("ĐVT", "dvt"), ("Số lượng", "so_luong"),
    ("Đơn giá", "don_gia"), ("Thành tiền", "thanh_tien"), ("% thuế GTGT", "thue_suat"),
    ("Tiền thuế GTGT", "tien_thue"), ("TK thuế GTGT", "tk_thue"),
]
COT_BAN_HANG = [
    ("Ngày hạch toán (*)", "ngay_ht"), ("Ngày chứng từ (*)", "ngay_ct"), ("Số chứng từ (*)", "so_ct"),
    ("Mã khách hàng", "ma_dt"), ("Tên khách hàng", "ten_dt"), ("Mã số thuế", "mst_dt"),
    ("Diễn giải", "dien_giai"), ("Mẫu số HĐ", "mau_hd"), ("Ký hiệu HĐ", "ky_hieu"), ("Số hóa đơn", "so_hd"),
    ("Ngày hóa đơn", "ngay_hd"), ("Mã hàng (*)", "ma_hang"), ("Tên hàng", "ten_hang"), ("Mã kho", "kho"),
    ("TK nợ (*)", "tk_no"), ("TK có (*)", "tk_co"), ("ĐVT", "dvt"), ("Số lượng", "so_luong"),
    ("Đơn giá", "don_gia"), ("Thành tiền", "thanh_tien"), ("% thuế GTGT", "thue_suat"),
    ("Tiền thuế GTGT", "tien_thue"), ("TK thuế GTGT", "tk_thue"),
]
TK_CONG_NO = {"vao": "331", "ra": "131"}
YELLOW = PatternFill("solid", fgColor="FFF3CD")


def _thue_suat(ts: str | None):
    if not ts:
        return None
    t = str(ts).strip()
    if t.endswith("%"):
        try:
            f = float(t[:-1])
            return int(f) if f.is_integer() else f
        except ValueError:
            return t
    return t                                        # KCT, KKKNT…


def _tien_thue(thanh_tien, ts) -> int | None:
    if thanh_tien is None or not isinstance(ts, (int, float)):
        return 0 if ts in ("KCT", "KKKNT") else None
    return round(thanh_tien * ts / 100)


def _ngay(d: str | None) -> str | None:
    return "/".join(reversed(d.split("-"))) if d else None      # 2026-10-05 → 05/10/2026


def chung_tu(invoices, items_for, categories: dict, che_do: str = "TT133"):
    """Trả về (dòng mua hàng, dòng bán hàng, cần xem, không nhập)."""
    bang = bang_phan_loai(che_do)
    mua, ban, can_xem, bo_qua = [], [], [], []
    for inv in sorted(invoices, key=lambda i: (i["direction"], i["tdlap"] or "", i["khhdon"] or "", str(i["shdon"]))):
        vao = inv["direction"] == "vao"
        so_hd = int(inv["shdon"]) if str(inv["shdon"]).isdigit() else inv["shdon"]
        ten_hd = f"HĐ {inv['khhdon']} số {so_hd}"
        if inv["tthai"] == 4:
            bo_qua.append((inv, "Hóa đơn đã bị thay thế: nhập hóa đơn thay thế thay cho hóa đơn này"))
            continue
        if inv["tthai"] == 6:
            bo_qua.append((inv, "Hóa đơn đã bị hủy"))
            continue
        doi_tac_mst = inv["nbmst"] if vao else inv["nmmst"]
        doi_tac_ten = inv["nbten"] if vao else inv["nmten"]
        dien_giai = (f"Mua hàng của {doi_tac_ten} theo {ten_hd}" if vao
                     else f"Bán hàng cho {doi_tac_ten} theo {ten_hd}")
        if inv["tthai"] in (2, 3) and inv["goc_shdon"]:
            goc = f"HĐ {inv['goc_khhdon'] or ''} số {inv['goc_shdon']}"
            dien_giai += f" ({'thay thế' if inv['tthai'] == 2 else 'điều chỉnh cho'} {goc})"
        dau = {
            "ngay_ht": _ngay(inv["tdlap"]), "ngay_ct": _ngay(inv["tdlap"]),
            "so_ct": f"{'MV' if vao else 'BR'}-{inv['khhdon']}-{so_hd}",
            "ma_dt": doi_tac_mst, "ten_dt": doi_tac_ten, "mst_dt": doi_tac_mst, "dien_giai": dien_giai,
            "mau_hd": inv["khmshdon"], "ky_hieu": inv["khhdon"], "so_hd": so_hd, "ngay_hd": _ngay(inv["tdlap"]),
        }
        dich = mua if vao else ban
        dong = items_for(inv["id"])
        if not dong:
            r = dict(dau, ten_hang=f"Theo {ten_hd}", thanh_tien=inv["tgtcthue"], tien_thue=inv["tgtthue"],
                     tk_no=None if vao else TK_CONG_NO["ra"], tk_co=TK_CONG_NO["vao"] if vao else None,
                     tk_thue="1331" if vao else "33311")
            r["_canh_bao"] = "Chưa có chi tiết hàng hóa (tải kèm XML) nên chưa biết TK; điền TK trước khi nhập"
            dich.append(r)
            can_xem.append((r, inv))
            continue
        key_mst = inv["nbmst"] if vao else inv["company_mst"]
        for d in dong:
            if d["tinh_chat"] == "Ghi chú, diễn giải":
                continue
            mk = ma_key(d["ma_hang"], d["ten_hang"])
            cat = categories.get(("vao" if vao else "ra", key_mst, mk))
            if cat is not None and cat["phan_loai"] in bang[inv["direction"]]:
                pl, tk, xn = cat["phan_loai"], cat["tai_khoan"], True
                ma_misa, kho = cat["ma_misa"], cat["kho"]
            else:
                pl = goi_y_phan_loai(inv["direction"], d["ten_hang"], d["dvt"], d["tinh_chat"])
                tk, xn, ma_misa, kho = bang[inv["direction"]][pl][1], False, None, None
            if pl == "khong_tinh":
                continue
            ts = _thue_suat(d["thue_suat"])
            r = dict(dau, ma_hang=ma_misa or d["ma_hang"], ten_hang=d["ten_hang"], kho=kho, dvt=d["dvt"],
                     so_luong=d["so_luong"], don_gia=d["don_gia"], thanh_tien=d["thanh_tien"],
                     thue_suat=ts, tien_thue=_tien_thue(d["thanh_tien"], ts),
                     tk_no=tk if vao else TK_CONG_NO["ra"], tk_co=TK_CONG_NO["vao"] if vao else tk,
                     tk_thue=("1332" if pl == "tscd" else "1331") if vao else "33311")
            ly_do = []
            if not tk:
                ly_do.append(f"Chưa có TK cho loại \"{bang[inv['direction']][pl][0]}\"")
            if not xn:
                ly_do.append("Phân loại tự gợi ý, chưa xác nhận")
            if not r["ma_hang"]:
                ly_do.append("Thiếu mã hàng")
            if ly_do:
                r["_canh_bao"] = "; ".join(ly_do)
                can_xem.append((r, inv))
            dich.append(r)
    return mua, ban, can_xem, bo_qua


def file_misa(invoices, items_for, categories: dict, che_do: str = "TT133") -> bytes:
    mua, ban, can_xem, bo_qua = chung_tu(invoices, items_for, categories, che_do)
    wb = Workbook()
    wb.remove(wb.active)
    for title, cot, rows in (("Mua hàng", COT_MUA_HANG, mua), ("Bán hàng", COT_BAN_HANG, ban)):
        ws = wb.create_sheet(title)
        ws.append([c for c, _ in cot])
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r.get(k) for _, k in cot])
            if r.get("_canh_bao"):
                for c in ws[ws.max_row]:
                    c.fill = YELLOW
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, (int, float)) and cot[c.column - 1][1] in ("so_luong", "don_gia",
                                                                                  "thanh_tien", "tien_thue"):
                    dinh_dang_so(c)
        for i, (h, _) in enumerate(cot, start=1):
            ws.column_dimensions[get_column_letter(i)].width = max(12, min(40, len(h) + 4))
        ws.freeze_panes = "A2"

    ws = wb.create_sheet("Kiểm tra trước khi nhập")
    ws.append(["Chiều", "Số chứng từ", "Số hóa đơn", "Đối tác", "Tên hàng", "Thành tiền", "Cần xem"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for r, inv in can_xem:
        ws.append(["Mua vào" if inv["direction"] == "vao" else "Bán ra", r["so_ct"], r["so_hd"], r["ten_dt"],
                   r.get("ten_hang"), r.get("thanh_tien"), r["_canh_bao"]])
    for inv, ly_do in bo_qua:
        ws.append(["Mua vào" if inv["direction"] == "vao" else "Bán ra", None,
                   int(inv["shdon"]) if str(inv["shdon"]).isdigit() else inv["shdon"],
                   inv["nbten"] if inv["direction"] == "vao" else inv["nmten"], tinh_chat(inv["tthai"]),
                   inv["tgtcthue"], "KHÔNG NHẬP: " + ly_do])
    if ws.max_row == 1:
        ws.append([None, None, None, None, None, None, "Không có gì cần xem. Có thể nhập khẩu vào MISA."])
    for (c,) in ws.iter_rows(min_row=2, min_col=6, max_col=6):
        if isinstance(c.value, (int, float)):
            c.number_format = "#,##0"
    for i, w in enumerate([10, 24, 12, 34, 34, 16, 70], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
