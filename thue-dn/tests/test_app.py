"""Kiểm thử không cần mạng: thay cổng thuế bằng dữ liệu giả."""
import io
import os
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thuedn.rules import chia_thang, muc_rui_ro, tinh_chat  # noqa: E402


def test_chia_thang():
    assert chia_thang(date(2026, 1, 15), date(2026, 3, 10)) == [
        (date(2026, 1, 15), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
        (date(2026, 3, 1), date(2026, 3, 10)),
    ]
    with pytest.raises(ValueError):
        chia_thang(date(2026, 2, 1), date(2026, 1, 1))


def test_muc_rui_ro():
    assert muc_rui_ro("cham_dut", "2026-05-01", "2026-06-01") == "cao"
    assert muc_rui_ro("cham_dut", "2026-05-01", "2026-04-01") == "trung_binh"
    assert muc_rui_ro("dang_hd", None, "2026-06-01") == "thap"
    assert muc_rui_ro("chua_tra", None, "2026-06-01") == "chua_ro"
    assert tinh_chat(3) == "Hóa đơn điều chỉnh"


FAKE_PURCHASE = [
    {"nbmst": "0100000001", "nbten": "NCC Một", "nmmst": "0300000000", "nmten": "DN A",
     "khmshdon": 1, "khhdon": "C26TAA", "shdon": 11, "tdlap": "2026-06-10T00:00:00Z",
     "tgtcthue": 1000000, "tgtthue": 100000, "tgtttbso": 1100000, "tthai": 1},
    {"nbmst": "0100000002", "nbten": "NCC Hai", "nmmst": "0300000000", "nmten": "DN A",
     "khmshdon": 1, "khhdon": "C26TBB", "shdon": 22, "tdlap": "2026-06-20T00:00:00Z",
     "tgtcthue": 2000000, "tgtthue": 200000, "tgtttbso": 2200000, "tthai": 3},
]
FAKE_SOLD = [
    {"nbmst": "0300000000", "nbten": "DN A", "nmmst": "0400000000", "nmten": "Khách X",
     "khmshdon": 1, "khhdon": "C26TCC", "shdon": 5, "tdlap": "2026-06-05T00:00:00Z",
     "tgtcthue": 500000, "tgtthue": 50000, "tgtttbso": 550000, "tthai": 1},
]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("THUEDN_DATA", str(tmp_path))
    sys.modules.pop("app", None)
    import app as appmod
    from thuedn import portal

    class FakeCaptcha:
        key = "k1"
        data_uri = "data:image/svg+xml;base64,PHN2Zy8+"

    monkeypatch.setattr(portal.PortalSession, "get_captcha", lambda self: FakeCaptcha())

    def fake_login(self, mst, pw, ckey, cval):
        if cval != "abc12":
            raise portal.PortalError("Sai captcha")
        assert pw == "mat-khau" and ckey == "k1"
        self.token = "t"

    monkeypatch.setattr(portal.PortalSession, "login", fake_login)
    monkeypatch.setattr(portal.PortalSession, "purchase", lambda self, tu, den: iter(FAKE_PURCHASE))
    monkeypatch.setattr(portal.PortalSession, "sold", lambda self, tu, den: iter(FAKE_SOLD))
    appmod.app.testing = True
    c = appmod.app.test_client()
    # đăng nhập sẵn bằng tài khoản Admin cho các bài kiểm thử chức năng
    tao_tai_khoan(appmod, "admin@test.vn", "admin")
    dang_nhap(c, "admin@test.vn")
    yield c, appmod


MAT_KHAU = "MatKhau123"


def tao_tai_khoan(appmod, email, vai_tro):
    from werkzeug.security import generate_password_hash
    return appmod.store.add_user(email, email.split("@")[0], generate_password_hash(MAT_KHAU), vai_tro, None, "x")


def dang_nhap(c, email, mk=MAT_KHAU):
    c.post("/dang-xuat")
    return c.post("/dang-nhap", data={"email": email, "mat_khau": mk})


def test_cong_thue_429_cho_roi_thu_lai(monkeypatch):
    """Cổng trả 429 khi gọi quá nhanh: giãn nhịp, chờ rồi thử lại; hết lượt thì báo lỗi."""
    from thuedn import portal

    ngu = []
    monkeypatch.setattr(portal.time, "sleep", lambda s: ngu.append(s))

    class Resp:
        def __init__(self, code, content=b"", headers=None):
            self.status_code, self.content, self.headers = code, content, headers or {}
            self.text = content.decode()

        def json(self):
            import json
            return json.loads(self.text)

    tra_ve = [Resp(429, b"Too Many Requests", {"Retry-After": "7"}), Resp(429, b"Too Many Requests"),
              Resp(200, b"PK\x03\x04zip")]
    s = portal.PortalSession()
    monkeypatch.setattr(s.http, "request", lambda *a, **k: tra_ve.pop(0))
    inv = {"nbmst": "0100000001", "khhdon": "C26TAA", "shdon": 1, "khmshdon": 1}
    assert s.export_xml(inv).startswith(b"PK")
    assert 7 in ngu and portal.CHO_KHI_429[1] in ngu

    monkeypatch.setattr(s.http, "request", lambda *a, **k: Resp(429, b"Too Many Requests"))
    with pytest.raises(portal.PortalError) as loi:
        s.export_xml(inv)
    assert not isinstance(loi.value, portal.KhongCoXML)

    # HĐ không mã của EVN / viễn thông: cổng không có XML, không thử lại vô ích
    khong_co = '{"message":"Không tồn tại hồ sơ gốc của hóa đơn."}'.encode()
    monkeypatch.setattr(s.http, "request", lambda *a, **k: Resp(500, khong_co))
    with pytest.raises(portal.KhongCoXML):
        s.export_xml(inv)


def test_hoa_don_may_tinh_tien(client, monkeypatch):
    """HĐ bán ra từ máy tính tiền: mỗi lần tra một captcha, lưu theo từng trang, xong thì tải ngầm."""
    from thuedn import portal
    c, appmod = client

    def hd(so):
        return {"nbmst": "0300000000", "nbten": "DN A", "nmmst": None, "nmten": "Khách lẻ", "khmshdon": 1,
                "khhdon": "C26MAA", "shdon": so, "tdlap": "2026-06-15T00:00:00Z", "tgtcthue": 100000,
                "tgtthue": 10000, "tgtttbso": 110000, "tthai": 1, "hsgoc": "x"}

    goi = []

    def trang_mtt(self, tu, den, state, ckey, cvalue):
        goi.append((state, ckey, cvalue))
        if cvalue != "mtt":
            raise portal.PortalError("Mã captcha không đúng")
        return ([hd(1), hd(2)], "s2", 3) if state is None else ([hd(3)], None, 3)

    monkeypatch.setattr(portal.PortalSession, "sold_mtt_page", trang_mtt)

    def excel_loi(self, tu, den, ckey, cvalue):
        raise portal.PortalError("Không xuất được Excel (mã 500)")

    monkeypatch.setattr(portal.PortalSession, "sold_mtt_excel", excel_loi)
    xml_goi = []
    monkeypatch.setattr(portal.PortalSession, "export_xml", lambda self, inv: xml_goi.append(inv["shdon"]) or b"PK")
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau"})
    c.post("/download", data={"mst": "0300000000", "loai": ["ra"], "tu": "2026-06-01", "den": "2026-06-30",
                              "mtt": "on", "xml_mtt": "on"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})                       # đăng nhập
    trang = c.get("/captcha").get_data(as_text=True)
    assert "máy tính tiền" in trang and "06/2026" in trang and "một captcha cho cả tháng" in trang
    c.post("/captcha", data={"cvalue": "mtt"})                         # Excel lỗi → chuyển sang tra từng trang
    assert "Chuyển sang tra từng trang" in c.get("/captcha").get_data(as_text=True)
    c.post("/captcha", data={"cvalue": "sai"})                         # sai captcha: tra lại trang đó
    c.post("/captcha", data={"cvalue": "mtt"})                         # trang 1
    assert "2/3" in c.get("/captcha").get_data(as_text=True)
    c.post("/captcha", data={"cvalue": "mtt"})                         # trang 2, hết
    assert [g[0] for g in goi] == [None, None, "s2"] and goi[1][1] == "k1"
    assert c.get("/captcha").headers["Location"].endswith("/dang-tai")
    so_mtt = [r for r in appmod.store.invoices() if r["khhdon"] == "C26MAA"]
    assert len(so_mtt) == 3 and sorted(xml_goi) == [1, 2, 3]
    assert "3 hóa đơn bán ra từ máy tính tiền" in c.get("/results").get_data(as_text=True)
    assert portal.la_mtt("C26MAA") and not portal.la_mtt("C26TAA") and not portal.la_mtt(None)


def _excel_cong(dong):
    """File Excel giống cổng xuất: tiêu đề 2 tầng, có dòng tổng cộng cuối."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["DANH SÁCH HÓA ĐƠN"])
    ws.append(["Từ ngày 01/06/2026 đến ngày 30/06/2026"])
    ws.append(["STT", "Ký hiệu mẫu số", "Ký hiệu hóa đơn", "Số hóa đơn", "Ngày lập", "Thông tin người mua", None,
               "Tổng tiền chưa thuế", "Tổng tiền thuế", "Tổng tiền thanh toán", "Trạng thái hóa đơn"])
    ws.append([None, None, None, None, None, "MST người mua", "Tên người mua"])
    for d in dong:
        ws.append(d)
    ws.append(["Tổng cộng", None, None, None, None, None, None, 300000, 30000, 330000, None])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_mtt_lay_bang_excel_mot_captcha(client, monkeypatch):
    from thuedn import portal
    c, appmod = client
    tep = _excel_cong([
        [1, 1, "C26MAA", "0000123", "15/06/2026", None, "Khách lẻ", "100.000", "10.000", "110.000", "Hóa đơn mới"],
        [2, 1, "C26MAA", 124, "16/06/2026", "0312345678", "Công ty X", 200000, 20000, 220000,
         "Hóa đơn đã bị điều chỉnh"],
    ])
    goi = []
    monkeypatch.setattr(portal.PortalSession, "sold_mtt_excel",
                        lambda self, tu, den, ckey, cvalue: goi.append(cvalue) or tep)
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau"})
    c.post("/download", data={"mst": "0300000000", "loai": ["ra"], "tu": "2026-06-01", "den": "2026-06-30",
                              "mtt": "on"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "x1"})
    assert goi == ["x1"]                                              # một captcha cho cả tháng
    assert c.get("/captcha").headers["Location"].endswith("/dang-tai")
    hd = {r["shdon"]: r for r in appmod.store.invoices() if r["khhdon"] == "C26MAA"}
    assert set(hd) == {"123", "124"}
    assert hd["123"]["tgtttbso"] == 110000 and hd["123"]["tdlap"] == "2026-06-15" and hd["123"]["tthai"] == 1
    assert hd["124"]["nmmst"] == "0312345678" and hd["124"]["tthai"] == 5
    assert (Path(appmod.DATA_DIR) / "mtt" / "0300000000" / "ban-ra-mtt_2026-06-01_2026-06-30.xlsx").exists()


def test_mtt_cong_khong_nhan_trang_lon(monkeypatch):
    from thuedn import portal
    monkeypatch.setattr(portal.time, "sleep", lambda s: None)

    class Resp:
        def __init__(self, code, body):
            import json
            self.status_code, self.text, self.headers = code, json.dumps(body), {}
            self.content = self.text.encode()

        def json(self):
            import json
            return json.loads(self.text)

    s = portal.PortalSession()
    sizes = []

    def req(method, url, params=None, headers=None, **k):
        sizes.append(params["size"])
        assert headers["ckey"] == "k" and params["cvalue"] == "v"
        if params["size"] > 50:
            return Resp(400, {"message": "size must be less than or equal to 50"})
        return Resp(200, {"datas": [{"shdon": 1}], "state": None, "total": 1})

    monkeypatch.setattr(s.http, "request", req)
    with pytest.raises(portal.PortalError):
        s.sold_mtt_page(date(2026, 6, 1), date(2026, 6, 30), None, "k", "v")
    rows, nxt, tong = s.sold_mtt_page(date(2026, 6, 1), date(2026, 6, 30), None, "k", "v")
    assert sizes == [portal.PAGE_SIZE_MTT, 50] and len(rows) == 1 and nxt is None


def test_tai_chay_ngam_chi_mot_luot(client, monkeypatch):
    """Trang chờ bị gọi lại nhiều lần trong lúc tải: chỉ một lượt tải chạy, xong thì sang Kết quả."""
    import threading
    from thuedn import portal
    c, appmod = client
    cho, so_luot = threading.Event(), []

    def mua_vao_cham(self, tu, den):
        so_luot.append(1)
        cho.wait(10)
        yield from FAKE_PURCHASE

    monkeypatch.setattr(portal.PortalSession, "purchase", mua_vao_cham)
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau"})
    c.post("/download", data={"mst": "0300000000", "loai": ["vao"], "tu": "2026-06-01", "den": "2026-06-30"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})
    appmod.app.testing = False
    try:
        assert c.get("/captcha").headers["Location"].endswith("/dang-tai")
        assert "Đang tải hóa đơn" in c.get("/dang-tai").get_data(as_text=True)
        c.get("/captcha")
        c.post("/captcha", data={"cvalue": "abc12"})
        r = c.post("/download", data={"mst": "0300000000", "loai": ["vao"], "tu": "2026-06-01", "den": "2026-06-30"})
        assert r.headers["Location"].endswith("/dang-tai")      # không cho bắt đầu lượt mới khi đang tải
        cho.set()
        for t in threading.enumerate():
            if t.name == "tai-hoa-don":
                t.join(10)
    finally:
        appmod.app.testing = True
    assert len(so_luot) == 1
    assert c.get("/dang-tai").headers["Location"].endswith("/results")
    assert len(appmod.store.invoices()) == 2


def test_luong_day_du(client):
    c, appmod = client
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau"})
    # mật khẩu không lưu dạng chữ thường
    raw = appmod.store.db.execute("SELECT enc_password FROM companies").fetchone()[0]
    assert b"mat-khau" not in raw

    r = c.post("/download", data={"mst": "0300000000", "loai": ["vao", "ra"],
                                  "tu": "2026-06-01", "den": "2026-06-30"})
    assert r.headers["Location"].endswith("/captcha")
    assert "Nhập captcha" in c.get("/captcha").get_data(as_text=True)

    c.post("/captcha", data={"cvalue": "sai"})
    assert appmod.job["pending"] == ["0300000000"]
    c.post("/captcha", data={"cvalue": "abc12"})
    # bấm "Đăng nhập và tải" 2 lần: lần 2 không còn DN chờ, không được lỗi 500
    r = c.post("/captcha", data={"cvalue": "abc12"})
    assert r.status_code == 302
    r = c.get("/captcha")
    assert r.headers["Location"].endswith("/dang-tai")   # tải chạy ngầm, trang tiến độ tự chuyển
    assert c.get("/dang-tai").headers["Location"].endswith("/results")
    # vào lại /captcha khi đã tải xong: không tải lần nữa
    assert c.get("/captcha").headers["Location"].endswith("/dang-tai")

    page = c.get("/results").get_data(as_text=True)
    assert "NCC Hai" in page and "Khách X" in page and "Hóa đơn điều chỉnh" in page

    # đánh dấu NCC Hai đã chấm dứt trước ngày lập → rủi ro cao
    c.get("/suppliers")
    c.post("/suppliers/0100000002", data={"status": "cham_dut", "ngay_ngung": "2026-06-15", "nguon": "cqt"})
    assert "Rủi ro CAO" in c.get("/results").get_data(as_text=True)

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    wb = load_workbook(io.BytesIO(x.data))
    assert wb.sheetnames == ["Mua vào", "Bán ra", "Điều chỉnh - thay thế", "Chi tiết bán ra", "Chi tiết mua vào",
                             "Tổng hợp hạch toán"]
    assert wb["Mua vào"].max_row == 3 and wb["Bán ra"].max_row == 2
    assert wb["Điều chỉnh - thay thế"].max_row == 3   # 2 hàng tiêu đề + 1 HĐ điều chỉnh
    head_vao = [h.value for h in wb["Mua vào"][1]]
    assert head_vao[-1] == "Đánh giá" and head_vao[-2] == "Mức rủi ro"
    cao = [r for r in wb["Mua vào"].iter_rows(values_only=True) if r[head_vao.index("Mức rủi ro")] == "CAO"]
    assert len(cao) == 1 and cao[0][6] == "0100000002"

    # tải lại không bị trùng hóa đơn
    c.post("/download", data={"mst": "0300000000", "loai": ["vao", "ra"],
                              "tu": "2026-06-01", "den": "2026-06-30"})
    c.get("/captcha")
    assert len(appmod.store.invoices()) == 3


# ---------- Kiểm tra đối tác ----------
from thuedn.rules import danh_gia_doi_tac, parse_danh_sach_mst  # noqa: E402


def test_danh_gia_doi_tac():
    today = date(2026, 11, 21)
    assert danh_gia_doi_tac("dang_hd", "2020-01-01", 1, [], "cqt", today)[0] == "nen_ky"
    kl, ly_do = danh_gia_doi_tac("dang_hd", "2026-06-01", 1, [], "cqt", today)
    assert kl == "can_xem" and "5 tháng" in ly_do[0]
    assert danh_gia_doi_tac("dang_hd", "2020-01-01", 0, [], "cqt", today)[0] == "can_xem"
    assert danh_gia_doi_tac("dang_hd", "2020-01-01", 1, [], "tong_hop", today)[0] == "can_xem"
    assert danh_gia_doi_tac("cham_dut", "2020-01-01", 1, [], "cqt", today)[0] == "khong_nen"
    kl, ly_do = danh_gia_doi_tac("dang_hd", "2020-01-01", 1, ["rui_ro_cao"], "cqt", today)
    assert kl == "khong_nen" and "rủi ro cao" in ly_do[0]
    assert danh_gia_doi_tac("chua_tra", "2020-01-01", 1, [], "cqt", today)[0] == "chua_du"


def test_parse_danh_sach_mst():
    text = "MST,Tên\n0100000001, Công ty A\n0100000002\tCông ty B\nabc\n0100000003-001\n0100000001,Trùng"
    assert parse_danh_sach_mst(text) == [
        ("0100000001", "Trùng"), ("0100000002", "Công ty B"), ("0100000003-001", "")]


def test_kiem_tra_doi_tac(client):
    c, appmod = client
    # có hóa đơn mua vào từ NCC Hai → NCC Hai cần tra lại
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau"})
    c.post("/download", data={"mst": "0300000000", "loai": ["vao"], "tu": "2026-06-01", "den": "2026-06-30"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})
    c.get("/captcha")
    assert "cần tra lại" in c.get("/").get_data(as_text=True)

    # nhập danh sách rủi ro, NCC Hai có tên
    r = c.post("/danh-sach-rui-ro", data={"loai": "rui_ro_cao", "nguon": "Cục Thuế 11/2026",
                                          "noi_dung": "0100000002, NCC Hai\n0999999999"})
    assert r.status_code == 302
    page = c.get("/doi-tac").get_data(as_text=True)
    assert "nằm trong danh sách rủi ro" in page and "NCC Hai" in page

    # đối tác mới, chưa có hóa đơn: kiểm tra trước khi ký
    r = c.post("/doi-tac", data={"mst": "0200000009", "ten": "Đối tác mới", "status": "dang_hd",
                                 "ngay_thanh_lap": "2019-03-01", "nganh_khop": "1", "nguon": "cqt"})
    assert r.headers["Location"].endswith("/doi-tac/0200000009")
    page = c.get("/doi-tac/0200000009").get_data(as_text=True)
    assert "Có thể giao dịch" in page and "Chưa có hóa đơn" in page

    # NCC Hai: đang hoạt động nhưng nằm trong danh sách → không nên
    c.post("/doi-tac", data={"mst": "0100000002", "ten": "NCC Hai", "status": "dang_hd",
                             "ngay_thanh_lap": "2019-03-01", "nganh_khop": "1", "nguon": "cqt"})
    page = c.get("/doi-tac/0100000002").get_data(as_text=True)
    assert "Không nên giao dịch" in page and "1 hóa đơn" in page

    # tra lại lần 2, đổi trạng thái → lịch sử giữ cả 2 lần, bảng NCC được đồng bộ
    c.post("/doi-tac", data={"mst": "0100000002", "ten": "NCC Hai", "status": "cham_dut",
                             "ngay_ngung": "2026-06-15", "nganh_khop": "1", "nguon": "cqt"})
    assert len(appmod.store.partner_checks("0100000002")) == 2
    assert appmod.store.supplier_map()["0100000002"]["status"] == "cham_dut"
    assert "Rủi ro CAO" in c.get("/results").get_data(as_text=True)

    # phiếu Excel làm bằng chứng
    x = c.get("/doi-tac/0100000002/phieu.xlsx")
    wb = load_workbook(io.BytesIO(x.data))
    assert wb.sheetnames == ["Phiếu kiểm tra", "Lịch sử kiểm tra"]
    assert wb["Lịch sử kiểm tra"].max_row == 3
    assert wb["Phiếu kiểm tra"]["B5"].value == "Không nên giao dịch"


# ---------- Nối HĐ điều chỉnh / thay thế với HĐ gốc ----------
from thuedn.xmlhd import hd_lien_quan_tu_xml, hd_lien_quan_tu_zip  # noqa: E402

XML_DIEU_CHINH = """<?xml version="1.0" encoding="UTF-8"?>
<HDon><DLHDon><TTChung><PBan>2.1.0</PBan><KHMSHDon>1</KHMSHDon><KHHDon>C26TAA</KHHDon><SHDon>30</SHDon>
<TTHDLQuan><TCHDon>2</TCHDon><LHDCLQuan>1</LHDCLQuan><KHMSHDCLQuan>1</KHMSHDCLQuan>
<KHHDCLQuan>C26TAA</KHHDCLQuan><SHDCLQuan>00000011</SHDCLQuan><NLHDCLQuan>2026-06-10</NLHDCLQuan>
<GChu>Điều chỉnh giảm đơn giá theo biên bản 05/BB</GChu>
</TTHDLQuan></TTChung><NDHDon><DSHHDVu><HHDVu><THHDVu>Thép cuộn</THHDVu></HHDVu></DSHHDVu></NDHDon>
</DLHDon></HDon>""".encode()


def test_doc_xml_hd_lien_quan():
    assert hd_lien_quan_tu_xml(XML_DIEU_CHINH) == {
        "noi_dung": "Điều chỉnh giảm đơn giá theo biên bản 05/BB",
        "tinh_chat": "dieu_chinh", "goc_khmshdon": "1", "goc_khhdon": "C26TAA",
        "goc_shdon": "11", "goc_tdlap": "2026-06-10"}
    buf = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hd.xml", XML_DIEU_CHINH)
    assert hd_lien_quan_tu_zip(buf.getvalue())["goc_shdon"] == "11"
    assert hd_lien_quan_tu_xml(b"<HDon><TTChung><SHDon>1</SHDon></TTChung></HDon>") is None
    # không có ghi chú → lấy tên hàng hóa
    no_gchu = XML_DIEU_CHINH.replace("<GChu>Điều chỉnh giảm đơn giá theo biên bản 05/BB</GChu>".encode(), b"")
    assert hd_lien_quan_tu_xml(no_gchu)["noi_dung"] == "Thép cuộn"


def _hd(nb, kh, so, ngay, tien, tthai, goc=None):
    r = {"nbmst": nb, "nbten": "NCC " + nb[-1], "nmmst": "0300000000", "nmten": "DN A", "khmshdon": 1,
         "khhdon": kh, "shdon": so, "tdlap": ngay + "T00:00:00Z", "tgtcthue": tien,
         "tgtthue": tien // 10, "tgtttbso": tien + tien // 10, "tthai": tthai}
    if goc:
        r.update({"khmshdgoc": 1, "khhdgoc": goc[0], "shdgoc": goc[1], "tdlhdgoc": goc[2] + "T00:00:00Z"})
    return r


def test_excel_noi_hd_goc(client):
    c, appmod = client
    from thuedn.portal import normalize
    rows = [
        _hd("0100000001", "C26TAA", 11, "2026-05-10", 10_000_000, 5),                              # gốc, bị điều chỉnh
        _hd("0100000001", "C26TAA", 30, "2026-06-12", -2_000_000, 3, ("C26TAA", 11, "2026-05-10")),  # điều chỉnh lần 1
        _hd("0100000001", "C26TAA", 41, "2026-06-25", -1_000_000, 3, ("C26TAA", 11, "2026-05-10")),  # điều chỉnh lần 2
        _hd("0100000002", "C26TBB", 7, "2026-06-03", 5_000_000, 4),                                # gốc, bị thay thế
        _hd("0100000002", "C26TBB", 9, "2026-06-05", 4_500_000, 2, ("C26TBB", 7, "2026-06-03")),     # thay thế
        _hd("0100000003", "C26TCC", 2, "2026-06-08", 3_000_000, 5),                                # bị ĐC, chưa có HĐ ĐC
        _hd("0100000004", "C26TDD", 5, "2026-06-09", 1_000_000, 3, ("C26TDD", 1, "2026-01-02")),     # gốc chưa tải
    ]
    for r in rows:
        appmod.store.save_invoice("0300000000", "vao", normalize(r))

    # lọc tháng 6: HĐ gốc tháng 5 vẫn được tìm thấy
    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    ws = load_workbook(io.BytesIO(x.data))["Điều chỉnh - thay thế"]
    head = [v for v in next(ws.iter_rows(min_row=2, max_row=2, values_only=True))]
    data = [dict(zip(range(len(head)), r)) for r in ws.iter_rows(min_row=3, values_only=True)]
    H = {h: i for i, h in enumerate(head) if h not in head[:i]}   # vị trí lần xuất hiện đầu
    goc_so, adj_so = 9, 17          # cột "Số HĐ" của HĐ gốc (trước) và HĐ điều chỉnh (sau), 0-based
    assert head[goc_so] == "Số HĐ" and head[adj_so] == "Số HĐ"
    assert head[goc_so + 5] == "Trạng thái HĐ gốc" and head[adj_so - 2] == "Ký hiệu mẫu"
    by_adj = {r[adj_so]: r for r in data if r[adj_so]}

    assert len(data) == 5
    dc1, dc2 = by_adj[30], by_adj[41]
    assert dc1[goc_so] == 11 and dc2[goc_so] == 11
    assert dc1[H["Lần"]] == 1 and dc2[H["Lần"]] == 2
    assert dc1[goc_so + 4] == 11_000_000           # tổng thanh toán HĐ gốc
    assert dc2[H["Tổng sau điều chỉnh (tạm tính)"]] == 11_000_000 - 2_200_000 - 1_100_000
    assert dc1[H["Trạng thái HĐ gốc"]] == "Bị điều chỉnh"

    tt = by_adj[9]
    assert tt[H["Loại"]] == "Thay thế" and tt[goc_so] == 7 and tt[H["Trạng thái HĐ gốc"]] == "Bị thay thế"

    chua_tai = by_adj[5]
    assert chua_tai[goc_so] == 1 and "chưa có trong dữ liệu" in chua_tai[H["Ghi chú"]]

    mo_coi = [r for r in data if not r[adj_so]]
    assert len(mo_coi) == 1 and mo_coi[0][goc_so] == 2
    assert "Chưa có HĐ điều chỉnh" in mo_coi[0][H["Ghi chú"]]

    # các HĐ điều chỉnh của cùng một HĐ gốc nằm liền nhau
    order = [r[adj_so] for r in data]
    assert abs(order.index(30) - order.index(41)) == 1


def test_ban_ra_hd_dieu_chinh_cung_hang(client):
    c, appmod = client
    from thuedn.portal import normalize

    def ra(kh, so, ngay, tien, tthai, goc=None):
        r = _hd("0300000000", kh, so, ngay, tien, tthai, goc)
        r.update({"nmmst": "0400000000", "nmten": "Khách X"})
        return r

    for r in [
        ra("C26TMA", 201, "2026-10-08", 45_000_000, 5),                                   # bị ĐC 2 lần
        ra("C26TMA", 205, "2026-10-09", 10_000_000, 1),                                   # bình thường
        ra("C26TMA", 209, "2026-10-15", -5_000_000, 3, ("C26TMA", 201, "2026-10-08")),
        ra("C26TMA", 226, "2026-10-18", -1_000_000, 3, ("C26TMA", 201, "2026-10-08")),
        ra("C26TMA", 230, "2026-10-20", 3_000_000, 4),                                    # bị thay thế
        ra("C26TMA", 231, "2026-10-21", 2_800_000, 2, ("C26TMA", 230, "2026-10-20")),
        ra("C26TMA", 240, "2026-10-25", 1_000_000, 5),                                    # thiếu HĐ ĐC
        ra("C26TMA", 150, "2026-09-10", 7_000_000, 5),                                    # gốc tháng 9
        ra("C26TMA", 250, "2026-10-28", 700_000, 3, ("C26TMA", 150, "2026-09-10")),        # ĐC tháng 10
        ra("C26TMA", 260, "2026-10-29", -200_000, 3, ("C26TMA", 99, "2026-03-01")),        # gốc chưa tải
    ]:
        appmod.store.save_invoice("0300000000", "ra", normalize(r))

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-10-01&den=2026-10-31")
    ws = load_workbook(io.BytesIO(x.data))["Bán ra"]
    head = [h.value for h in ws[1]]
    assert head[-1] == "Đánh giá"
    assert head.index("Số HĐ ĐC/TT") > head.index("Tính chất")
    rows = [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    so = lambda r: (r["Số HĐ"], r["Số HĐ ĐC/TT"])
    assert [so(r) for r in rows] == [
        (201, 209), (201, 226), (205, None), (230, 231), (240, None), (150, 250), (99, 260)]

    r1, r2 = rows[0], rows[1]
    assert r1["Tổng thanh toán"] == 49_500_000 and r2["Tổng thanh toán"] is None   # không cộng trùng
    assert r1["Ngày HĐ ĐC/TT"] == "2026-10-15" and r1["Tổng thanh toán ĐC/TT"] == -5_500_000
    assert r1["Nội dung điều chỉnh"] == "Điều chỉnh giảm"
    assert r2["Tổng sau điều chỉnh (tạm tính)"] == 49_500_000 - 5_500_000 - 1_100_000
    assert r1["Đánh giá"] == "Đã điều chỉnh lần 1" and r2["Đánh giá"] == "Đã điều chỉnh lần 2"
    assert rows[2]["Đánh giá"] == "Bình thường"
    assert rows[3]["Nội dung điều chỉnh"] == "Thay thế" and rows[3]["Tổng sau điều chỉnh (tạm tính)"] == 3_080_000
    assert "chưa có HĐ ĐC/TT" in rows[4]["Đánh giá"]
    assert "HĐ gốc thuộc kỳ khác" in rows[5]["Đánh giá"] and rows[5]["Nội dung điều chỉnh"] == "Điều chỉnh tăng"
    assert "HĐ gốc chưa có trong dữ liệu" in rows[6]["Đánh giá"] and rows[6]["Tổng thanh toán"] is None
    # mỗi HĐ ĐC/TT chỉ xuất hiện một lần, không thành hàng riêng
    assert sum(1 for r in rows if r["Số HĐ"] in (209, 226, 231, 250, 260)) == 0


def test_mua_vao_hd_dieu_chinh_cung_hang(client):
    c, appmod = client
    from thuedn.portal import normalize
    for r in [
        _hd("0100000001", "C26TAA", 11, "2026-06-05", 10_000_000, 5),
        _hd("0100000001", "C26TAA", 30, "2026-06-12", -2_000_000, 3, ("C26TAA", 11, "2026-06-05")),
        _hd("0100000002", "C26TBB", 7, "2026-06-03", 5_000_000, 4),
        _hd("0100000002", "C26TBB", 9, "2026-06-20", 4_500_000, 2, ("C26TBB", 7, "2026-06-03")),
        _hd("0100000003", "C26TCC", 2, "2026-06-08", 3_000_000, 1),
    ]:
        appmod.store.save_invoice("0300000000", "vao", normalize(r))
    appmod.store.ensure_suppliers_from_invoices()
    # người bán 2 chấm dứt 15/6: HĐ gốc lập trước, HĐ thay thế lập sau → rủi ro CAO
    appmod.store.update_supplier("0100000002", "cham_dut", "2026-06-15", "cqt", "2026-11-21 08:00")

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    ws = load_workbook(io.BytesIO(x.data))["Mua vào"]
    head = [h.value for h in ws[1]]
    assert head[6:8] == ["MST người bán", "Tên người bán"]
    assert head[-4:] == ["Tổng sau điều chỉnh (tạm tính)", "Trạng thái người bán", "Mức rủi ro", "Đánh giá"]
    rows = [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    assert [(r["Số HĐ"], r["Số HĐ ĐC/TT"]) for r in rows] == [(7, 9), (11, 30), (2, None)]
    tt, dc, bt = rows
    assert tt["Mức rủi ro"] == "CAO" and tt["Đánh giá"] == "Đã thay thế"
    assert dc["Nội dung điều chỉnh"] == "Điều chỉnh giảm" and dc["Tổng sau điều chỉnh (tạm tính)"] == 8_800_000
    assert dc["Mức rủi ro"] == "Chưa rõ" and bt["Đánh giá"] == "Bình thường"
    so_hd = [c for c in ws[1] if c.value in ("Số HĐ", "Số HĐ ĐC/TT")]
    assert all(ws.cell(2, c.column).number_format == "General" for c in so_hd)


# ---------- Chi tiết hàng hóa ----------
XML_BAN = """<?xml version="1.0" encoding="UTF-8"?>
<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TMA</KHHDon><SHDon>201</SHDon></TTChung>
<NDHDon><DSHHDVu>
 <HHDVu><TChat>1</TChat><STT>1</STT><MHHDVu>SP-001</MHHDVu><THHDVu>Thép cuộn CB240</THHDVu><DVTinh>kg</DVTinh>
  <SLuong>1500</SLuong><DGia>18500</DGia><TLCKhau>0</TLCKhau><STCKhau>0</STCKhau><ThTien>27750000</ThTien><TSuat>10%</TSuat></HHDVu>
 <HHDVu><TChat>1</TChat><STT>2</STT><MHHDVu>SP-002</MHHDVu><THHDVu>Dây buộc</THHDVu><DVTinh>cuộn</DVTinh>
  <SLuong>12.5</SLuong><DGia>40000</DGia><ThTien>500000</ThTien><TSuat>8%</TSuat></HHDVu>
 <HHDVu><TChat>3</TChat><STT>3</STT><THHDVu>Chiết khấu thương mại</THHDVu><ThTien>-250000</ThTien><TSuat>10%</TSuat></HHDVu>
</DSHHDVu></NDHDon></DLHDon></HDon>""".encode()


def test_doc_hang_hoa_xml():
    from thuedn.xmlhd import hang_hoa_tu_xml
    h = hang_hoa_tu_xml(XML_BAN)
    assert [d["ma_hang"] for d in h] == ["SP-001", "SP-002", None]
    assert h[0]["so_luong"] == 1500 and h[0]["don_gia"] == 18500 and h[0]["thue_suat"] == "10%"
    assert h[1]["so_luong"] == 12.5 and h[2]["tinh_chat"] == "Chiết khấu thương mại"


def test_sheet_chi_tiet(client, tmp_path):
    c, appmod = client
    import zipfile
    from thuedn.portal import normalize
    ban = _hd("0300000000", "C26TMA", 201, "2026-06-08", 28_000_000, 1)
    ban.update({"nmmst": "0400000000", "nmten": "Khách X"})
    appmod.store.save_invoice("0300000000", "ra", normalize(ban))
    appmod.store.save_invoice("0300000000", "vao", normalize(_hd("0100000001", "C26TAA", 11, "2026-06-05", 1_000_000, 1)))

    # luồng thật: lưu file zip cổng thuế trả về → đọc ra các dòng hàng hóa
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hd.xml", XML_BAN)
    inv_id = appmod.store.invoices(direction="ra")[0]["id"]
    appmod.luu_xml(inv_id, "x.zip", buf.getvalue())

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    wb = load_workbook(io.BytesIO(x.data))
    ws = wb["Chi tiết bán ra"]
    head = [h.value for h in ws[1]]
    rows = [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    assert len(rows) == 3 and all(r["Số HĐ"] == 201 and r["Tên đối tác"] == "Khách X" for r in rows)
    assert rows[0]["Mã hàng"] == "SP-001" and rows[0]["Số lượng"] == 1500
    assert rows[0]["Tiền thuế (tính theo thuế suất)"] == 2_775_000
    assert rows[1]["Tiền thuế (tính theo thuế suất)"] == 40_000
    assert rows[2]["Tính chất dòng"] == "Chiết khấu thương mại"

    mv = [dict(zip(head, r)) for r in wb["Chi tiết mua vào"].iter_rows(min_row=2, values_only=True)]
    assert len(mv) == 1 and mv[0]["Mã hàng"] is None and "Chưa có chi tiết" in mv[0]["Ghi chú"]


# ---------- Tổng hợp hạch toán, phân loại hàng hóa ----------
from thuedn.rules import goi_y_phan_loai  # noqa: E402


def test_goi_y_phan_loai():
    assert goi_y_phan_loai("vao", "Thép cuộn CB240", "kg", "Hàng hóa, dịch vụ") == "hang_hoa"
    assert goi_y_phan_loai("vao", "Phí vận chuyển", "chuyến", None) == "cp_qldn"
    assert goi_y_phan_loai("vao", "Cước internet tháng 10", None, None) == "cp_qldn"
    assert goi_y_phan_loai("vao", "Bàn làm việc", "tháng", None) == "cp_qldn"       # ĐVT dịch vụ
    assert goi_y_phan_loai("vao", "Chiết khấu thương mại", None, "Chiết khấu thương mại") == "chiet_khau"
    assert goi_y_phan_loai("ra", "Thép cuộn", "kg", None) == "dt_hang"
    assert goi_y_phan_loai("ra", "Dịch vụ lắp đặt", "lần", None) == "dt_dv"


def _xml_zip(lines):
    import zipfile
    x = "<HDon><DLHDon><NDHDon><DSHHDVu>" + "".join(
        f"<HHDVu><TChat>{t}</TChat><STT>{i + 1}</STT><MHHDVu>{m}</MHHDVu><THHDVu>{n}</THHDVu><DVTinh>{d}</DVTinh>"
        f"<SLuong>{q}</SLuong><DGia>{p}</DGia><ThTien>{tt}</ThTien><TSuat>{ts}</TSuat></HHDVu>"
        for i, (t, m, n, d, q, p, tt, ts) in enumerate(lines)) + "</DSHHDVu></NDHDon></DLHDon></HDon>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hd.xml", x.encode())
    return buf.getvalue()


def test_tong_hop_hach_toan(client):
    c, appmod = client
    from thuedn.portal import normalize
    st = appmod.store

    def them(direction, nb, so, tthai, lines):
        r = _hd(nb, "C26TAA", so, "2026-06-10", 1, tthai)
        st.save_invoice("0300000000", direction, normalize(r))
        iid = [i for i in st.invoices(direction=direction) if i["shdon"] == str(so) and i["nbmst"] == nb][0]["id"]
        appmod.luu_xml(iid, f"{so}.zip", _xml_zip(lines))

    them("vao", "0100000001", 1, 1, [(1, "SP-1", "Thép cuộn", "kg", 1000, 18000, 18_000_000, "10%"),
                                     (1, "VC", "Phí vận chuyển", "chuyến", 1, 500_000, 500_000, "8%")])
    them("vao", "0100000001", 2, 1, [(1, "SP-1", "Thép cuộn", "kg", 500, 19000, 9_500_000, "10%")])
    them("vao", "0100000002", 3, 1, [(1, "SP-1", "Giấy A4", "ram", 10, 60000, 600_000, "10%")])  # trùng mã, khác NB
    them("vao", "0100000001", 4, 4, [(1, "SP-1", "Thép cuộn", "kg", 999, 1, 999, "10%")])        # bị thay thế: bỏ
    st.save_invoice("0300000000", "vao", normalize(_hd("0100000009", "C26TZZ", 9, "2026-06-11", 2_000_000, 1)))

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    ws = load_workbook(io.BytesIO(x.data))["Tổng hợp hạch toán"]
    vals = [r for r in ws.iter_rows(values_only=True)]
    i_ma = next(i for i, r in enumerate(vals) if r[0] == "CHI TIẾT THEO MÃ HÀNG")
    loai = {r[2]: r for r in vals[4:i_ma] if r[1] in ("Mua vào", "Bán ra")}
    assert loai["Hàng hóa"][5] == 28_100_000 and loai["Hàng hóa"][4] == 2      # thép + giấy, 2 mặt hàng
    assert loai["Chi phí quản lý doanh nghiệp"][5] == 500_000
    assert loai["Chi phí quản lý doanh nghiệp"][6] == 40_000
    assert any("1 hóa đơn chưa có chi tiết" in str(r[2]) for r in vals[4:i_ma])

    head = vals[i_ma + 1]
    ma = [dict(zip(head, r)) for r in vals[i_ma + 2:]]
    thep = next(r for r in ma if r["Tên hàng hóa, dịch vụ"] == "Thép cuộn")
    assert thep["Số HĐ"] == 2 and thep["Số lượng"] == 1500 and thep["Thành tiền chưa thuế"] == 27_500_000
    assert thep["Đơn giá bình quân"] == 18333 and thep["TK gợi ý"] == "156"
    assert thep["Xác nhận phân loại"] == "Tự gợi ý, cần xem"
    assert len([r for r in ma if r["Mã hàng"] == "SP-1"]) == 2                    # tách theo người bán

    # trang phân loại: đổi Phí vận chuyển sang Chi phí bán hàng, TK 641
    page = c.get("/phan-loai?chieu=vao").get_data(as_text=True)
    assert "Phí vận chuyển" in page and "Gợi ý" in page
    import re
    idx = re.search(r'name="k_(\d+)" value="vao\|0100000001\|VC"', page).group(1)
    form = {"chieu": "vao", f"k_{idx}": "vao|0100000001|VC", f"pl_{idx}": "cp_bh", f"tk_{idx}": "6417"}
    assert c.post("/phan-loai", data=form).status_code == 302
    assert "Phí vận chuyển" not in c.get("/phan-loai?chieu=vao&chua_xn=1").get_data(as_text=True)

    ws = load_workbook(io.BytesIO(c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30").data))[
        "Tổng hợp hạch toán"]
    vals = [r for r in ws.iter_rows(values_only=True)]
    vc = next(r for r in vals if r[7] == "Phí vận chuyển")
    assert vc[2] == "Chi phí bán hàng" and vc[3] == "6417" and vc[-1] == "Đã xác nhận"


def test_chi_tiet_dieu_chinh_thay_the(client):
    c, appmod = client
    from thuedn.portal import normalize
    st = appmod.store

    def them(so, ngay, tthai, lines, goc=None):
        r = _hd("0300000000", "C26TMA", so, ngay, 1, tthai, goc)
        r.update({"nmmst": "0400000000", "nmten": "Khách X"})
        st.save_invoice("0300000000", "ra", normalize(r))
        iid = [i for i in st.invoices(direction="ra") if i["shdon"] == str(so)][0]["id"]
        if lines:
            appmod.luu_xml(iid, f"{so}.zip", _xml_zip(lines))

    # gốc tháng 9, bị điều chỉnh 2 lần trong tháng 10
    them(150, "2026-09-10", 5, [(1, "SP-1", "Thép cuộn", "kg", 2000, 18500, 37_000_000, "10%"),
                                (1, "SP-2", "Dây buộc", "cuộn", 50, 40000, 2_000_000, "10%")])
    them(210, "2026-10-05", 3, [(1, "SP-1", "Thép cuộn", "kg", -100, 18500, -1_850_000, "10%")],
         ("C26TMA", 150, "2026-09-10"))
    them(220, "2026-10-12", 3, [(1, "SP-1", "Thép cuộn", "kg", 0, -500, -950_000, "10%"),
                                (1, "SP-9", "Hàng lạ", "cái", 1, 100, 100, "10%")],
         ("C26TMA", 150, "2026-09-10"))
    # bị thay thế và thay thế trong tháng 10
    them(230, "2026-10-20", 4, [(1, "SP-3", "Ống thép", "cây", 10, 90000, 900_000, "10%")])
    them(231, "2026-10-21", 2, [(1, "SP-3", "Ống thép", "cây", 10, 85000, 850_000, "10%")],
         ("C26TMA", 230, "2026-10-20"))
    # hóa đơn thường nhiều mặt hàng
    them(240, "2026-10-25", 1, [(1, "SP-1", "Thép cuộn", "kg", 300, 18500, 5_550_000, "10%"),
                                (1, "SP-2", "Dây buộc", "cuộn", 5, 40000, 200_000, "10%")])

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-10-01&den=2026-10-31")
    ws = load_workbook(io.BytesIO(x.data))["Chi tiết bán ra"]
    head = [h.value for h in ws[1]]
    rows = [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    assert [(r["Số HĐ"], r["STT dòng"]) for r in rows] == [
        (150, 1), (150, 2), (210, 1), (220, 1), (220, 2),     # gốc rồi ngay dưới là 2 HĐ điều chỉnh
        (230, 1), (231, 1),                                   # bị thay thế rồi HĐ thay thế
        (240, 1), (240, 2)]                                   # nhiều mặt hàng: mỗi mặt hàng một hàng
    by = {(r["Số HĐ"], r["STT dòng"]): r for r in rows}

    # điểm 2: tính vào tổng
    assert by[(150, 1)]["Tính vào tổng"] == "Không" and "kỳ khác" in by[(150, 1)]["Ghi chú"]
    assert by[(230, 1)]["Tính vào tổng"] == "Không" and "bị thay thế" in by[(230, 1)]["Ghi chú"]
    assert all(by[k]["Tính vào tổng"] == "Có" for k in [(210, 1), (220, 1), (231, 1), (240, 1)])
    tong = sum(r["Thành tiền chưa thuế"] for r in rows if r["Tính vào tổng"] == "Có")
    assert tong == -1_850_000 - 950_000 + 100 + 850_000 + 5_550_000 + 200_000

    # điểm 3: sau điều chỉnh, ghép theo mã hàng
    assert by[(150, 1)]["SL sau điều chỉnh"] == 1900
    assert by[(150, 1)]["Thành tiền sau điều chỉnh"] == 37_000_000 - 1_850_000 - 950_000
    assert "C26TMA số 210" in by[(150, 1)]["Ghi chú"] and "C26TMA số 220" in by[(150, 1)]["Ghi chú"]
    assert by[(150, 2)]["SL sau điều chỉnh"] is None                # dòng không bị điều chỉnh
    assert by[(210, 1)]["Ghi chú"] == "Ghép với dòng 1 của HĐ gốc"
    assert "Không ghép được" in by[(220, 2)]["Ghi chú"]
    assert by[(231, 1)]["Ghi chú"] == "Thay thế toàn bộ HĐ gốc"
    assert by[(240, 1)]["Số HĐ"] == by[(240, 2)]["Số HĐ"] and by[(240, 2)]["Tên đối tác"] == "Khách X"

    # tô màu: xám cho dòng không tính, vàng cho dòng không ghép được
    fill = {(r[5].value, r[10].value): r[0].fill.fgColor.rgb for r in ws.iter_rows(min_row=2)}
    assert fill[(230, 1)].endswith("E7E9ED") and fill[(220, 2)].endswith("FFF3CD")


def test_nhieu_doanh_nghiep(client):
    """10 công ty dùng chung một ứng dụng; xuất Excel riêng từng công ty."""
    c, appmod = client
    import zipfile
    from thuedn.portal import normalize
    for k in range(10):
        mst = f"03000000{k:02d}"
        c.post("/companies", data={"name": f"Công ty số {k}/ABC", "mst": mst, "password": "mat-khau"})
        appmod.store.save_invoice(mst, "vao", normalize(_hd("0100000001", "C26TAA", 100 + k, "2026-06-10", 1_000_000, 1)))
    assert len(appmod.store.companies()) == 10

    page = c.get("/results?tu=2026-06-01&den=2026-06-30").get_data(as_text=True)
    assert "Tất cả (10)" in page and "Excel từng DN (.zip)" in page

    # lọc một công ty
    page = c.get("/results?mst=0300000003&tu=2026-06-01&den=2026-06-30").get_data(as_text=True)
    assert "1 hóa đơn" in page

    r = c.get("/export-tung-dn.zip?tu=2026-06-01&den=2026-06-30")
    z = zipfile.ZipFile(io.BytesIO(r.data))
    names = sorted(z.namelist())
    assert len(names) == 10
    assert names[3] == "0300000003 Công ty số 3 ABC 2026-06-01_2026-06-30.xlsx"
    ws = load_workbook(io.BytesIO(z.read(names[3])))["Mua vào"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 1 and rows[0][1] == "0300000003" and rows[0][5] == 103

    x = c.get("/export.xlsx?mst=0300000003&tu=2026-06-01&den=2026-06-30")
    assert "bang-ke_0300000003_" in x.headers["Content-Disposition"]


# ---------- Google Drive: mỗi công ty một email ----------
class _Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code, self.text = data, status, str(data)

    def json(self):
        return self._d


class FakeGoogle:
    """Mô phỏng Google: đăng nhập theo email, mỗi email một Drive riêng."""
    def __init__(self):
        self.drives: dict[str, list[dict]] = {}
        self.revoked: list[str] = []
        self.n = 0

    def _email(self, headers):
        return headers["Authorization"].split("at:", 1)[1]

    def post(self, url, data=None, json=None, params=None, headers=None, timeout=None):
        from thuedn import gdrive
        if url == gdrive.TOKEN_URL:
            if data["grant_type"] == "authorization_code":
                e = data["code"].split("code:", 1)[1]
                # "|khong-drive": người dùng bỏ tick ô quyền Google Drive ở màn hình xin quyền
                e, bo_drive = e.split("|")[0], e.endswith("|khong-drive")
                scope = "openid https://www.googleapis.com/auth/userinfo.email" + (
                    "" if bo_drive else " https://www.googleapis.com/auth/drive.file")
                return _Resp({"access_token": f"at:{e}", "refresh_token": f"rt:{e}", "scope": scope})
            return _Resp({"access_token": "at:" + data["refresh_token"].split("rt:", 1)[1]})
        if url == gdrive.REVOKE_URL:
            self.revoked.append(data["token"])
            return _Resp({})
        e = self._email(headers)
        if url == gdrive.FILES_URL:                                   # tạo thư mục
            return _Resp({"id": self._add(e, json["name"], json["mimeType"], json.get("parents"), None)})
        if url == gdrive.UPLOAD_URL:
            meta, content = self._parse(data, headers)
            return _Resp({"id": self._add(e, meta["name"], "file", meta["parents"], content)})
        raise AssertionError(url)

    def patch(self, url, data=None, params=None, headers=None, timeout=None):
        e = self._email(headers)
        fid = url.rsplit("/", 1)[1]
        _, content = self._parse(data, headers)
        next(f for f in self.drives[e] if f["id"] == fid)["content"] = content
        return _Resp({"id": fid})

    def get(self, url, params=None, headers=None, timeout=None):
        from thuedn import gdrive
        import re
        e = self._email(headers)
        if url == gdrive.USERINFO_URL:
            return _Resp({"email": e})
        q = params["q"]
        name = re.search(r"name = '((?:[^'\\]|\\.)*)'", q).group(1).replace("\\'", "'")
        parent = re.search(r"'([^']+)' in parents", q).group(1)
        folder = "mimeType = " in q
        found = [f for f in self.drives.get(e, []) if f["name"] == name
                 and (f["parents"] or ["root"])[0] == parent and (f["mime"] == gdrive.FOLDER_MIME) == folder]
        return _Resp({"files": [{"id": f["id"], "name": f["name"]} for f in found]})

    def _add(self, e, name, mime, parents, content):
        self.n += 1
        self.drives.setdefault(e, []).append({"id": f"f{self.n}", "name": name, "mime": mime,
                                              "parents": parents, "content": content})
        return f"f{self.n}"

    def _parse(self, body, headers):
        import json
        b = headers["Content-Type"].split("boundary=")[1].encode()
        parts = body.split(b"--" + b)
        meta = json.loads(parts[1].split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0])
        content = parts[2].split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
        return meta, content

    def path(self, e, f):
        """Đường dẫn đầy đủ của một file trong Drive của email e."""
        by = {x["id"]: x for x in self.drives[e]}
        p = [f["name"]]
        while f["parents"]:
            f = by[f["parents"][0]]
            p.insert(0, f["name"])
        return "/".join(p)


@pytest.fixture()
def google(client, monkeypatch):
    from thuedn import gdrive
    fake = FakeGoogle()
    monkeypatch.setattr(gdrive, "http", fake)
    c, appmod = client
    c.post("/cai-dat", data={"client_id": "cid.apps.googleusercontent.com", "client_secret": "bi-mat"})
    return fake


def _ket_noi(c, mst, dang_nhap_email):
    from urllib.parse import parse_qs, urlparse
    r = c.post(f"/google/ket-noi/{mst}")
    q = parse_qs(urlparse(r.headers["Location"]).query)
    assert "drive.file" in q["scope"][0]
    return c.get(f"/google/callback?state={q['state'][0]}&code=code:{dang_nhap_email}"), q


def test_google_drive_moi_cong_ty_mot_email(client, google):
    c, appmod = client
    st = appmod.store
    from thuedn.portal import normalize
    c.post("/companies", data={"name": "Công ty A", "mst": "0300000001", "password": "x", "email": "KeToan.A@gmail.com"})
    c.post("/companies", data={"name": "Công ty B", "mst": "0300000002", "password": "x", "email": "ketoan.b@gmail.com"})
    assert st.company("0300000001")["email"] == "ketoan.a@gmail.com"
    assert b"bi-mat" not in st.db.execute("SELECT v FROM settings WHERE k='google_client_secret'").fetchone()[0]

    # đăng nhập nhầm email B khi kết nối công ty A → từ chối, không lưu, thu hồi quyền
    r, q = _ket_noi(c, "0300000001", "ketoan.b@gmail.com")
    assert q["login_hint"] == ["ketoan.a@gmail.com"]
    assert st.google_token("0300000001") is None and google.revoked == ["rt:ketoan.b@gmail.com"]
    assert "Không lưu kết nối" in c.get("/").get_data(as_text=True)

    # đúng email nhưng bỏ tick ô quyền Google Drive → từ chối, báo rõ cần tick ô nào
    r, _ = _ket_noi(c, "0300000001", "ketoan.a@gmail.com|khong-drive")
    assert st.google_token("0300000001") is None and google.revoked[-1] == "rt:ketoan.a@gmail.com"
    assert "tick" in c.get("/").get_data(as_text=True)

    # đăng nhập đúng email
    _ket_noi(c, "0300000001", "ketoan.a@gmail.com")
    _ket_noi(c, "0300000002", "ketoan.b@gmail.com")
    assert st.google_token("0300000001") == "rt:ketoan.a@gmail.com"
    raw = st.db.execute("SELECT google_token FROM companies WHERE mst='0300000001'").fetchone()[0]
    assert b"rt:ketoan" not in raw                                      # token lưu mã hóa
    assert "Đã kết nối" in c.get("/").get_data(as_text=True)

    for mst, so in (("0300000001", 11), ("0300000002", 22)):
        st.save_invoice(mst, "vao", normalize(_hd("0100000001", "C26TAA", so, "2026-06-10", 1_000_000, 1)))

    r = c.post("/drive/day-len", data={"mst": ["0300000001", "0300000002"], "tu": "2026-06-01", "den": "2026-06-30"})
    assert r.status_code == 302
    for email, mst, so in (("ketoan.a@gmail.com", "0300000001", 11), ("ketoan.b@gmail.com", "0300000002", 22)):
        files = [f for f in google.drives[email] if f["content"] is not None]
        thu_muc = f"Hóa đơn {mst} - Công ty {'A' if mst.endswith('1') else 'B'}/2026-06"
        assert [google.path(email, f) for f in files] == [
            f"{thu_muc}/Bảng kê {mst} 2026-06.xlsx", f"{thu_muc}/Nhập MISA {mst} 2026-06.xlsx"]
        ws = load_workbook(io.BytesIO(files[0]["content"]))["Mua vào"]
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        assert [(r[1], r[5]) for r in rows] == [(mst, so)]               # chỉ dữ liệu của đúng công ty

    # đẩy lại cùng kỳ: ghi đè, không tạo file trùng
    c.post("/drive/day-len", data={"mst": "0300000001", "tu": "2026-06-01", "den": "2026-06-30"})
    assert len([f for f in google.drives["ketoan.a@gmail.com"] if f["content"] is not None]) == 2

    # đổi email công ty A → tự ngắt kết nối cũ, không đẩy được nữa
    c.post("/companies", data={"name": "Công ty A", "mst": "0300000001", "password": "x", "email": "moi.a@gmail.com"})
    assert st.google_token("0300000001") is None
    c.post("/drive/day-len", data={"mst": "0300000001", "tu": "2026-06-01", "den": "2026-06-30"})
    assert "moi.a@gmail.com" not in google.drives


def test_tai_hoa_don_xong_tu_day_len_drive(client, google):
    c, appmod = client
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau", "email": "a@gmail.com"})
    c.post("/companies", data={"name": "DN chưa kết nối", "mst": "0300000009", "password": "mat-khau"})
    _ket_noi(c, "0300000000", "a@gmail.com")
    c.post("/download", data={"mst": ["0300000000", "0300000009"], "loai": ["vao", "ra"],
                              "tu": "2026-06-01", "den": "2026-06-30", "drive": "on"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})
    c.get("/captcha")
    c.post("/captcha", data={"cvalue": "abc12"})
    c.get("/captcha")
    log = " | ".join(appmod.job["log"])
    assert "DN A: đã đẩy 2 file lên Drive a@gmail.com" in log
    assert "DN chưa kết nối: chưa kết nối Google Drive" in log
    assert list(google.drives) == ["a@gmail.com"]


def test_tai_khoan_theo_thong_tu_133(client):
    c, appmod = client
    from thuedn.rules import bang_phan_loai
    tt133, tt200 = bang_phan_loai("TT133"), bang_phan_loai("TT200")
    assert tt133["vao"]["cp_qldn"][1] == "6422" and tt133["vao"]["cp_bh"][1] == "6421"
    assert tt133["vao"]["cp_sx"][1] == "154" and tt133["ra"]["chiet_khau"][1] == "511"
    assert tt133["vao"]["hang_hoa"][1] == "156" and tt200["vao"]["cp_qldn"][1] == "642"

    from thuedn.portal import normalize
    st = appmod.store
    st.save_invoice("0300000000", "vao", normalize(_hd("0100000001", "C26TAA", 1, "2026-06-10", 1, 1)))
    iid = st.invoices()[0]["id"]
    appmod.luu_xml(iid, "1.zip", _xml_zip([(1, "VC", "Phí vận chuyển", "chuyến", 1, 500_000, 500_000, "8%")]))

    assert "Thông tư 133" in c.get("/cai-dat").get_data(as_text=True)        # mặc định TT133
    page = c.get("/phan-loai?chieu=vao").get_data(as_text=True)
    assert 'value="6422"' in page and "Thông tư 133" in page
    c.post("/cai-dat", data={"che_do": "TT200"})
    assert 'value="642"' in c.get("/phan-loai?chieu=vao").get_data(as_text=True)


# ---------- File nhập MISA ----------
def test_file_nhap_misa(client):
    c, appmod = client
    from thuedn.portal import normalize
    st = appmod.store

    def them(direction, nb, so, tthai, lines, goc=None, ngay="2026-10-05"):
        r = _hd(nb, "C26TAA", so, ngay, 1, tthai, goc)
        r.update({"nbten": f"NCC {nb[-1]}", "tgtcthue": 9_000_000, "tgtthue": 900_000})
        if direction == "ra":
            r.update({"nbmst": "0300000000", "nmmst": nb, "nmten": f"Khách {nb[-1]}"})
        st.save_invoice("0300000000", direction, normalize(r))
        iid = [i for i in st.invoices(direction=direction) if i["shdon"] == str(so)][0]["id"]
        if lines:
            appmod.luu_xml(iid, f"{so}.zip", _xml_zip(lines))

    them("vao", "0100000001", 11, 1, [(1, "TP-1", "Thép cuộn", "kg", 1000, 18000, 18_000_000, "10%"),
                                      (1, "VC", "Phí vận chuyển", "chuyến", 1, 500_000, 500_000, "8%"),
                                      (4, "", "Hàng giao tại kho bên mua", "", "", "", "", "")])
    them("vao", "0100000002", 12, 1, [(1, "ML", "Máy lạnh 2HP", "bộ", 1, 24_500_000, 24_500_000, "10%")])
    them("vao", "0100000003", 13, 4, [(1, "X", "Hàng X", "cái", 1, 1, 1, "10%")])          # bị thay thế
    them("vao", "0100000004", 14, 1, None)                                                 # chưa có XML
    them("ra", "0400000001", 201, 1, [(1, "SP-1", "Thép cuộn", "kg", 500, 21000, 10_500_000, "10%"),
                                      (1, "DV", "Phí giao hàng", "chuyến", 1, 800_000, 800_000, "8%")])
    them("ra", "0400000001", 209, 3, [(1, "SP-1", "Thép cuộn", "kg", -10, 21000, -210_000, "10%")],
         ("C26TAA", 201, "2026-10-05"), ngay="2026-10-15")
    # anh/chị đã xác nhận: máy lạnh là TSCĐ, mã MISA "MAYLANH-01"; thép là hàng hóa nhập kho "KHO1"
    st.set_category("vao", "0100000002", "ML", "tscd", "211", "x", "MAYLANH-01", None)
    st.set_category("vao", "0100000001", "TP-1", "hang_hoa", "156", "x", "THEP-CB240", "KHO1")

    x = c.get("/export-misa?mst=0300000000&tu=2026-10-01&den=2026-10-31")
    assert "Nhap MISA 0300000000" in x.headers["Content-Disposition"]
    wb = load_workbook(io.BytesIO(x.data))
    assert wb.sheetnames == ["Mua hàng", "Bán hàng", "Kiểm tra trước khi nhập"]

    def doc(ws):
        head = [h.value for h in ws[1]]
        return [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]

    mua = doc(wb["Mua hàng"])
    assert [(r["Số chứng từ (*)"], r["Tên hàng"]) for r in mua] == [
        ("MV-C26TAA-11", "Thép cuộn"), ("MV-C26TAA-11", "Phí vận chuyển"),     # dòng ghi chú bị bỏ
        ("MV-C26TAA-12", "Máy lạnh 2HP"), ("MV-C26TAA-14", "Theo HĐ C26TAA số 14")]   # HĐ 13 bị thay thế: không nhập
    thep, vc, ml, thieu = mua
    assert (thep["TK nợ (*)"], thep["TK có (*)"], thep["TK thuế GTGT"]) == ("156", "331", "1331")
    assert thep["Mã hàng (*)"] == "THEP-CB240" and thep["Mã kho"] == "KHO1"
    assert thep["Ngày hạch toán (*)"] == "05/10/2026" and thep["Mã nhà cung cấp"] == "0100000001"
    assert thep["% thuế GTGT"] == 10 and thep["Tiền thuế GTGT"] == 1_800_000
    assert vc["TK nợ (*)"] == "6422" and vc["% thuế GTGT"] == 8 and vc["Tiền thuế GTGT"] == 40_000   # TT133
    assert (ml["TK nợ (*)"], ml["TK thuế GTGT"], ml["Mã hàng (*)"]) == ("211", "1332", "MAYLANH-01")
    assert thieu["TK nợ (*)"] is None and thieu["Thành tiền"] == 9_000_000

    ban = doc(wb["Bán hàng"])
    assert [(r["Số chứng từ (*)"], r["TK nợ (*)"], r["TK có (*)"], r["TK thuế GTGT"]) for r in ban] == [
        ("BR-C26TAA-201", "131", "5111", "33311"), ("BR-C26TAA-201", "131", "5113", "33311"),
        ("BR-C26TAA-209", "131", "5111", "33311")]
    assert "điều chỉnh cho HĐ C26TAA số 201" in ban[2]["Diễn giải"] and ban[2]["Thành tiền"] == -210_000

    kt = doc(wb["Kiểm tra trước khi nhập"])
    ly_do = {(r["Số hóa đơn"], r["Tên hàng"]): r["Cần xem"] for r in kt}
    assert "chưa xác nhận" in ly_do[(11, "Phí vận chuyển")]
    assert (11, "Thép cuộn") not in ly_do and (12, "Máy lạnh 2HP") not in ly_do        # đã xác nhận
    assert "Chưa có chi tiết hàng hóa" in ly_do[(14, "Theo HĐ C26TAA số 14")]
    assert ly_do[(13, "Bị thay thế")].startswith("KHÔNG NHẬP")

    # nhiều công ty: mỗi công ty một file trong .zip
    import zipfile
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "x"})
    c.post("/companies", data={"name": "DN B", "mst": "0300000005", "password": "x"})
    z = zipfile.ZipFile(io.BytesIO(c.get("/export-misa?tu=2026-10-01&den=2026-10-31").data))
    assert sorted(z.namelist()) == ["Nhap MISA 0300000000 DN A 2026-10-01_2026-10-31.xlsx",
                                    "Nhap MISA 0300000005 DN B 2026-10-01_2026-10-31.xlsx"]


def test_dinh_dang_so_khong_thua_dau_phan_cach():
    from openpyxl import Workbook
    from thuedn.export import dinh_dang_so
    ws = Workbook().active
    for v, fmt, kq in ((2000.0, "#,##0", 2000), (12.5, "#,##0.###", 12.5), (42000000, "#,##0", 42000000)):
        ws["A1"] = v
        dinh_dang_so(ws["A1"])
        assert ws["A1"].number_format == fmt and ws["A1"].value == kq and type(ws["A1"].value) is type(kq)


# ---------- 3 cấp tài khoản ----------
def test_khoi_tao_admin_dau_tien(tmp_path, monkeypatch):
    monkeypatch.setenv("THUEDN_DATA", str(tmp_path))
    sys.modules.pop("app", None)
    import app as appmod
    c = appmod.app.test_client()
    assert c.get("/").headers["Location"].endswith("/khoi-tao")          # chưa có tài khoản nào
    r = c.post("/khoi-tao", data={"ho_ten": "Anh A", "email": "Boss@Cty.vn", "mat_khau": "ngan", "mat_khau2": "ngan"})
    assert not appmod.store.users()                                       # mật khẩu yếu: không tạo
    c.post("/khoi-tao", data={"ho_ten": "Anh A", "email": "Boss@Cty.vn", "mat_khau": "Abc12345", "mat_khau2": "Abc12345"})
    u = appmod.store.user_by_email("boss@cty.vn")
    assert u["vai_tro"] == "admin" and u["pw_hash"] != "Abc12345"         # mật khẩu lưu dạng băm
    assert c.get("/").status_code == 200                                  # đã đăng nhập luôn
    assert c.get("/khoi-tao").headers["Location"].endswith("/dang-nhap")   # không tạo lại được


def test_dang_nhap_sai_va_khoa_tam(client):
    c, appmod = client
    c.post("/dang-xuat")
    assert c.get("/results").headers["Location"].startswith("/dang-nhap")
    assert c.post("/dang-nhap", data={"email": "admin@test.vn", "mat_khau": "sai"}).status_code == 401
    for _ in range(4):
        c.post("/dang-nhap", data={"email": "admin@test.vn", "mat_khau": "sai"})
    # sai 5 lần: khóa tạm, kể cả nhập đúng
    assert c.post("/dang-nhap", data={"email": "admin@test.vn", "mat_khau": MAT_KHAU}).status_code == 429
    appmod.lan_sai.clear()
    r = c.post("/dang-nhap?next=/results", data={"email": "admin@test.vn", "mat_khau": MAT_KHAU})
    assert r.headers["Location"] == "/results"
    r = c.post("/dang-nhap?next=//evil.com", data={"email": "admin@test.vn", "mat_khau": MAT_KHAU})
    assert r.headers["Location"] == "/"                                   # không chuyển hướng ra ngoài


def test_quyen_nguoi_su_dung(client):
    c, appmod = client
    c.post("/companies", data={"name": "DN A", "mst": "0300000000", "password": "mat-khau", "email": "a@gmail.com"})
    tao_tai_khoan(appmod, "nv@test.vn", "nguoi_dung")
    dang_nhap(c, "nv@test.vn")
    page = c.get("/").get_data(as_text=True)
    assert "Người sử dụng" in page and "DN A" in page
    assert "Thêm doanh nghiệp" not in page and "Xóa</button>" not in page and "Kết nối Drive" not in page
    assert "Cài đặt</a>" not in page and "Tài khoản</a>" not in page
    # được dùng phần mềm
    for url in ("/results", "/suppliers", "/phan-loai", "/doi-tac", "/export.xlsx", "/doi-mat-khau"):
        assert c.get(url).status_code == 200, url
    # không được thêm / xóa doanh nghiệp, đổi cài đặt, kết nối Drive, nhập danh sách rủi ro, quản lý tài khoản
    for method, url, data in (("post", "/companies", {"name": "X", "mst": "0399999999", "password": "x"}),
                              ("post", "/companies/0300000000/delete", {}),
                              ("get", "/cai-dat", None), ("post", "/cai-dat", {"che_do": "TT200"}),
                              ("post", "/google/ket-noi/0300000000", {}),
                              ("post", "/danh-sach-rui-ro", {"loai": "rui_ro_cao", "noi_dung": "0100000001"}),
                              ("get", "/tai-khoan", None),
                              ("post", "/tai-khoan/them", {"email": "x@y.vn", "vai_tro": "admin", "mat_khau": "Abc12345"})):
        r = getattr(c, method)(url, data=data)
        assert r.status_code == 303 and r.headers["Location"] == "/", url
    assert [x["mst"] for x in appmod.store.companies()] == ["0300000000"]
    assert appmod.store.setting("che_do") is None and appmod.store.user_by_email("x@y.vn") is None


def test_quan_tri_khong_dung_toi_admin(client):
    c, appmod = client
    admin2 = tao_tai_khoan(appmod, "admin2@test.vn", "admin")
    tao_tai_khoan(appmod, "qt@test.vn", "quan_tri")
    nv = tao_tai_khoan(appmod, "nv@test.vn", "nguoi_dung")
    dang_nhap(c, "qt@test.vn")
    # Quản trị làm được việc quản lý
    assert c.get("/cai-dat").status_code == 200
    c.post("/companies", data={"name": "DN B", "mst": "0300000001", "password": "x"})
    assert appmod.store.company("0300000001") is not None
    page = c.get("/tai-khoan").get_data(as_text=True)
    assert f'action="/tai-khoan/{nv}/sua"' in page and f'action="/tai-khoan/{admin2}/sua"' not in page
    assert '<option value="admin"' not in page                            # không chọn được vai trò Admin
    # tạo được Người sử dụng / Quản trị, không tạo được Admin
    c.post("/tai-khoan/them", data={"email": "moi@test.vn", "vai_tro": "nguoi_dung", "mat_khau": "Abc12345"})
    c.post("/tai-khoan/them", data={"email": "hack@test.vn", "vai_tro": "admin", "mat_khau": "Abc12345"})
    assert appmod.store.user_by_email("moi@test.vn") and appmod.store.user_by_email("hack@test.vn") is None
    # không sửa / khóa / xóa được Admin, không nâng ai lên Admin
    c.post(f"/tai-khoan/{admin2}/xoa")
    c.post(f"/tai-khoan/{admin2}/sua", data={"vai_tro": "nguoi_dung", "hoat_dong": "0"})
    c.post(f"/tai-khoan/{nv}/sua", data={"vai_tro": "admin", "hoat_dong": "1"})
    assert appmod.store.user(admin2)["vai_tro"] == "admin" and appmod.store.user(admin2)["hoat_dong"] == 1
    assert appmod.store.user(nv)["vai_tro"] == "nguoi_dung"
    # sửa, khóa, đặt lại mật khẩu, xóa Người sử dụng thì được
    c.post(f"/tai-khoan/{nv}/sua", data={"vai_tro": "nguoi_dung", "hoat_dong": "0", "mat_khau": "MoiMoi999"})
    assert appmod.store.user(nv)["hoat_dong"] == 0
    assert dang_nhap(c, "nv@test.vn", "MoiMoi999").status_code == 403    # tài khoản bị khóa
    dang_nhap(c, "qt@test.vn")
    c.post(f"/tai-khoan/{nv}/xoa")
    assert appmod.store.user(nv) is None


def test_admin_toan_quyen_va_giu_it_nhat_mot_admin(client):
    c, appmod = client
    me = appmod.store.user_by_email("admin@test.vn")["id"]
    qt = tao_tai_khoan(appmod, "qt@test.vn", "quan_tri")
    # không tự hạ quyền / khóa / xóa chính mình
    c.post(f"/tai-khoan/{me}/sua", data={"vai_tro": "nguoi_dung", "hoat_dong": "1"})
    c.post(f"/tai-khoan/{me}/xoa")
    assert appmod.store.user(me)["vai_tro"] == "admin"
    # Admin nâng Quản trị lên Admin, tạo Admin mới, rồi xóa Admin khác
    c.post(f"/tai-khoan/{qt}/sua", data={"vai_tro": "admin", "hoat_dong": "1"})
    assert appmod.store.user(qt)["vai_tro"] == "admin"
    c.post("/tai-khoan/them", data={"email": "a3@test.vn", "vai_tro": "admin", "mat_khau": "Abc12345"})
    a3 = appmod.store.user_by_email("a3@test.vn")["id"]
    c.post(f"/tai-khoan/{a3}/xoa")
    assert appmod.store.user(a3) is None
    # Admin cuối cùng: Admin khác không khóa hay xóa được nếu chỉ còn 1
    c.post(f"/tai-khoan/{qt}/sua", data={"vai_tro": "nguoi_dung", "hoat_dong": "1"})
    assert appmod.store.so_admin_hoat_dong() == 1
    dang_nhap(c, "admin@test.vn")
    assert "Admin" in c.get("/").get_data(as_text=True)


def test_quy_tac_quyen():
    from thuedn.quyen import co_quyen, gan_duoc, kiem_tra_mat_khau, quan_ly_duoc
    assert co_quyen("nguoi_dung", "su_dung") and not co_quyen("nguoi_dung", "quan_ly")
    assert co_quyen("quan_tri", "quan_ly") and co_quyen("admin", "tai_khoan")
    assert quan_ly_duoc("admin", "admin") and not quan_ly_duoc("quan_tri", "admin")
    assert quan_ly_duoc("quan_tri", "quan_tri") and not quan_ly_duoc("nguoi_dung", "nguoi_dung")
    assert gan_duoc("admin", "admin") and not gan_duoc("quan_tri", "admin") and not gan_duoc("admin", "vua")
    assert kiem_tra_mat_khau("abc12345") is None and kiem_tra_mat_khau("abcdefgh") and kiem_tra_mat_khau("a1")


def test_lenh_tao_tai_khoan(tmp_path):
    from thuedn.storage import Storage
    from werkzeug.security import check_password_hash
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tao_tai_khoan import tao_hoac_cap_nhat
    st = Storage(tmp_path)
    assert "Đã tạo" in tao_hoac_cap_nhat(st, "Sep@Cty.vn", "admin", "Sếp", "Abc12345")
    tao_hoac_cap_nhat(st, "qt@cty.vn", "quan_tri", "QT", "Abc12345")
    u = st.user_by_email("sep@cty.vn")
    assert u["vai_tro"] == "admin" and check_password_hash(u["pw_hash"], "Abc12345")
    with pytest.raises(ValueError):
        tao_hoac_cap_nhat(st, "x@cty.vn", "vua", "", "Abc12345")
    with pytest.raises(ValueError):
        tao_hoac_cap_nhat(st, "x@cty.vn", "nguoi_dung", "", "yeu")
    # đã có: đổi vai trò, mở khóa, giữ mật khẩu cũ khi không nhập
    st.update_user(st.user_by_email("qt@cty.vn")["id"], hoat_dong=0)
    tao_hoac_cap_nhat(st, "qt@cty.vn", "nguoi_dung", "", None)
    u = st.user_by_email("qt@cty.vn")
    assert u["vai_tro"] == "nguoi_dung" and u["hoat_dong"] == 1 and check_password_hash(u["pw_hash"], "Abc12345")


def test_ket_noi_drive_chi_tren_may_chinh(client, google):
    c, appmod = client
    c.post("/companies", data={"name": "DN A", "mst": "0300000001", "password": "x", "email": "a@gmail.com"})
    # mở từ máy khác trong mạng (địa chỉ IP): đăng nhập được, nhưng không cho bắt đầu kết nối Google
    lan = "http://192.168.1.10:5000"
    c.post("/dang-nhap", data={"email": "admin@test.vn", "mat_khau": MAT_KHAU}, base_url=lan)
    assert c.get("/results", base_url=lan).status_code == 200
    r = c.post("/google/ket-noi/0300000001", base_url=lan)
    assert r.headers["Location"] == "/"
    assert "phải làm trên máy chính" in c.get("/", base_url=lan).get_data(as_text=True)
    # trên chính máy đó (127.0.0.1) thì được
    may_chinh = "http://127.0.0.1:5000"
    c.post("/dang-nhap", data={"email": "admin@test.vn", "mat_khau": MAT_KHAU}, base_url=may_chinh)
    r = c.post("/google/ket-noi/0300000001", base_url=may_chinh)
    assert r.headers["Location"].startswith("https://accounts.google.com/")


def test_ip_noi_bo_khong_loi():
    import importlib
    ip = importlib.import_module("app").ip_noi_bo() if "app" in sys.modules else None
    assert ip is None or ip.count(".") == 3
