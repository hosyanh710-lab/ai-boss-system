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
    yield appmod.app.test_client(), appmod


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
    r = c.get("/captcha")
    assert r.headers["Location"].endswith("/results")

    page = c.get("/results").get_data(as_text=True)
    assert "NCC Hai" in page and "Khách X" in page and "Hóa đơn điều chỉnh" in page

    # đánh dấu NCC Hai đã chấm dứt trước ngày lập → rủi ro cao
    c.get("/suppliers")
    c.post("/suppliers/0100000002", data={"status": "cham_dut", "ngay_ngung": "2026-06-15", "nguon": "cqt"})
    assert "Rủi ro CAO" in c.get("/results").get_data(as_text=True)

    x = c.get("/export.xlsx?mst=0300000000&tu=2026-06-01&den=2026-06-30")
    wb = load_workbook(io.BytesIO(x.data))
    assert wb.sheetnames == ["Mua vào", "Bán ra", "Điều chỉnh - thay thế"]
    assert wb["Mua vào"].max_row == 3 and wb["Bán ra"].max_row == 2
    assert wb["Điều chỉnh - thay thế"].max_row == 2
    cao = [r for r in wb["Mua vào"].iter_rows(values_only=True) if r[-1] == "CAO"]
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
