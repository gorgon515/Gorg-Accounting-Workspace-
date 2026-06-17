"""Shared SQLite layer for the accounting platform: schema, connection, audit log,
and period controls. One database holds the entire double-entry system so the GL,
AP/AR, fixed assets, and statements all tie out against the same posted lines.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

SCHEMA = """
-- Chart of accounts
CREATE TABLE IF NOT EXISTS account (
  id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('asset','liability','equity','revenue','expense')),
  subtype TEXT, parent_id INTEGER REFERENCES account(id), active INTEGER NOT NULL DEFAULT 1,
  cash INTEGER NOT NULL DEFAULT 0, cashflow TEXT, created_at TEXT NOT NULL
);
-- Accounting periods (posting controls)
CREATE TABLE IF NOT EXISTS period (
  year INTEGER NOT NULL, month INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  PRIMARY KEY (year, month)
);
-- General ledger: balanced journal entries
CREATE TABLE IF NOT EXISTS journal_entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, memo TEXT, source TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','posted','void')),
  entry_type TEXT NOT NULL DEFAULT 'standard', reversal_of INTEGER REFERENCES journal_entry(id),
  recurring_id INTEGER, created_by TEXT, created_at TEXT NOT NULL, posted_at TEXT
);
CREATE TABLE IF NOT EXISTS journal_line (
  id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL REFERENCES journal_entry(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES account(id), debit REAL NOT NULL DEFAULT 0,
  credit REAL NOT NULL DEFAULT 0, memo TEXT
);
CREATE INDEX IF NOT EXISTS idx_line_entry ON journal_line(entry_id);
CREATE INDEX IF NOT EXISTS idx_line_account ON journal_line(account_id);
-- Recurring entry templates
CREATE TABLE IF NOT EXISTS recurring_template (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, frequency TEXT NOT NULL,
  memo TEXT, lines TEXT NOT NULL, last_run TEXT, created_at TEXT NOT NULL
);
-- Accounts payable
CREATE TABLE IF NOT EXISTS vendor (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT, terms_days INTEGER DEFAULT 30,
  is_1099 INTEGER NOT NULL DEFAULT 0, tin TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bill (
  id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id INTEGER REFERENCES vendor(id), number TEXT,
  bill_date TEXT NOT NULL, due_date TEXT, amount REAL NOT NULL, expense_account_id INTEGER,
  ap_account_id INTEGER, status TEXT NOT NULL DEFAULT 'open', paid REAL NOT NULL DEFAULT 0,
  je_id INTEGER, created_at TEXT NOT NULL
);
-- Accounts receivable
CREATE TABLE IF NOT EXISTS customer (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT, terms_days INTEGER DEFAULT 30,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ar_invoice (
  id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER REFERENCES customer(id), number TEXT,
  invoice_date TEXT NOT NULL, due_date TEXT, amount REAL NOT NULL, revenue_account_id INTEGER,
  ar_account_id INTEGER, status TEXT NOT NULL DEFAULT 'open', paid REAL NOT NULL DEFAULT 0,
  je_id INTEGER, created_at TEXT NOT NULL
);
-- Fixed assets
CREATE TABLE IF NOT EXISTS fixed_asset (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, acquired_on TEXT NOT NULL,
  cost REAL NOT NULL, salvage REAL NOT NULL DEFAULT 0, life_months INTEGER NOT NULL,
  method TEXT NOT NULL DEFAULT 'straight_line', units_total REAL, asset_account_id INTEGER,
  expense_account_id INTEGER, accumdep_account_id INTEGER, created_at TEXT NOT NULL
);
-- Client / engagement management
CREATE TABLE IF NOT EXISTS client (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, kind TEXT, email TEXT, notes TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS engagement (
  id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER REFERENCES client(id), name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', due_date TEXT, deliverable TEXT, notes TEXT, created_at TEXT NOT NULL
);
-- Document center
CREATE TABLE IF NOT EXISTS document (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, doc_type TEXT, path TEXT,
  tags TEXT NOT NULL DEFAULT '[]', client_id INTEGER, link_entity TEXT, link_id INTEGER,
  version INTEGER NOT NULL DEFAULT 1, supersedes INTEGER, created_at TEXT NOT NULL
);
-- Bank reconciliation
CREATE TABLE IF NOT EXISTS bank_txn (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, date TEXT NOT NULL, amount REAL NOT NULL,
  description TEXT, fitid TEXT, matched_line_id INTEGER, status TEXT NOT NULL DEFAULT 'unmatched',
  imported_at TEXT NOT NULL
);
-- Immutable audit log
CREATE TABLE IF NOT EXISTS audit_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, user TEXT, entity TEXT NOT NULL,
  entity_id TEXT, action TEXT NOT NULL, old_value TEXT, new_value TEXT, source TEXT, reason TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    path = path or os.environ.get("HELIOS_ACCT_DB") or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".data", "accounting.db")
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def audit(conn: sqlite3.Connection, *, entity: str, action: str, entity_id=None,
          old=None, new=None, user: str = "system", source: str = "app", reason: str = "") -> None:
    """Append an immutable audit record. Never updated or deleted."""
    conn.execute(
        "INSERT INTO audit_event (ts,user,entity,entity_id,action,old_value,new_value,source,reason) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (now_iso(), user, entity, str(entity_id) if entity_id is not None else None, action,
         json.dumps(old) if old is not None else None, json.dumps(new) if new is not None else None,
         source, reason))


def audit_log(conn: sqlite3.Connection, limit: int = 100, entity: Optional[str] = None) -> list[dict]:
    sql, args = "SELECT * FROM audit_event", []
    if entity:
        sql += " WHERE entity=?"; args.append(entity)
    sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    out = []
    for r in conn.execute(sql, args):
        d = dict(r)
        for k in ("old_value", "new_value"):
            d[k] = json.loads(d[k]) if d[k] else None
        out.append(d)
    return out


# ---- period controls ----
def ensure_period(conn: sqlite3.Connection, year: int, month: int) -> None:
    conn.execute("INSERT OR IGNORE INTO period (year,month,status) VALUES (?,?,'open')", (year, month))


def period_status(conn: sqlite3.Connection, year: int, month: int) -> str:
    r = conn.execute("SELECT status FROM period WHERE year=? AND month=?", (year, month)).fetchone()
    return r["status"] if r else "open"  # unseen periods default open


def close_period(conn: sqlite3.Connection, year: int, month: int, user: str = "system") -> dict:
    ensure_period(conn, year, month)
    conn.execute("UPDATE period SET status='closed' WHERE year=? AND month=?", (year, month))
    audit(conn, entity="period", entity_id=f"{year}-{month:02d}", action="close", user=user)
    conn.commit()
    return {"year": year, "month": month, "status": "closed"}


def reopen_period(conn: sqlite3.Connection, year: int, month: int, user: str = "system") -> dict:
    conn.execute("UPDATE period SET status='open' WHERE year=? AND month=?", (year, month))
    audit(conn, entity="period", entity_id=f"{year}-{month:02d}", action="reopen", user=user)
    conn.commit()
    return {"year": year, "month": month, "status": "open"}


_locks: dict[int, threading.Lock] = {}


def lock_for(conn: sqlite3.Connection) -> threading.Lock:
    return _locks.setdefault(id(conn), threading.Lock())
