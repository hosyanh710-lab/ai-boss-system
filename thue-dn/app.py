"""Giao diện web chạy trên máy: mở http://127.0.0.1:5000 bằng trình duyệt."""
from __future__ import annotations

import os
import zipfile
import io
from datetime import date, datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from thuedn import export
from thuedn.portal import PortalError, PortalSession, normalize
from thuedn.rules import TRANG_THAI_NCC, chia_thang, muc_rui_ro, tinh_chat, to_date
from thuedn.storage import Storage

DATA_DIR = Path(os.environ.get("THUEDN_DATA", Path(__file__).parent / "data"))
VERIFY_SSL = os.environ.get("THUEDN_VERIFY_SSL", "1") != "0"

app = Flask(__name__)
app.secret_key = os.urandom(24)
store = Storage(DATA_DIR)

sessions: dict[str, PortalSession] = {}   # phiên đăng nhập cổng thuế theo MST, chỉ trong bộ nhớ
job: dict = {}                             # lượt tải hiện tại

app.jinja_env.globals.update(tinh_chat=tinh_chat, TRANG_THAI_NCC=TRANG_THAI_NCC)


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
    data = export.bang_ke_excel(rows, store.supplier_map(), names)
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


if __name__ == "__main__":
    print("Mở trình duyệt vào: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
