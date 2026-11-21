"""Giao diện web chạy trên máy: mở http://127.0.0.1:5000 bằng trình duyệt."""
from __future__ import annotations

import os
import zipfile
import io
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from thuedn import export
from thuedn.portal import PortalError, PortalSession, normalize
from thuedn.rules import (DS_RUI_RO, KET_LUAN, NGAY_TRA_LAI, TRANG_THAI_NCC, chia_thang,
                          danh_gia_doi_tac, muc_rui_ro, parse_danh_sach_mst, tinh_chat, to_date)
from thuedn.storage import Storage
from thuedn.xmlhd import hd_lien_quan_tu_zip

DATA_DIR = Path(os.environ.get("THUEDN_DATA", Path(__file__).parent / "data"))
VERIFY_SSL = os.environ.get("THUEDN_VERIFY_SSL", "1") != "0"

app = Flask(__name__)
app.secret_key = os.urandom(24)
store = Storage(DATA_DIR)

sessions: dict[str, PortalSession] = {}   # phiên đăng nhập cổng thuế theo MST, chỉ trong bộ nhớ
job: dict = {}                             # lượt tải hiện tại

app.jinja_env.globals.update(tinh_chat=tinh_chat, TRANG_THAI_NCC=TRANG_THAI_NCC,
                             KET_LUAN=KET_LUAN, DS_RUI_RO=DS_RUI_RO)


def han_tra_lai() -> str:
    return (datetime.now() - timedelta(days=NGAY_TRA_LAI)).strftime("%Y-%m-%d %H:%M")


def session_for(mst: str) -> PortalSession:
    if mst not in sessions:
        sessions[mst] = PortalSession(verify_ssl=VERIFY_SSL)
    return sessions[mst]


# ---------- 1. Danh sách doanh nghiệp ----------
@app.get("/")
def index():
    today = date.today()
    return render_template(
        "index.html", companies=store.companies(),
        can_tra_lai=len(store.due_rechecks(han_tra_lai())),
        trong_ds=store.suppliers_in_watchlist(),
        logged={m for m, s in sessions.items() if s.logged_in},
        tu=today.replace(day=1).isoformat(), den=today.isoformat(),
    )


@app.post("/companies")
def add_company():
    mst, name, pw = (request.form.get(k, "").strip() for k in ("mst", "name", "password"))
    if not (mst and name and pw):
        flash("Cần nhập đủ tên, MST và mật khẩu", "error")
    else:
        store.add_company(mst, name, pw)
        flash(f"Đã lưu {name}", "ok")
    return redirect(url_for("index"))


@app.post("/companies/<mst>/delete")
def delete_company(mst):
    store.delete_company(mst)
    sessions.pop(mst, None)
    flash("Đã xóa doanh nghiệp", "ok")
    return redirect(url_for("index"))


@app.post("/download")
def start_download():
    msts = request.form.getlist("mst")
    loai = request.form.getlist("loai")
    if not msts or not loai:
        flash("Chọn ít nhất một doanh nghiệp và một loại hóa đơn", "error")
        return redirect(url_for("index"))
    try:
        tu, den = to_date(request.form["tu"]), to_date(request.form["den"])
        chia_thang(tu, den)
    except (KeyError, ValueError) as e:
        flash(f"Khoảng ngày không hợp lệ: {e}", "error")
        return redirect(url_for("index"))
    job.clear()
    job.update(msts=msts, loai=loai, tu=tu, den=den, xml="xml" in request.form,
               pending=[m for m in msts if not session_for(m).logged_in], log=[])
    return redirect(url_for("captcha"))


# ---------- 2. Nhập captcha ----------
@app.get("/captcha")
def captcha():
    if not job:
        return redirect(url_for("index"))
    if not job["pending"]:
        run_downloads()
        return redirect(url_for("results"))
    mst = job["pending"][0]
    try:
        cap = session_for(mst).get_captcha()
    except Exception as e:  # mạng / cổng lỗi
        flash(f"Không lấy được captcha cho {mst}: {e}", "error")
        return render_template("captcha.html", mst=mst, name=store.company_name(mst), cap=None,
                               con_lai=len(job["pending"]))
    job["ckey"] = cap.key
    return render_template("captcha.html", mst=mst, name=store.company_name(mst), cap=cap,
                           con_lai=len(job["pending"]))


@app.post("/captcha")
def submit_captcha():
    mst = job["pending"][0]
    if "bo_qua" in request.form:
        job["pending"].pop(0)
        job["log"].append(f"{store.company_name(mst)}: bỏ qua")
        return redirect(url_for("captcha"))
    try:
        session_for(mst).login(mst, store.password(mst), job.get("ckey", ""),
                               request.form.get("cvalue", "").strip())
        job["pending"].pop(0)
    except (PortalError, Exception) as e:
        flash(f"{store.company_name(mst)}: {e}", "error")
    return redirect(url_for("captcha"))


def run_downloads() -> None:
    xml_dir = DATA_DIR / "xml"
    for mst in job["msts"]:
        s = sessions.get(mst)
        name = store.company_name(mst)
        if not s or not s.logged_in:
            continue
        dem = 0
        try:
            for tu, den in chia_thang(job["tu"], job["den"]):
                nguon = []
                if "vao" in job["loai"]:
                    nguon.append(("vao", s.purchase(tu, den)))
                if "ra" in job["loai"]:
                    nguon.append(("ra", s.sold(tu, den)))
                for direction, rows in nguon:
                    for row in rows:
                        inv = normalize(row)
                        store.save_invoice(mst, direction, inv)
                        dem += 1
                        if job["xml"]:
                            _save_xml(s, mst, direction, inv, xml_dir)
            job["log"].append(f"{name}: tải {dem} hóa đơn")
        except PortalError as e:
            job["log"].append(f"{name}: lỗi — {e}")
    store.ensure_suppliers_from_invoices()


def _save_xml(s: PortalSession, mst: str, direction: str, inv: dict, xml_dir: Path) -> None:
    rel = Path(mst) / direction / f"{inv['nbmst']}_{inv['khhdon']}_{inv['shdon']}.zip"
    target = xml_dir / rel
    if target.exists():
        return
    try:
        content = s.export_xml(inv)
    except PortalError:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    row = store.db.execute(
        "SELECT id FROM invoices WHERE company_mst=? AND direction=? AND nbmst=? AND khhdon=? AND shdon=?",
        (mst, direction, inv["nbmst"], inv["khhdon"], str(inv["shdon"]))).fetchone()
    if row:
        store.set_xml_path(row["id"], str(rel))
        lq = hd_lien_quan_tu_zip(content)
        if lq:
            store.set_goc(row["id"], lq)


# ---------- 3. Kết quả ----------
def _filtered():
    msts = request.args.getlist("mst") or job.get("msts") or [c["mst"] for c in store.companies()]
    tu = request.args.get("tu") or (job["tu"].isoformat() if job else None)
    den = request.args.get("den") or (job["den"].isoformat() if job else None)
    return msts, tu, den, store.invoices(msts, tu, den, request.args.get("chieu") or None)


@app.get("/results")
def results():
    msts, tu, den, rows = _filtered()
    sup = store.supplier_map()
    view = []
    for r in rows:
        s = sup.get(r["nbmst"]) if r["direction"] == "vao" else None
        muc = muc_rui_ro(s["status"] if s else None, s["ngay_ngung"] if s else None, r["tdlap"]) \
            if r["direction"] == "vao" else None
        view.append((r, s, muc))
    names = {c["mst"]: c["name"] for c in store.companies()}
    return render_template("results.html", rows=view, names=names, log=job.get("log", []),
                           msts=msts, tu=tu, den=den, chieu=request.args.get("chieu", ""))


@app.get("/export.xlsx")
def export_excel():
    _, tu, den, rows = _filtered()
    names = {c["mst"]: c["name"] for c in store.companies()}
    data = export.bang_ke_excel(
        rows, store.supplier_map(), names,
        find_goc=lambda i: store.find_invoice(i["company_mst"], i["direction"], i["nbmst"],
                                              i["goc_khmshdon"], i["goc_khhdon"], i["goc_shdon"]),
        find_adjusting=store.find_adjusting)
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"bang-ke_{tu}_{den}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/export-xml.zip")
def export_xml():
    _, tu, den, rows = _filtered()
    data = export.zip_xml(rows, DATA_DIR / "xml")
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"xml_{tu}_{den}.zip", mimetype="application/zip")


# ---------- 4. Kiểm tra nhà cung cấp ----------
@app.get("/suppliers")
def suppliers():
    store.ensure_suppliers_from_invoices()
    return render_template("suppliers.html", rows=store.suppliers())


@app.post("/suppliers/<mst>")
def update_supplier(mst):
    status = request.form.get("status", "chua_tra")
    if status not in TRANG_THAI_NCC:
        flash("Trạng thái không hợp lệ", "error")
    else:
        store.update_supplier(mst, status, request.form.get("ngay_ngung"),
                              request.form.get("nguon", "nhap_tay"),
                              datetime.now().strftime("%Y-%m-%d %H:%M"))
        flash(f"Đã cập nhật {mst}", "ok")
    return redirect(url_for("suppliers") + f"#ncc-{mst}")



# ---------- 5. Kiểm tra đối tác (trước khi ký hợp đồng / trước khi nhận hóa đơn) ----------
@app.get("/doi-tac")
def doi_tac():
    mst = request.args.get("mst", "").strip()
    prefill = None
    if mst:
        prefill = store.latest_partner_check(mst) or store.supplier_map().get(mst)
    return render_template(
        "doi_tac.html", mst=mst, prefill=prefill,
        hits=store.watchlist_hits(mst) if mst else [],
        recent=store.partner_checks(limit=50),
        due=store.due_rechecks(han_tra_lai()), ngay_tra_lai=NGAY_TRA_LAI,
        trong_ds=store.suppliers_in_watchlist(),
        ds_summary={r["loai"]: r for r in store.watchlist_summary()},
    )


@app.post("/doi-tac")
def luu_doi_tac():
    f = request.form
    mst = f.get("mst", "").strip()
    status = f.get("status", "chua_tra")
    if not mst or status not in TRANG_THAI_NCC:
        flash("Cần nhập MST và chọn trạng thái hợp lệ", "error")
        return redirect(url_for("doi_tac", mst=mst))
    ngay_tl = f.get("ngay_thanh_lap") or None
    try:
        if ngay_tl:
            to_date(ngay_tl)
    except ValueError:
        flash("Ngày thành lập không hợp lệ", "error")
        return redirect(url_for("doi_tac", mst=mst))
    nganh_khop = {"1": 1, "0": 0}.get(f.get("nganh_khop", ""))
    nguon = f.get("nguon", "nhap_tay")
    ds = [r["loai"] for r in store.watchlist_hits(mst)]
    ket_luan, ly_do = danh_gia_doi_tac(status, ngay_tl, nganh_khop, ds, nguon, date.today())
    store.add_partner_check({
        "mst": mst, "ten": f.get("ten", "").strip(), "status": status,
        "ngay_ngung": f.get("ngay_ngung") or None, "ngay_thanh_lap": ngay_tl,
        "dia_chi": f.get("dia_chi", "").strip(), "nguoi_dai_dien": f.get("nguoi_dai_dien", "").strip(),
        "nganh_nghe": f.get("nganh_nghe", "").strip(), "nganh_khop": nganh_khop, "nguon": nguon,
        "ghi_chu": f.get("ghi_chu", "").strip(), "ds_rui_ro": ",".join(ds),
        "ket_luan": ket_luan, "ly_do": "; ".join(ly_do),
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    return redirect(url_for("phieu_doi_tac", mst=mst))


@app.get("/doi-tac/<mst>")
def phieu_doi_tac(mst):
    checks = store.partner_checks(mst)
    if not checks:
        return redirect(url_for("doi_tac", mst=mst))
    return render_template("phieu_doi_tac.html", mst=mst, c=checks[0], history=checks,
                           hits=store.watchlist_hits(mst), mua=store.purchase_summary(mst),
                           qua_han=checks[0]["checked_at"] < han_tra_lai())


@app.get("/doi-tac/<mst>/phieu.xlsx")
def phieu_excel(mst):
    data = export.phieu_kiem_tra(mst, store.partner_checks(mst), store.purchase_summary(mst))
    return send_file(io.BytesIO(data), as_attachment=True, download_name=f"phieu-kiem-tra_{mst}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/danh-sach-rui-ro")
def nhap_danh_sach():
    loai = request.form.get("loai")
    if loai not in DS_RUI_RO:
        flash("Chọn loại danh sách", "error")
        return redirect(url_for("doi_tac"))
    text = request.form.get("noi_dung", "")
    up = request.files.get("tep")
    if up and up.filename:
        raw = up.read()
        if up.filename.lower().endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            text += "\n" + "\n".join(
                "\t".join("" if v is None else str(v) for v in row[:2])
                for ws in wb.worksheets for row in ws.iter_rows(values_only=True))
        else:
            text += "\n" + raw.decode("utf-8-sig", errors="replace")
    rows = parse_danh_sach_mst(text)
    if not rows:
        flash("Không tìm thấy MST nào. Mỗi dòng cần bắt đầu bằng MST 10 số.", "error")
        return redirect(url_for("doi_tac"))
    n = store.import_watchlist(loai, rows, request.form.get("nguon", "").strip(),
                               datetime.now().strftime("%Y-%m-%d %H:%M"))
    flash(f"Đã nhập {n} MST vào danh sách {DS_RUI_RO[loai]}", "ok")
    return redirect(url_for("doi_tac"))


if __name__ == "__main__":
    print("Mở trình duyệt vào: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
