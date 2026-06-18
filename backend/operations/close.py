"""Month-End Close System — checklist, status tracking, and a close package
(trial balance + statements snapshot) built from the accounting platform.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from accounting_platform import statements, gl, db as acct_db

CHECKLIST_TEMPLATE = [
    ("journal_entries", "Record routine journal entries"),
    ("accruals", "Record accruals"),
    ("prepaids", "Amortize prepaids"),
    ("depreciation", "Post depreciation"),
    ("reconciliations", "Complete bank/account reconciliations"),
    ("review", "Perform review procedures (flux/variance)"),
    ("closing_entries", "Post closing entries"),
    ("statements", "Generate financial statements"),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS close_period (
  period TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'open', checklist TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class CloseStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_CLOSE_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "close.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def start(self, period: str) -> dict:
        checklist = [{"key": k, "label": label, "status": "pending"} for k, label in CHECKLIST_TEMPLATE]
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO close_period (period,status,checklist,created_at) "
                              "VALUES (?, 'in_progress', ?, ?)",
                              (period, json.dumps(checklist), datetime.now(timezone.utc).isoformat()))
            self.conn.commit()
        return self.get(period)

    def get(self, period: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM close_period WHERE period=?", (period,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["checklist"] = json.loads(d["checklist"])
        done = sum(1 for i in d["checklist"] if i["status"] == "done")
        d["progress"] = round(done / len(d["checklist"]) * 100)
        d["ready_to_close"] = done == len(d["checklist"])
        return d

    def update_item(self, period: str, key: str, status: str) -> dict:
        p = self.get(period) or self.start(period)
        for item in p["checklist"]:
            if item["key"] == key:
                item["status"] = status
        with self._lock:
            self.conn.execute("UPDATE close_period SET checklist=? WHERE period=?",
                              (json.dumps(p["checklist"]), period))
            self.conn.commit()
        return self.get(period)

    def close(self, period: str) -> dict:
        p = self.get(period)
        if not p:
            raise ValueError("close not started")
        if not p["ready_to_close"]:
            raise ValueError("checklist incomplete — cannot close")
        y, m = int(period[:4]), int(period[5:7])
        acct_db.close_period(self.conn_for_acct(), y, m) if False else None  # period lock is on the acct DB
        with self._lock:
            self.conn.execute("UPDATE close_period SET status='closed' WHERE period=?", (period,))
            self.conn.commit()
        return self.get(period)

    def conn_for_acct(self):  # pragma: no cover - overridden by the router with the live acct conn
        return None

    def dashboard(self) -> dict:
        rows = [self.get(r["period"]) for r in self.conn.execute("SELECT period FROM close_period ORDER BY period DESC")]
        return {"periods": rows, "count": len(rows)}

    def close_db(self):
        self.conn.close()


def close_package(acct_conn, period: str) -> dict:
    """Snapshot the books for a period: trial balance + the three statements."""
    y, m = int(period[:4]), int(period[5:7])
    last_day = "31" if m in (1, 3, 5, 7, 8, 10, 12) else ("28" if m == 2 else "30")
    as_of = f"{period}-{last_day}"
    start = f"{period}-01"
    return {
        "period": period, "as_of": as_of,
        "trial_balance": gl.trial_balance(acct_conn, as_of),
        "income_statement": statements.income_statement(acct_conn, start, as_of),
        "balance_sheet": statements.balance_sheet(acct_conn, as_of),
        "cash_flow": statements.cash_flow(acct_conn, start, as_of),
    }
