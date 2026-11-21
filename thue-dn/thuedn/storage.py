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
"""


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.data_dir / "thuedn.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.fernet = Fernet(self._load_key())

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
                   khmshdon, khhdon, shdon, tdlap, tgtcthue, tgtthue, tgtttbso, tthai, raw)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(company_mst, direction, nbmst, khmshdon, khhdon, shdon)
               DO UPDATE SET tthai=excluded.tthai, raw=excluded.raw,
                   tgtcthue=excluded.tgtcthue, tgtthue=excluded.tgtthue, tgtttbso=excluded.tgtttbso""",
            (
                company_mst, direction,
                inv.get("nbmst"), inv.get("nbten"), inv.get("nmmst"), inv.get("nmten"),
                str(inv.get("khmshdon", "")), inv.get("khhdon"), str(inv.get("shdon", "")),
                inv.get("tdlap"), inv.get("tgtcthue"), inv.get("tgtthue"), inv.get("tgtttbso"),
                inv.get("tthai"), json.dumps(inv.get("raw", {}), ensure_ascii=False),
            ),
        )
        self.db.commit()

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
