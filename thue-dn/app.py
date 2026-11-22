"""Giao diện web chạy trên máy: mở http://127.0.0.1:5000 bằng trình duyệt."""
from __future__ import annotations

import os
import threading
import zipfile
import io
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from thuedn import excel_cong, export, gdrive, misa
from thuedn.portal import KhongCoXML, PortalError, PortalSession, normalize
from thuedn.rules import (CHE_DO_KE_TOAN, DS_RUI_RO, KET_LUAN, NGAY_TRA_LAI, PHAN_LOAI, TRANG_THAI_NCC, chia_thang,
                          bang_phan_loai, danh_gia_doi_tac, muc_rui_ro, parse_danh_sach_mst, tinh_chat, to_date)
from thuedn.storage import Storage
from thuedn.xmlhd import doc_zip
from thuedn.quyen import VAI_TRO, co_quyen, gan_duoc, kiem_tra_mat_khau, quan_ly_duoc
from thuedn.tonghop import tong_hop_mat_hang

DATA_DIR = Path(os.environ.get("THUEDN_DATA", Path(__file__).parent / "data"))
VERIFY_SSL = os.environ.get("THUEDN_VERIFY_SSL", "1") != "0"

app = Flask(__name__)
store = Storage(DATA_DIR)
_key = DATA_DIR / "session.key"                 # khóa ký phiên đăng nhập, giữ qua các lần mở lại
if not _key.exists():
    _key.write_bytes(os.urandom(32))
app.secret_key = _key.read_bytes()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=timedelta(days=30))

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
    mst, name, pw, email = (request.form.get(k, "").strip() for k in ("mst", "name", "password", "email"))
    if not (mst and name and pw):
        flash("Cần nhập đủ tên, MST và mật khẩu", "error")
    elif email and "@" not in email:
        flash("Email không hợp lệ", "error")
    else:
        store.add_company(mst, name, pw, email)
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
    if job.get("trang_thai") == "dang_chay":
        flash("Đang có một lượt tải chạy, chờ xong rồi tải tiếp", "error")
        return redirect(url_for("dang_tai"))
    job.clear()
    job.update(msts=msts, loai=loai, tu=tu, den=den, xml="xml" in request.form, drive="drive" in request.form,
               pending=[m for m in msts if not session_for(m).logged_in], log=[], trang_thai="cho_captcha",
               tien_do="", mtt="mtt" in request.form and "ra" in loai, xml_mtt="xml_mtt" in request.form,
               mtt_pending=None, mtt_inv={})
    return redirect(url_for("captcha"))


# ---------- 2. Nhập captcha ----------
@app.get("/captcha")
def captcha():
    if not job:
        return redirect(url_for("index"))
    buoc = None
    if job["pending"]:
        mst = job["pending"][0]
    else:
        _lap_buoc_mtt()
        if not job.get("mtt_pending"):
            bat_dau_tai()
            return redirect(url_for("dang_tai"))
        buoc = job["mtt_pending"][0]
        mst = buoc["mst"]
    xem = dict(mst=mst, name=store.company_name(mst), con_lai=len(job["pending"]), buoc=buoc)
    try:
        cap = session_for(mst).get_captcha()
    except Exception as e:  # mạng / cổng lỗi
        flash(f"Không lấy được captcha cho {mst}: {e}", "error")
        return render_template("captcha.html", cap=None, **xem)
    job["ckey"] = cap.key
    return render_template("captcha.html", cap=cap, **xem)


def _lap_buoc_mtt() -> None:
    """Sau khi đăng nhập xong: mỗi DN × mỗi tháng một bước tra HĐ bán ra từ máy tính tiền."""
    if job.get("mtt_pending") is not None:
        return
    job["mtt_pending"] = [
        {"mst": m, "tu": tu, "den": den, "state": None, "trang": 1, "da_tai": 0, "tong": None, "kieu": "excel"}
        for m in job["msts"] if job.get("mtt") and sessions.get(m) and sessions[m].logged_in
        for tu, den in chia_thang(job["tu"], job["den"])]


def _tra_mtt(cvalue: str) -> None:
    """Tra một trang HĐ máy tính tiền bằng captcha vừa gõ; lưu ngay, XML để lượt tải ngầm."""
    b = job["mtt_pending"][0]
    s = sessions[b["mst"]]
    if b["kieu"] == "excel":
        try:
            noi_dung = s.sold_mtt_excel(b["tu"], b["den"], job.get("ckey", ""), cvalue)
        except PortalError as e:
            if "captcha" in str(e).lower() or "xác thực" in str(e).lower() or s.token is None:
                raise
            b["kieu"] = "trang"          # cổng không cho xuất Excel: tra từng trang 50 HĐ như trang web
            raise PortalError(f"Không xuất được Excel ({e}). Chuyển sang tra từng trang 50 hóa đơn, "
                              "gõ captcha mới để tra tiếp.") from e
        tep = DATA_DIR / "mtt" / b["mst"] / f"ban-ra-mtt_{b['tu']:%Y-%m-%d}_{b['den']:%Y-%m-%d}.xlsx"
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_bytes(noi_dung)                          # giữ file gốc của cổng để đối chiếu
        try:
            dong = excel_cong.doc_danh_sach(noi_dung, b["mst"], store.company_name(b["mst"]))
        except Exception as e:
            app.logger.exception("Đọc Excel HĐ máy tính tiền")
            job["mtt_pending"].pop(0)
            job["log"].append(f"{store.company_name(b['mst'])}: đã tải Excel HĐ máy tính tiền {b['tu']:%m/%Y} "
                              f"nhưng chưa đọc được ({e}). File lưu ở {tep}")
            return
        for row in dong:
            inv = normalize(row)
            store.save_invoice(b["mst"], "ra", inv)
            job["mtt_inv"].setdefault(b["mst"], []).append(inv)
        job["mtt_pending"].pop(0)
        job["log"].append(f"{store.company_name(b['mst'])}: {len(dong)} hóa đơn bán ra từ máy tính tiền "
                          f"({b['tu']:%m/%Y}, lấy bằng Excel của cổng, 1 captcha)")
        return
    rows, nxt, tong = s.sold_mtt_page(b["tu"], b["den"], b["state"], job.get("ckey", ""), cvalue)
    for row in rows:
        inv = normalize(row)
        store.save_invoice(b["mst"], "ra", inv)
        job["mtt_inv"].setdefault(b["mst"], []).append(inv)
    b.update(da_tai=b["da_tai"] + len(rows), tong=tong)
    if nxt and rows:
        b.update(state=nxt, trang=b["trang"] + 1)
    else:
        job["mtt_pending"].pop(0)
        job["log"].append(f"{store.company_name(b['mst'])}: {b['da_tai']} hóa đơn bán ra từ máy tính tiền "
                          f"({b['tu']:%m/%Y})")


@app.post("/captcha")
def submit_captcha():
    if job and not job.get("pending") and job.get("mtt_pending") and job.get("trang_thai") == "cho_captcha":
        if not _khoa_mtt.acquire(blocking=False):
            return redirect(url_for("captcha"))      # bấm 2 lần khi cổng đang tạo Excel: bỏ qua lần sau
        try:
            b = job["mtt_pending"][0]
            if "bo_qua" in request.form:
                job["mtt_pending"].pop(0)
                job["log"].append(f"{store.company_name(b['mst'])}: bỏ qua HĐ máy tính tiền {b['tu']:%m/%Y}")
            else:
                try:
                    _tra_mtt(request.form.get("cvalue", "").strip())
                except PortalError as e:
                    flash(f"{store.company_name(b['mst'])}: {e}", "error")
        finally:
            _khoa_mtt.release()
        return redirect(url_for("captcha"))
    if not job or not job.get("pending"):
        # Form gửi lại lần 2 (bấm 2 lần / tải lại trang) khi đã đăng nhập xong: chỉ cần đi tiếp
        return redirect(url_for("captcha") if job else url_for("index"))
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


_khoa_tai = threading.Lock()
_khoa_mtt = threading.Lock()


def bat_dau_tai() -> None:
    """Tải chạy ngầm, mỗi lúc chỉ một lượt: tải hàng trăm XML mất vài phút (cổng giới hạn tốc độ),
    trang chờ không được giữ request lâu (bị gửi lại nhiều lần → nhiều lượt tải đè nhau)."""
    if not _khoa_tai.acquire(blocking=False):
        return                                    # đang có lượt tải chạy
    if job.get("trang_thai") in ("dang_chay", "xong"):
        _khoa_tai.release()
        return
    job["trang_thai"] = "dang_chay"

    def chay():
        try:
            run_downloads()
        except Exception as e:                    # pragma: no cover - lỗi bất ngờ vẫn phải mở khóa
            app.logger.exception("Lỗi khi tải hóa đơn")
            job["log"].append(f"Lỗi khi tải: {e}")
        finally:
            job["trang_thai"] = "xong"
            _khoa_tai.release()

    if app.testing:
        chay()
    else:
        threading.Thread(target=chay, name="tai-hoa-don", daemon=True).start()


@app.get("/dang-tai")
def dang_tai():
    if not job:
        return redirect(url_for("index"))
    if job.get("trang_thai") != "dang_chay":
        return redirect(url_for("results") if job.get("trang_thai") == "xong" else url_for("captcha"))
    return render_template("dang_tai.html", log=job["log"], tien_do=job.get("tien_do", ""))


def run_downloads() -> None:
    xml_dir = DATA_DIR / "xml"
    for mst in job["msts"]:
        s = sessions.get(mst)
        name = store.company_name(mst)
        if not s or not s.logged_in:
            continue
        dem = thieu_xml = khong_co_xml = 0
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
                            kq = _save_xml(s, mst, direction, inv, xml_dir)
                            thieu_xml += kq is False
                            khong_co_xml += kq is None
                        job["tien_do"] = f"{name}: {dem} hóa đơn" + (" (kèm XML)" if job["xml"] else "")
            mtt = job.get("mtt_inv", {}).get(mst, []) if job.get("xml_mtt") else []
            for i, inv in enumerate(mtt, 1):
                kq = _save_xml(s, mst, "ra", inv, xml_dir)
                thieu_xml += kq is False
                khong_co_xml += kq is None
                job["tien_do"] = f"{name}: XML hóa đơn máy tính tiền {i}/{len(mtt)}"
            job["log"].append(f"{name}: tải {dem} hóa đơn" + (
                f"; {thieu_xml} hóa đơn chưa tải được XML — bấm Tải hóa đơn lại để lấy tiếp" if thieu_xml else "") + (
                f"; {khong_co_xml} hóa đơn cổng thuế không có XML (thường là HĐ không mã của EVN, viễn thông…)"
                if khong_co_xml else ""))
        except PortalError as e:
            job["log"].append(f"{name}: lỗi — {e}")
    store.ensure_suppliers_from_invoices()
    if job.get("drive"):
        for mst in job["msts"]:
            s = sessions.get(mst)
            if not s or not s.logged_in:
                continue
            name = store.company_name(mst)
            if not store.google_token(mst):
                job["log"].append(f"{name}: chưa kết nối Google Drive, không đẩy file")
                continue
            try:
                job["log"].append(f"{name}: {day_len_drive(mst, job['tu'].isoformat(), job['den'].isoformat())}")
            except gdrive.DriveError as e:
                job["log"].append(f"{name}: KHÔNG đẩy lên Drive — {e}")


def _save_xml(s: PortalSession, mst: str, direction: str, inv: dict, xml_dir: Path) -> bool | None:
    """True: có XML. False: chưa tải được (lần tải sau thử lại). None: cổng không có XML hóa đơn này."""
    rel = Path(mst) / direction / f"{inv['nbmst']}_{inv['khhdon']}_{inv['shdon']}.zip"
    target = xml_dir / rel
    khong_co = target.with_suffix(".khong-co-xml")
    raw = inv.get("raw") or {}
    if khong_co.exists() or ("hsgoc" in raw and not raw["hsgoc"]):
        # hsgoc rỗng trong danh sách cổng = cổng không lưu XML hóa đơn này (đã đối chiếu 116/116 HĐ thật)
        return None
    if target.exists():
        content = target.read_bytes()            # đã tải trước đây: đọc lại, không tải lại
    else:
        try:
            content = s.export_xml(inv)
        except KhongCoXML:
            khong_co.parent.mkdir(parents=True, exist_ok=True)
            khong_co.write_text("Cổng thuế: Không tồn tại hồ sơ gốc của hóa đơn", encoding="utf-8")
            return None
        except PortalError:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    row = store.db.execute(
        "SELECT id FROM invoices WHERE company_mst=? AND direction=? AND nbmst=? AND khhdon=? AND shdon=?",
        (mst, direction, inv["nbmst"], inv["khhdon"], str(inv["shdon"]))).fetchone()
    if row:
        luu_xml(row["id"], str(rel), content)
    return True


def luu_xml(invoice_id: int, rel: str, content: bytes) -> None:
    """Ghi đường dẫn XML, thông tin HĐ gốc / nội dung điều chỉnh và các dòng hàng hóa."""
    store.set_xml_path(invoice_id, rel)
    lq, hang = doc_zip(content)
    if lq:
        store.set_goc(invoice_id, lq)
    if hang:
        store.set_items(invoice_id, hang)


# ---------- 3. Kết quả ----------
def _filtered():
    msts = [m for m in request.args.getlist("mst") if m] or job.get("msts") or [c["mst"] for c in store.companies()]
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
                           msts=msts, tu=tu, den=den, chieu=request.args.get("chieu", ""),
                           companies=store.companies())


@app.get("/export.xlsx")
def export_excel():
    msts, tu, den, rows = _filtered()
    data = _excel(msts, tu, den, rows)
    ten = f"{msts[0]}_" if len(msts) == 1 else ""
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"bang-ke_{ten}{tu}_{den}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _excel(msts: list[str], tu, den, rows) -> bytes:
    names = {c["mst"]: c["name"] for c in store.companies()}
    return export.bang_ke_excel(
        rows, store.supplier_map(), names,
        items=store.items_by_invoice([r["id"] for r in rows]),
        items_for=store.items_by_invoice,
        tong_hop=tong_hop_mat_hang(store.item_lines(msts, tu, den), store.categories(), che_do=che_do()),
        find_goc=lambda i: store.find_invoice(i["company_mst"], i["direction"], i["nbmst"],
                                              i["goc_khmshdon"], i["goc_khhdon"], i["goc_shdon"]),
        find_adjusting=store.find_adjusting)


def _ten_file(s: str) -> str:
    """Tên công ty → tên file an toàn trên Windows (giữ tiếng Việt, bỏ ký tự cấm)."""
    import re
    s = re.sub(r'[\\/:*?"<>|]+', " ", s)
    return re.sub(r"\s+", " ", s).strip()[:60] or "DN"


def _misa(mst: str, tu, den) -> bytes:
    rows = store.invoices([mst], tu, den)
    return misa.file_misa(rows, lambda i: store.items_by_invoice([i]).get(i, []), store.categories(), che_do())


@app.get("/export-misa")
def export_misa():
    """File chứng từ hạch toán sẵn để nhập khẩu vào MISA: mỗi công ty một file (MISA nhập theo từng công ty)."""
    msts, tu, den, _ = _filtered()
    names = {c["mst"]: c["name"] for c in store.companies()}
    if len(msts) == 1:
        return send_file(io.BytesIO(_misa(msts[0], tu, den)), as_attachment=True,
                         download_name=f"Nhap MISA {msts[0]} {tu}_{den}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for mst in msts:
            z.writestr(f"Nhap MISA {mst} {_ten_file(names.get(mst, mst))} {tu}_{den}.xlsx", _misa(mst, tu, den))
    return send_file(io.BytesIO(buf.getvalue()), as_attachment=True,
                     download_name=f"nhap-misa-tung-dn_{tu}_{den}.zip", mimetype="application/zip")


@app.get("/export-tung-dn.zip")
def export_tung_dn():
    """Mỗi doanh nghiệp một file Excel riêng, gom trong một file .zip."""
    msts, tu, den, _ = _filtered()
    names = {c["mst"]: c["name"] for c in store.companies()}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for mst in msts:
            rows = store.invoices([mst], tu, den, request.args.get("chieu") or None)
            z.writestr(f"{mst} {_ten_file(names.get(mst, mst))} {tu}_{den}.xlsx", _excel([mst], tu, den, rows))
    return send_file(io.BytesIO(buf.getvalue()), as_attachment=True,
                     download_name=f"bang-ke-tung-dn_{tu}_{den}.zip", mimetype="application/zip")


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



# ---------- 6. Phân loại hàng hóa để hạch toán ----------
@app.get("/phan-loai")
def phan_loai():
    chieu = request.args.get("chieu", "vao")
    if chieu not in PHAN_LOAI:
        chieu = "vao"
    chua_xn = request.args.get("chua_xn") == "1"
    rows = [r for r in tong_hop_mat_hang(store.item_lines(), store.categories(), theo_dn=False, che_do=che_do())
            if r["chieu"] == chieu and (not chua_xn or not r["da_xac_nhan"])]
    return render_template("phan_loai.html", rows=rows, chieu=chieu, chua_xn=chua_xn,
                           loai=bang_phan_loai(che_do())[chieu], che_do=CHE_DO_KE_TOAN[che_do()])


@app.post("/phan-loai")
def luu_phan_loai():
    chieu = request.form.get("chieu", "vao")
    at = datetime.now().strftime("%Y-%m-%d %H:%M")
    n = 0
    for k in request.form:
        if not k.startswith("pl_"):
            continue
        i = k[3:]
        key = request.form.get(f"k_{i}", "")
        parts = key.split("|", 2)
        pl = request.form[k]
        if len(parts) != 3 or parts[0] not in PHAN_LOAI or pl not in PHAN_LOAI[parts[0]]:
            continue
        store.set_category(parts[0], parts[1], parts[2], pl, request.form.get(f"tk_{i}", "").strip(), at,
                           request.form.get(f"ma_{i}", "").strip(), request.form.get(f"kho_{i}", "").strip())
        n += 1
    flash(f"Đã lưu phân loại {n} mặt hàng", "ok")
    return redirect(url_for("phan_loai", chieu=chieu, chua_xn=request.form.get("chua_xn") or None))


# ---------- 7. Google Drive: mỗi công ty một tài khoản Google riêng ----------
REDIRECT_URI = "http://127.0.0.1:5000/google/callback"
oauth_states: dict[str, str] = {}      # state → MST đang kết nối


def che_do() -> str:
    """Chế độ kế toán dùng để gợi ý tài khoản; mặc định Thông tư 133."""
    v = store.setting("che_do")
    return v if v in CHE_DO_KE_TOAN else "TT133"


def ten_ky(tu: str, den: str) -> str:
    """'2026-10' nếu đúng trọn một tháng, ngược lại '2026-10-01_2026-10-15'."""
    a, b = to_date(tu), to_date(den)
    if a.day == 1 and a.year == b.year and a.month == b.month and (b + timedelta(days=1)).day == 1:
        return f"{a:%Y-%m}"
    return f"{tu}_{den}"


def _google_client() -> tuple[str, str]:
    cid, sec = store.setting("google_client_id"), store.setting("google_client_secret", secret=True)
    if not (cid and sec):
        raise gdrive.DriveError("Chưa cài đặt Google (vào trang Cài đặt)")
    return cid, sec


def day_len_drive(mst: str, tu: str, den: str) -> str:
    """Đẩy bảng kê Excel và XML của ĐÚNG MỘT công ty lên Drive của email công ty đó."""
    c = store.company(mst)
    if c is None or not c["email"]:
        raise gdrive.DriveError("chưa khai email Google cho công ty này")
    refresh = store.google_token(mst)
    if not refresh:
        raise gdrive.DriveError("chưa kết nối Google Drive")
    cid, sec = _google_client()
    token = gdrive.access_token(cid, sec, refresh)
    email = gdrive.email_of(token)
    if email != c["email"] or email != (c["google_email"] or ""):
        raise gdrive.DriveError(f"tài khoản Google đang kết nối là {email}, khác email đã khai {c['email']}. "
                                "Không đẩy để tránh nhầm công ty; hãy kết nối lại.")
    rows = store.invoices([mst], tu, den)
    if any(r["company_mst"] != mst for r in rows):           # chốt chặn cuối: không lẫn dữ liệu công ty khác
        raise gdrive.DriveError("dữ liệu lẫn công ty khác, dừng lại")
    if not rows:
        return f"không có hóa đơn trong kỳ, không đẩy lên Drive {email}"
    ky = ten_ky(tu, den)
    goc = gdrive.ensure_folder(token, f"Hóa đơn {mst} - {_ten_file(c['name'])}")
    thu_muc = gdrive.ensure_folder(token, ky, goc)
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    files = [(f"Bảng kê {mst} {ky}.xlsx", _excel([mst], tu, den, rows), xlsx),
             (f"Nhập MISA {mst} {ky}.xlsx", _misa(mst, tu, den), xlsx)]
    if any(r["xml_path"] for r in rows):
        files.append((f"XML {mst} {ky}.zip", export.zip_xml(rows, DATA_DIR / "xml"), "application/zip"))
    for name, content, mime in files:
        gdrive.upload(token, name, thu_muc, content, mime)
    return f"đã đẩy {len(files)} file lên Drive {email}, thư mục \"Hóa đơn {mst}…/{ky}\""


@app.route("/cai-dat", methods=["GET", "POST"])
def cai_dat():
    if request.method == "POST":
        if request.form.get("che_do") in CHE_DO_KE_TOAN:
            store.set_setting("che_do", request.form["che_do"])
        cid = request.form.get("client_id", "").strip()
        sec = request.form.get("client_secret", "").strip()
        if cid:
            store.set_setting("google_client_id", cid)
        if sec:
            store.set_setting("google_client_secret", sec, secret=True)
        flash("Đã lưu cài đặt", "ok")
        return redirect(url_for("cai_dat"))
    return render_template("cai_dat.html", client_id=store.setting("google_client_id") or "",
                           co_secret=bool(store.setting("google_client_secret", secret=True)),
                           redirect_uri=REDIRECT_URI, che_do=che_do(), cac_che_do=CHE_DO_KE_TOAN)


@app.post("/google/ket-noi/<mst>")
def google_ket_noi(mst):
    if request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        # Google chỉ trả kết quả về 127.0.0.1 của máy đang mở trình duyệt
        flash("Kết nối Google Drive phải làm trên máy chính (máy đang chạy công cụ), mở http://127.0.0.1:5000", "error")
        return redirect(url_for("index"))
    c = store.company(mst)
    if c is None or not c["email"]:
        flash("Khai email Google cho công ty trước (nhập lại công ty với ô Email)", "error")
        return redirect(url_for("index"))
    try:
        cid, _ = _google_client()
    except gdrive.DriveError as e:
        flash(str(e), "error")
        return redirect(url_for("cai_dat"))
    state = os.urandom(16).hex()
    oauth_states[state] = mst
    return redirect(gdrive.auth_url(cid, REDIRECT_URI, state, c["email"]))


@app.get("/google/callback")
def google_callback():
    mst = oauth_states.pop(request.args.get("state", ""), None)
    if mst is None:
        flash("Phiên kết nối Google không hợp lệ hoặc đã hết hạn, bấm Kết nối lại", "error")
        return redirect(url_for("index"))
    c = store.company(mst)
    if request.args.get("error") or not request.args.get("code"):
        flash(f"{c['name']}: chưa cấp quyền Google Drive", "error")
        return redirect(url_for("index"))
    try:
        cid, sec = _google_client()
        tok = gdrive.exchange_code(cid, sec, REDIRECT_URI, request.args["code"])
        email = gdrive.email_of(tok["access_token"])
    except gdrive.DriveError as e:
        flash(f"{c['name']}: {e}", "error")
        return redirect(url_for("index"))
    if email != (c["email"] or "").lower():
        if tok.get("refresh_token"):
            gdrive.revoke(tok["refresh_token"])
        flash(f"{c['name']} (MST {mst}): anh đăng nhập {email}, nhưng email đã khai là {c['email']}. "
              "Không lưu kết nối để tránh nhầm Drive. Bấm Kết nối lại và chọn đúng email.", "error")
        return redirect(url_for("index"))
    if "scope" in tok and "auth/drive.file" not in tok["scope"]:
        # Google cho bỏ tick từng quyền ở màn hình xin quyền; thiếu quyền Drive thì đẩy file sẽ lỗi 403
        if tok.get("refresh_token"):
            gdrive.revoke(tok["refresh_token"])
        flash(f"{c['name']}: chưa cấp quyền Google Drive. Bấm Kết nối Drive lại, ở màn hình xin quyền nhớ tick ô "
              "\"Xem, chỉnh sửa, tạo và xóa các tệp cụ thể trên Google Drive…\" rồi bấm Tiếp tục.", "error")
        return redirect(url_for("index"))
    if not tok.get("refresh_token"):
        flash(f"{c['name']}: Google không cấp quyền lâu dài, bấm Kết nối lại", "error")
        return redirect(url_for("index"))
    store.set_google(mst, tok["refresh_token"], email, datetime.now().strftime("%Y-%m-%d %H:%M"))
    flash(f"{c['name']}: đã kết nối Google Drive {email}", "ok")
    return redirect(url_for("index"))


@app.post("/google/ngat/<mst>")
def google_ngat(mst):
    tok = store.google_token(mst)
    if tok:
        gdrive.revoke(tok)
    store.clear_google(mst)
    flash("Đã ngắt kết nối Google Drive", "ok")
    return redirect(url_for("index"))


@app.post("/drive/day-len")
def drive_day_len():
    msts = [m for m in request.form.getlist("mst") if m]
    tu, den = request.form.get("tu"), request.form.get("den")
    if not (msts and tu and den):
        flash("Chọn doanh nghiệp và khoảng ngày", "error")
        return redirect(url_for("results"))
    for mst in msts:
        name = store.company_name(mst)
        try:
            flash(f"{name}: {day_len_drive(mst, tu, den)}", "ok")
        except gdrive.DriveError as e:
            flash(f"{name}: KHÔNG đẩy lên Drive — {e}", "error")
    return redirect(url_for("results", mst=msts, tu=tu, den=den))


# ---------- 8. Đăng nhập và 3 cấp tài khoản ----------
# Trang không cần đăng nhập
CONG_KHAI = {"dang_nhap", "khoi_tao", "static"}
# Trang chỉ Admin / Quản trị được vào (Người sử dụng không được)
CAN_QUAN_LY = {"add_company", "delete_company", "google_ket_noi", "google_ngat", "cai_dat", "nhap_danh_sach"}
CAN_TAI_KHOAN = {"tai_khoan", "them_tai_khoan", "sua_tai_khoan", "xoa_tai_khoan"}
lan_sai: dict[str, list[float]] = {}     # email → thời điểm đăng nhập sai, chống dò mật khẩu
SAI_TOI_DA, KHOA_PHUT = 5, 15


@app.before_request
def kiem_tra_dang_nhap():
    g.user = None
    uid = session.get("uid")
    if uid is not None:
        u = store.user(uid)
        if u is not None and u["hoat_dong"]:
            g.user = u
        else:
            session.clear()
    ep = request.endpoint or ""
    if ep in CONG_KHAI:
        return None
    if not store.users():
        return redirect(url_for("khoi_tao"))
    if g.user is None:
        return redirect(url_for("dang_nhap", next=request.full_path if request.method == "GET" else None))
    vt = g.user["vai_tro"]
    if (ep in CAN_QUAN_LY and not co_quyen(vt, "quan_ly")) or (ep in CAN_TAI_KHOAN and not co_quyen(vt, "tai_khoan")):
        flash("Tài khoản của anh/chị không có quyền làm việc này", "error")
        return redirect(url_for("index")), 303
    return None


@app.context_processor
def bien_chung():
    vt = g.user["vai_tro"] if getattr(g, "user", None) else None
    return {"nguoi_dung": getattr(g, "user", None), "ten_vai_tro": VAI_TRO,
            "co_quyen": lambda q: co_quyen(vt, q)}


def _bay_gio() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@app.route("/khoi-tao", methods=["GET", "POST"])
def khoi_tao():
    """Lần chạy đầu tiên: tạo tài khoản Admin đầu tiên."""
    if store.users():
        return redirect(url_for("dang_nhap"))
    if request.method == "POST":
        email, ho_ten = request.form.get("email", "").strip().lower(), request.form.get("ho_ten", "").strip()
        mk = request.form.get("mat_khau", "")
        loi = ("Email không hợp lệ" if "@" not in email else
               kiem_tra_mat_khau(mk) or ("Hai lần nhập mật khẩu không khớp" if mk != request.form.get("mat_khau2") else None))
        if loi:
            flash(loi, "error")
        else:
            uid = store.add_user(email, ho_ten, generate_password_hash(mk), "admin", None, _bay_gio())
            session.clear()
            session["uid"] = uid
            flash("Đã tạo tài khoản Admin đầu tiên", "ok")
            return redirect(url_for("index"))
    return render_template("khoi_tao.html")


@app.route("/dang-nhap", methods=["GET", "POST"])
def dang_nhap():
    if not store.users():
        return redirect(url_for("khoi_tao"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        now = datetime.now().timestamp()
        sai = [t for t in lan_sai.get(email, []) if now - t < KHOA_PHUT * 60]
        if len(sai) >= SAI_TOI_DA:
            flash(f"Nhập sai quá {SAI_TOI_DA} lần. Thử lại sau {KHOA_PHUT} phút.", "error")
            return render_template("dang_nhap.html", email=email), 429
        u = store.user_by_email(email)
        if u is None or not check_password_hash(u["pw_hash"], request.form.get("mat_khau", "")):
            lan_sai[email] = sai + [now]
            flash("Email hoặc mật khẩu không đúng", "error")
            return render_template("dang_nhap.html", email=email), 401
        if not u["hoat_dong"]:
            flash("Tài khoản đã bị khóa. Liên hệ Admin hoặc Quản trị.", "error")
            return render_template("dang_nhap.html", email=email), 403
        lan_sai.pop(email, None)
        session.clear()
        session["uid"] = u["id"]
        session.permanent = "ghi_nho" in request.form
        nxt = request.args.get("next") or ""
        return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
    return render_template("dang_nhap.html", email="")


@app.post("/dang-xuat")
def dang_xuat():
    session.clear()
    return redirect(url_for("dang_nhap"))


@app.route("/doi-mat-khau", methods=["GET", "POST"])
def doi_mat_khau():
    if request.method == "POST":
        mk = request.form.get("mat_khau_moi", "")
        if not check_password_hash(g.user["pw_hash"], request.form.get("mat_khau_cu", "")):
            flash("Mật khẩu hiện tại không đúng", "error")
        elif loi := kiem_tra_mat_khau(mk):
            flash(loi, "error")
        elif mk != request.form.get("mat_khau_moi2"):
            flash("Hai lần nhập mật khẩu mới không khớp", "error")
        else:
            store.update_user(g.user["id"], pw_hash=generate_password_hash(mk))
            flash("Đã đổi mật khẩu", "ok")
            return redirect(url_for("index"))
    return render_template("doi_mat_khau.html")


@app.get("/tai-khoan")
def tai_khoan():
    vt = g.user["vai_tro"]
    return render_template("tai_khoan.html", users=store.users(),
                           sua_duoc=lambda u: u["id"] != g.user["id"] and quan_ly_duoc(vt, u["vai_tro"]),
                           vai_tro_gan=[k for k in VAI_TRO if gan_duoc(vt, k)])


@app.post("/tai-khoan/them")
def them_tai_khoan():
    f = request.form
    email, vai_tro, mk = f.get("email", "").strip().lower(), f.get("vai_tro", ""), f.get("mat_khau", "")
    if not gan_duoc(g.user["vai_tro"], vai_tro):
        flash("Anh/chị không được tạo tài khoản với vai trò này", "error")
    elif "@" not in email:
        flash("Email không hợp lệ", "error")
    elif store.user_by_email(email):
        flash("Email này đã có tài khoản", "error")
    elif loi := kiem_tra_mat_khau(mk):
        flash(loi, "error")
    else:
        store.add_user(email, f.get("ho_ten", ""), generate_password_hash(mk), vai_tro, g.user["email"], _bay_gio())
        flash(f"Đã tạo tài khoản {email} ({VAI_TRO[vai_tro]})", "ok")
    return redirect(url_for("tai_khoan"))


def _doi_tuong(uid: int):
    """Tài khoản cần sửa / xóa, sau khi kiểm tra người đang làm có quyền với nó."""
    u = store.user(uid)
    if u is None:
        flash("Không tìm thấy tài khoản", "error")
    elif u["id"] == g.user["id"]:
        flash("Không tự sửa vai trò, khóa hoặc xóa tài khoản của chính mình. Đổi mật khẩu ở mục Đổi mật khẩu.", "error")
    elif not quan_ly_duoc(g.user["vai_tro"], u["vai_tro"]):
        flash("Quản trị không được sửa, khóa hoặc xóa tài khoản Admin", "error")
    else:
        return u
    return None


@app.post("/tai-khoan/<int:uid>/sua")
def sua_tai_khoan(uid):
    u = _doi_tuong(uid)
    if u is None:
        return redirect(url_for("tai_khoan"))
    f = request.form
    vai_tro = f.get("vai_tro", u["vai_tro"])
    hoat_dong = 1 if f.get("hoat_dong") == "1" else 0
    if not gan_duoc(g.user["vai_tro"], vai_tro):
        flash("Anh/chị không được đổi sang vai trò này", "error")
        return redirect(url_for("tai_khoan"))
    bo_admin = u["vai_tro"] == "admin" and u["hoat_dong"] and (vai_tro != "admin" or not hoat_dong)
    if bo_admin and store.so_admin_hoat_dong() <= 1:
        flash("Phải còn ít nhất một Admin đang hoạt động", "error")
        return redirect(url_for("tai_khoan"))
    thay = {"vai_tro": vai_tro, "hoat_dong": hoat_dong, "ho_ten": f.get("ho_ten", u["ho_ten"] or "").strip()}
    if f.get("mat_khau"):
        if loi := kiem_tra_mat_khau(f["mat_khau"]):
            flash(loi, "error")
            return redirect(url_for("tai_khoan"))
        thay["pw_hash"] = generate_password_hash(f["mat_khau"])
    store.update_user(uid, **thay)
    flash(f"Đã cập nhật tài khoản {u['email']}", "ok")
    return redirect(url_for("tai_khoan"))


@app.post("/tai-khoan/<int:uid>/xoa")
def xoa_tai_khoan(uid):
    u = _doi_tuong(uid)
    if u is not None:
        if u["vai_tro"] == "admin" and u["hoat_dong"] and store.so_admin_hoat_dong() <= 1:
            flash("Phải còn ít nhất một Admin đang hoạt động", "error")
        else:
            store.delete_user(uid)
            flash(f"Đã xóa tài khoản {u['email']}", "ok")
    return redirect(url_for("tai_khoan"))


def ip_noi_bo() -> str | None:
    """Địa chỉ IP của máy này trong mạng văn phòng / wifi (không gửi dữ liệu ra ngoài)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def bat_log() -> None:
    """Ghi nhật ký kết nối cổng thuế ra màn hình và data/logs/cong-thue.log (không ghi mật khẩu)."""
    import logging
    from logging.handlers import RotatingFileHandler
    (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    lg = logging.getLogger("thuedn")
    lg.setLevel(logging.INFO)
    for h in (logging.StreamHandler(),
              RotatingFileHandler(DATA_DIR / "logs" / "cong-thue.log", maxBytes=2_000_000,
                                  backupCount=3, encoding="utf-8")):
        h.setFormatter(fmt)
        lg.addHandler(h)


if __name__ == "__main__":
    import sys
    bat_log()
    if "--mang-noi-bo" in sys.argv or os.environ.get("THUEDN_LAN") == "1":
        # Máy chính: cho các máy khác cùng mạng mở bằng trình duyệt (vẫn phải đăng nhập)
        ip = ip_noi_bo()
        print("CHẾ ĐỘ MẠNG NỘI BỘ: máy này là máy chính.")
        print("  Trên máy này mở:      http://127.0.0.1:5000")
        print(f"  Máy khác cùng mạng:   http://{ip or '<IP máy này>'}:5000")
        print("  Kết nối Google Drive phải làm trên chính máy này.")
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    else:
        print("Mở trình duyệt vào: http://127.0.0.1:5000")
        app.run(host="127.0.0.1", port=5000, debug=False)
