"""Workpaper Generator — builds lead schedules, trial-balance, depreciation,
reconciliation, and tax workpapers from the accounting platform, with
cross-reference indexing and version tracking.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Optional

from accounting_platform import bank_rec, coa, fixed_assets, gl, statements

# Standard workpaper index references by account type (lead schedules).
LEAD_INDEX = {"asset": "A", "liability": "B", "equity": "C", "revenue": "R", "expense": "E"}

_WP_SCHEMA = """
CREATE TABLE IF NOT EXISTS workpaper (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, index_ref TEXT, title TEXT,
  content TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, supersedes INTEGER, created_at TEXT NOT NULL
);
"""


def trial_balance_workpaper(conn, as_of: Optional[str] = None) -> dict:
    tb = gl.trial_balance(conn, as_of)
    for i, row in enumerate(tb["rows"], 1):
        row["ref"] = f"TB-{i}"
    return {"kind": "trial_balance", "index_ref": "TB", "title": f"Trial Balance @ {as_of or 'current'}",
            "as_of": as_of, "rows": tb["rows"], "total_debit": tb["total_debit"],
            "total_credit": tb["total_credit"], "tie_out": tb["balanced"]}


def lead_schedule(conn, account_type: str, as_of: Optional[str] = None) -> dict:
    idx = LEAD_INDEX.get(account_type, "X")
    rows, subtotal = [], 0.0
    for acct in coa.list_accounts(conn):
        if acct["type"] != account_type:
            continue
        bal = gl.account_balance(conn, acct["id"], as_of)["balance"]
        if abs(bal) < 0.005:
            continue
        subtotal += bal
        rows.append({"ref": f"{idx}-{acct['number']}", "account": acct["number"],
                     "name": acct["name"], "balance": round(bal, 2)})
    return {"kind": "lead_schedule", "index_ref": idx, "title": f"{account_type.title()} Lead Schedule",
            "account_type": account_type, "rows": rows, "subtotal": round(subtotal, 2)}


def depreciation_workpaper(conn) -> dict:
    rows = []
    for a in fixed_assets.list_assets(conn):
        sched = fixed_assets.depreciation_schedule(conn, a["id"])
        rows.append({"ref": f"PPE-{a['id']}", "asset": a["name"], "cost": a["cost"],
                     "salvage": a["salvage"], "method": a["method"],
                     "annual_or_total": sched.get("total_depreciation") or sched.get("rate_per_unit")})
    return {"kind": "depreciation", "index_ref": "PPE", "title": "Depreciation Workpaper", "rows": rows}


def reconciliation_workpaper(conn, account_id: int, as_of: Optional[str] = None) -> dict:
    rep = bank_rec.reconciliation_report(conn, account_id, as_of)
    return {"kind": "reconciliation", "index_ref": "REC", "title": f"Bank Reconciliation — acct {rep['account']}",
            **rep}


def tax_workpaper(conn, year: int, m1_adjustments: Optional[list[dict]] = None) -> dict:
    """Book-to-tax (Schedule M-1 style) workpaper: book net income + adjustments."""
    inc = statements.income_statement(conn, f"{year}-01-01", f"{year}-12-31")
    book = inc["net_income"]
    adjustments = m1_adjustments or []
    taxable = round(book + sum(a.get("amount", 0) for a in adjustments), 2)
    return {"kind": "tax", "index_ref": "TAX", "title": f"Book-to-Tax (M-1) {year}",
            "book_net_income": book, "adjustments": adjustments, "taxable_income": taxable}


class WorkpaperStore:
    """Optional persistence with version tracking and cross-references."""

    def __init__(self, conn):
        self.conn = conn
        self._lock = threading.Lock()
        self.conn.executescript(_WP_SCHEMA)
        self.conn.commit()

    def save(self, wp: dict, supersedes: Optional[int] = None) -> dict:
        version = 1
        if supersedes:
            prev = self.conn.execute("SELECT version FROM workpaper WHERE id=?", (supersedes,)).fetchone()
            version = (prev["version"] + 1) if prev else 1
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO workpaper (kind,index_ref,title,content,version,supersedes,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (wp.get("kind"), wp.get("index_ref"), wp.get("title"), json.dumps(wp),
                 version, supersedes, datetime.now(timezone.utc).isoformat()))
            self.conn.commit()
        return {"id": cur.lastrowid, "version": version, "index_ref": wp.get("index_ref")}

    def list(self) -> list[dict]:
        return [{"id": r["id"], "kind": r["kind"], "index_ref": r["index_ref"], "title": r["title"],
                 "version": r["version"]} for r in self.conn.execute("SELECT * FROM workpaper ORDER BY id DESC")]
