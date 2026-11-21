"""Lưu dữ liệu trên máy: SQLite + mã hóa mật khẩu cổng thuế.

Khóa mã hóa nằm ở data/secret.key, chỉ trên máy này. Mất file đó thì phải
nhập lại mật khẩu các doanh nghiệp.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    mst TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enc_password BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_mst TEXT NOT NULL,
    direction TEXT NOT NULL,          -- 'vao' (mua vào) | 'ra' (bán ra)
    nbmst TEXT, nbten TEXT,           -- người bán
    nmmst TEXT, nmten TEXT,           -- người mua
    khmshdon TEXT, khhdon TEXT, shdon TEXT,
    tdlap TEXT,                       -- ngày lập, YYYY-MM-DD
    tgtcthue REAL, tgtthue REAL, tgtttbso REAL,
    tthai INTEGER,                    -- tính chất hóa đơn theo cổng thuế
    xml_path TEXT,
    raw TEXT,
    UNIQUE(company_mst, direction, nbmst, khmshdon, khhdon, shdon)
);
CREATE TABLE IF NOT EXISTS suppliers (
    mst TEXT PRIMARY KEY,
    ten TEXT,
    status TEXT NOT NULL DEFAULT 'chua_tra',
    ngay_ngung TEXT,                  -- YYYY-MM-DD, nếu có
    nguon TEXT,                       -- 'cqt' | 'tong_hop' | 'nhap_tay'
    can_xac_nhan INTEGER NOT NULL DEFAULT 0,
    checked_at TEXT
);
-- Mỗi lần kiểm tra đối tác là một dòng, giữ lại làm bằng chứng
CREATE TABLE IF NOT EXISTS partner_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mst TEXT NOT NULL,
    ten TEXT,
    status TEXT NOT NULL,
    ngay_ngung TEXT,
    ngay_thanh_lap TEXT,
    dia_chi TEXT,
    nguoi_dai_dien TEXT,
    nganh_nghe TEXT,
    nganh_khop INTEGER,               -- 1 khớp, 0 không khớp, NULL chưa xem
    nguon TEXT,
    ghi_chu TEXT,
    ds_rui_ro TEXT,                   -- danh sách rủi ro đối tác nằm trong, lúc kiểm tra
    ket_luan TEXT NOT NULL,           -- 'nen_ky' | 'can_xem' | 'khong_nen' | 'chua_du'
    ly_do TEXT,
    checked_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_partner_checks_mst ON partner_checks(mst, checked_at);
-- Dòng hàng hóa, dịch vụ của từng hóa đơn (đọc từ XML)
CREATE TABLE IF NOT EXISTS invoice_items (
    invoice_id INTEGER NOT NULL,
    stt INTEGER,
    tinh_chat TEXT,
    ma_hang TEXT,
    ten_hang TEXT,
    dvt TEXT,
    so_luong REAL,
    don_gia REAL,
    tl_ck REAL,
    tien_ck REAL,
    thanh_tien REAL,
    thue_suat TEXT
);
CREATE INDEX IF NOT EXISTS idx_invoice_items ON invoice_items(invoice_id, stt);
-- Phân loại hạch toán anh đã xác nhận cho từng mặt hàng.
-- key_mst: MST người bán (mua vào, vì mã hàng là mã của người bán) hoặc MST DN của anh (bán ra)
CREATE TABLE IF NOT EXISTS item_categories (
    chieu TEXT NOT NULL,
    key_mst TEXT NOT NULL,
    ma_key TEXT NOT NULL,
    phan_loai TEXT NOT NULL,
    tai_khoan TEXT,
    updated_at TEXT,
    PRIMARY KEY (chieu, key_mst, ma_key)
);
-- Danh sách cơ quan thuế công bố: DN rủi ro cao, DN bị công khai nợ thuế
CREATE TABLE IF NOT EXISTS watchlist (
    mst TEXT NOT NULL,
    loai TEXT NOT NULL,               -- 'rui_ro_cao' | 'no_thue'
    ten TEXT,
    nguon TEXT,
    imported_at TEXT,
    PRIMARY KEY (mst, loai)
);
"""


# Hóa đơn gốc mà hóa đơn điều chỉnh / thay thế trỏ tới
GOC_COLS = ("goc_khmshdon", "goc_khhdon", "goc_shdon", "goc_tdlap")


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.data_dir / "thuedn.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._migrate()
        self.fernet = Fernet(self._load_key())

    def _migrate(self) -> None:
        """Thêm cột thông tin hóa đơn gốc (HĐ bị điều chỉnh / bị thay thế) cho dữ liệu cũ."""
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(invoices)")}
        for col in GOC_COLS + ("noi_dung",):
            if col not in cols:
                self.db.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT")
        self.db.commit()

    def _load_key(self) -> bytes:
        key_file = self.data_dir / "secret.key"
        if not key_file.exists():
            key_file.write_bytes(Fernet.generate_key())
        return key_file.read_bytes()

    # ---- doanh nghiệp ----
    def add_company(self, mst: str, name: str, password: str) -> None:
        enc = self.fernet.encrypt(password.encode("utf-8"))
        self.db.execute(
            "INSERT INTO companies(mst, name, enc_password) VALUES(?,?,?) "
            "ON CONFLICT(mst) DO UPDATE SET name=excluded.name, enc_password=excluded.enc_password",
            (mst.strip(), name.strip(), enc),
        )
        self.db.commit()

    def delete_company(self, mst: str) -> None:
        self.db.execute("DELETE FROM companies WHERE mst=?", (mst,))
        self.db.commit()

    def companies(self) -> list[sqlite3.Row]:
        return self.db.execute("SELECT mst, name FROM companies ORDER BY name").fetchall()

    def company_name(self, mst: str) -> str:
        row = self.db.execute("SELECT name FROM companies WHERE mst=?", (mst,)).fetchone()
        return row["name"] if row else mst

    def password(self, mst: str) -> str:
        row = self.db.execute("SELECT enc_password FROM companies WHERE mst=?", (mst,)).fetchone()
        if not row:
            raise KeyError(mst)
        return self.fernet.decrypt(row["enc_password"]).decode("utf-8")

    # ---- hóa đơn ----
    def save_invoice(self, company_mst: str, direction: str, inv: dict) -> None:
        self.db.execute(
            """INSERT INTO invoices(company_mst, direction, nbmst, nbten, nmmst, nmten,
                   khmshdon, khhdon, shdon, tdlap, tgtcthue, tgtthue, tgtttbso, tthai, raw,
                   goc_khmshdon, goc_khhdon, goc_shdon, goc_tdlap)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(company_mst, direction, nbmst, khmshdon, khhdon, shdon)
               DO UPDATE SET tthai=excluded.tthai, raw=excluded.raw,
                   tgtcthue=excluded.tgtcthue, tgtthue=excluded.tgtthue, tgtttbso=excluded.tgtttbso,
                   goc_khmshdon=COALESCE(excluded.goc_khmshdon, goc_khmshdon),
                   goc_khhdon=COALESCE(excluded.goc_khhdon, goc_khhdon),
                   goc_shdon=COALESCE(excluded.goc_shdon, goc_shdon),
                   goc_tdlap=COALESCE(excluded.goc_tdlap, goc_tdlap)""",
            (
                company_mst, direction,
                inv.get("nbmst"), inv.get("nbten"), inv.get("nmmst"), inv.get("nmten"),
                str(inv.get("khmshdon", "")), inv.get("khhdon"), str(inv.get("shdon", "")),
                inv.get("tdlap"), inv.get("tgtcthue"), inv.get("tgtthue"), inv.get("tgtttbso"),
                inv.get("tthai"), json.dumps(inv.get("raw", {}), ensure_ascii=False),
                *(_s(inv.get(c)) for c in GOC_COLS),
            ),
        )
        self.db.commit()

    def set_goc(self, invoice_id: int, goc: dict) -> None:
        """Ghi thông tin hóa đơn gốc lấy từ file XML (chính xác hơn danh sách cổng thuế)."""
        self.db.execute(
            "UPDATE invoices SET goc_khmshdon=?, goc_khhdon=?, goc_shdon=?, goc_tdlap=? WHERE id=?",
            (*(_s(goc.get(c)) for c in GOC_COLS), invoice_id))
        if goc.get("noi_dung"):
            self.db.execute("UPDATE invoices SET noi_dung=? WHERE id=?", (goc["noi_dung"], invoice_id))
        self.db.commit()

    def find_invoice(self, company_mst: str, direction: str, nbmst: str,
                     khmshdon, khhdon, shdon) -> sqlite3.Row | None:
        """Tìm hóa đơn theo người bán + ký hiệu mẫu + ký hiệu + số (không giới hạn ngày)."""
        sql = ("SELECT * FROM invoices WHERE company_mst=? AND direction=? AND nbmst=? "
               "AND khhdon=? AND CAST(shdon AS INTEGER)=CAST(? AS INTEGER)")
        args = [company_mst, direction, nbmst, khhdon, shdon]
        if khmshdon:
            sql += " AND khmshdon=?"
            args.append(str(khmshdon))
        return self.db.execute(sql, args).fetchone()

    def find_adjusting(self, goc: sqlite3.Row) -> list[sqlite3.Row]:
        """Các hóa đơn điều chỉnh / thay thế trỏ tới hóa đơn gốc này."""
        return self.db.execute(
            """SELECT * FROM invoices WHERE company_mst=? AND direction=? AND nbmst=?
                   AND goc_khhdon=? AND CAST(goc_shdon AS INTEGER)=CAST(? AS INTEGER)
                   AND (goc_khmshdon IS NULL OR goc_khmshdon='' OR goc_khmshdon=?)
               ORDER BY tdlap, id""",
            (goc["company_mst"], goc["direction"], goc["nbmst"], goc["khhdon"], goc["shdon"],
             goc["khmshdon"])).fetchall()

    def set_items(self, invoice_id: int, items: list[dict]) -> None:
        self.db.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        self.db.executemany(
            """INSERT INTO invoice_items(invoice_id, stt, tinh_chat, ma_hang, ten_hang, dvt, so_luong,
                   don_gia, tl_ck, tien_ck, thanh_tien, thue_suat)
               VALUES(:invoice_id,:stt,:tinh_chat,:ma_hang,:ten_hang,:dvt,:so_luong,:don_gia,:tl_ck,
                   :tien_ck,:thanh_tien,:thue_suat)""",
            [{**it, "invoice_id": invoice_id} for it in items])
        self.db.commit()

    def items_by_invoice(self, invoice_ids: list[int]) -> dict[int, list[sqlite3.Row]]:
        out: dict[int, list[sqlite3.Row]] = {}
        for i in range(0, len(invoice_ids), 500):
            part = invoice_ids[i:i + 500]
            for r in self.db.execute(
                    f"SELECT * FROM invoice_items WHERE invoice_id IN ({','.join('?' * len(part))}) "
                    "ORDER BY invoice_id, stt", part):
                out.setdefault(r["invoice_id"], []).append(r)
        return out

    def categories(self) -> dict[tuple[str, str, str], sqlite3.Row]:
        return {(r["chieu"], r["key_mst"], r["ma_key"]): r
                for r in self.db.execute("SELECT * FROM item_categories")}

    def set_category(self, chieu: str, key_mst: str, ma_key: str, phan_loai: str,
                     tai_khoan: str, at: str) -> None:
        self.db.execute(
            """INSERT INTO item_categories(chieu, key_mst, ma_key, phan_loai, tai_khoan, updated_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(chieu, key_mst, ma_key) DO UPDATE SET
                   phan_loai=excluded.phan_loai, tai_khoan=excluded.tai_khoan, updated_at=excluded.updated_at""",
            (chieu, key_mst, ma_key, phan_loai, tai_khoan, at))
        self.db.commit()

    def item_lines(self, msts: list[str] | None = None, date_from: str | None = None,
                   date_to: str | None = None) -> list[sqlite3.Row]:
        """Dòng hàng hóa kèm thông tin hóa đơn, bỏ HĐ bị thay thế (4) và bị hủy (6) để không tính trùng."""
        sql = """SELECT it.*, i.company_mst, i.direction, i.nbmst, i.nbten, i.tdlap, i.tthai, i.id AS hd_id
                 FROM invoice_items it JOIN invoices i ON i.id = it.invoice_id
                 WHERE COALESCE(i.tthai, 1) NOT IN (4, 6)"""
        args: list = []
        if msts:
            sql += f" AND i.company_mst IN ({','.join('?' * len(msts))})"
            args += msts
        if date_from:
            sql += " AND i.tdlap >= ?"
            args.append(date_from)
        if date_to:
            sql += " AND i.tdlap <= ?"
            args.append(date_to)
        return self.db.execute(sql + " ORDER BY i.company_mst, i.direction, i.tdlap, it.stt", args).fetchall()

    def set_xml_path(self, invoice_id: int, path: str) -> None:
        self.db.execute("UPDATE invoices SET xml_path=? WHERE id=?", (path, invoice_id))
        self.db.commit()

    def invoices(self, msts: list[str] | None = None, date_from: str | None = None,
                 date_to: str | None = None, direction: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM invoices WHERE 1=1"
        args: list = []
        if msts:
            sql += f" AND company_mst IN ({','.join('?' * len(msts))})"
            args += msts
        if date_from:
            sql += " AND tdlap >= ?"
            args.append(date_from)
        if date_to:
            sql += " AND tdlap <= ?"
            args.append(date_to)
        if direction:
            sql += " AND direction = ?"
            args.append(direction)
        sql += " ORDER BY company_mst, direction, tdlap"
        return self.db.execute(sql, args).fetchall()

    # ---- nhà cung cấp ----
    def ensure_suppliers_from_invoices(self) -> None:
        self.db.execute(
            """INSERT OR IGNORE INTO suppliers(mst, ten)
               SELECT nbmst, MAX(nbten) FROM invoices
               WHERE direction='vao' AND nbmst IS NOT NULL AND nbmst != ''
               GROUP BY nbmst"""
        )
        self.db.commit()

    def suppliers(self) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT s.*, COUNT(i.id) AS so_hd, MAX(i.tdlap) AS hd_cuoi
               FROM suppliers s LEFT JOIN invoices i ON i.nbmst = s.mst AND i.direction='vao'
               GROUP BY s.mst ORDER BY s.ten"""
        ).fetchall()

    def supplier_map(self) -> dict[str, sqlite3.Row]:
        return {r["mst"]: r for r in self.db.execute("SELECT * FROM suppliers").fetchall()}

    def update_supplier(self, mst: str, status: str, ngay_ngung: str | None,
                        nguon: str, checked_at: str) -> None:
        self.db.execute(
            """UPDATE suppliers SET status=?, ngay_ngung=?, nguon=?, can_xac_nhan=?, checked_at=?
               WHERE mst=?""",
            (status, ngay_ngung or None, nguon, 1 if nguon == "tong_hop" else 0, checked_at, mst),
        )
        self.db.commit()

    # ---- kiểm tra đối tác ----
    def add_partner_check(self, c: dict) -> int:
        cur = self.db.execute(
            """INSERT INTO partner_checks(mst, ten, status, ngay_ngung, ngay_thanh_lap, dia_chi,
                   nguoi_dai_dien, nganh_nghe, nganh_khop, nguon, ghi_chu, ds_rui_ro, ket_luan, ly_do, checked_at)
               VALUES(:mst,:ten,:status,:ngay_ngung,:ngay_thanh_lap,:dia_chi,:nguoi_dai_dien,:nganh_nghe,
                   :nganh_khop,:nguon,:ghi_chu,:ds_rui_ro,:ket_luan,:ly_do,:checked_at)""", c)
        # đồng bộ sang bảng nhà cung cấp để cảnh báo hóa đơn dùng chung kết quả
        self.db.execute("INSERT OR IGNORE INTO suppliers(mst, ten) VALUES(?, ?)", (c["mst"], c["ten"]))
        self.db.execute(
            """UPDATE suppliers SET ten=COALESCE(NULLIF(?, ''), ten), status=?, ngay_ngung=?, nguon=?,
                   can_xac_nhan=?, checked_at=? WHERE mst=?""",
            (c["ten"], c["status"], c["ngay_ngung"], c["nguon"], 1 if c["nguon"] == "tong_hop" else 0,
             c["checked_at"], c["mst"]))
        self.db.commit()
        return cur.lastrowid

    def partner_checks(self, mst: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
        if mst:
            return self.db.execute(
                "SELECT * FROM partner_checks WHERE mst=? ORDER BY checked_at DESC, id DESC", (mst,)).fetchall()
        return self.db.execute(
            """SELECT p.* FROM partner_checks p
               JOIN (SELECT mst, MAX(id) AS id FROM partner_checks GROUP BY mst) last ON last.id = p.id
               ORDER BY p.checked_at DESC LIMIT ?""", (limit,)).fetchall()

    def latest_partner_check(self, mst: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM partner_checks WHERE mst=? ORDER BY checked_at DESC, id DESC LIMIT 1", (mst,)).fetchone()

    def import_watchlist(self, loai: str, rows: list[tuple[str, str]], nguon: str, at: str) -> int:
        self.db.executemany(
            """INSERT INTO watchlist(mst, loai, ten, nguon, imported_at) VALUES(?,?,?,?,?)
               ON CONFLICT(mst, loai) DO UPDATE SET ten=excluded.ten, nguon=excluded.nguon,
                   imported_at=excluded.imported_at""",
            [(mst, loai, ten, nguon, at) for mst, ten in rows])
        self.db.commit()
        return len(rows)

    def watchlist_hits(self, mst: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM watchlist WHERE mst=?", (mst,)).fetchall()

    def watchlist_summary(self) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT loai, COUNT(*) AS so, MAX(imported_at) AS cap_nhat FROM watchlist GROUP BY loai").fetchall()

    def suppliers_in_watchlist(self) -> list[sqlite3.Row]:
        """Nhà cung cấp đã có hóa đơn mà nằm trong danh sách rủi ro."""
        return self.db.execute(
            """SELECT DISTINCT s.mst, s.ten, w.loai FROM suppliers s
               JOIN watchlist w ON w.mst = s.mst
               JOIN invoices i ON i.nbmst = s.mst AND i.direction = 'vao'""").fetchall()

    def due_rechecks(self, older_than: str) -> list[sqlite3.Row]:
        """Nhà cung cấp có hóa đơn mua vào mà chưa tra, hoặc tra trước ngày older_than."""
        return self.db.execute(
            """SELECT s.mst, s.ten, s.status, s.checked_at, MAX(i.tdlap) AS hd_cuoi
               FROM suppliers s JOIN invoices i ON i.nbmst = s.mst AND i.direction = 'vao'
               WHERE s.checked_at IS NULL OR s.checked_at < ?
               GROUP BY s.mst ORDER BY s.checked_at IS NOT NULL, s.checked_at""", (older_than,)).fetchall()

    def purchase_summary(self, mst: str) -> sqlite3.Row:
        return self.db.execute(
            """SELECT COUNT(*) AS so_hd, COALESCE(SUM(tgtttbso), 0) AS tong,
                   SUM(CASE WHEN tthai NOT IN (1) THEN 1 ELSE 0 END) AS so_dc,
                   MIN(tdlap) AS dau, MAX(tdlap) AS cuoi
               FROM invoices WHERE direction='vao' AND nbmst=?""", (mst,)).fetchone()


def _s(v) -> str | None:
    return None if v in (None, "") else str(v)
