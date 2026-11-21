"""Cộng gộp dòng hàng hóa theo mặt hàng và theo loại hạch toán."""
from __future__ import annotations

from collections import Counter

from .rules import PHAN_LOAI, goi_y_phan_loai, ma_key


def _tien_thue(thanh_tien, thue_suat):
    if thanh_tien is None or not thue_suat:
        return 0
    try:
        return round(thanh_tien * float(str(thue_suat).strip().rstrip("%")) / 100)
    except ValueError:
        return 0


def tong_hop_mat_hang(lines, categories: dict, theo_dn: bool = True) -> list[dict]:
    """Mỗi phần tử: một mặt hàng (theo DN nếu theo_dn, chiều, người bán / DN, mã hàng)."""
    nhom: dict = {}
    for d in lines:
        chieu = d["direction"]
        key_mst = d["nbmst"] if chieu == "vao" else d["company_mst"]
        mk = ma_key(d["ma_hang"], d["ten_hang"])
        k = (d["company_mst"] if theo_dn else "", chieu, key_mst, mk)
        g = nhom.get(k)
        if g is None:
            g = nhom[k] = {
                "company_mst": d["company_mst"], "chieu": chieu, "key_mst": key_mst, "ma_key": mk,
                "ma_hang": d["ma_hang"], "nguoi_ban": d["nbten"] if chieu == "vao" else None,
                "ten": Counter(), "dvt": Counter(), "tinh_chat": Counter(), "hd": set(),
                "so_luong": 0, "thanh_tien": 0, "tien_thue": 0,
            }
        g["ten"][d["ten_hang"] or ""] += 1
        if d["dvt"]:
            g["dvt"][d["dvt"]] += 1
        if d["tinh_chat"]:
            g["tinh_chat"][d["tinh_chat"]] += 1
        g["hd"].add(d["hd_id"])
        g["so_luong"] += d["so_luong"] or 0
        g["thanh_tien"] += d["thanh_tien"] or 0
        g["tien_thue"] += _tien_thue(d["thanh_tien"], d["thue_suat"])

    out = []
    for g in nhom.values():
        ten = g["ten"].most_common(1)[0][0] or None
        dvt = g["dvt"].most_common(1)[0][0] if g["dvt"] else None
        tc = g["tinh_chat"].most_common(1)[0][0] if g["tinh_chat"] else None
        da_chon = categories.get((g["chieu"], g["key_mst"], g["ma_key"]))
        if da_chon is not None and da_chon["phan_loai"] in PHAN_LOAI[g["chieu"]]:
            pl, tk, xn = da_chon["phan_loai"], da_chon["tai_khoan"], True
        else:
            pl = goi_y_phan_loai(g["chieu"], ten, dvt, tc)
            tk, xn = PHAN_LOAI[g["chieu"]][pl][1], False
        out.append({
            "company_mst": g["company_mst"], "chieu": g["chieu"], "key_mst": g["key_mst"],
            "ma_key": g["ma_key"], "ma_hang": g["ma_hang"], "ten_hang": ten, "dvt": dvt,
            "nguoi_ban": g["nguoi_ban"], "so_hd": len(g["hd"]), "so_luong": g["so_luong"],
            "don_gia_bq": round(g["thanh_tien"] / g["so_luong"]) if g["so_luong"] else None,
            "thanh_tien": g["thanh_tien"], "tien_thue": g["tien_thue"],
            "phan_loai": pl, "ten_phan_loai": PHAN_LOAI[g["chieu"]][pl][0], "tai_khoan": tk or "",
            "da_xac_nhan": xn,
        })
    thu_tu = {c: i for chieu in PHAN_LOAI for i, c in enumerate(PHAN_LOAI[chieu])}
    out.sort(key=lambda r: (r["company_mst"], r["chieu"] != "vao", thu_tu[r["phan_loai"]],
                            r["key_mst"], r["ten_hang"] or ""))
    return out
