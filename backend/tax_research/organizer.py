"""Client Tax Organizer — profiles, document requests, missing-doc tracking,
tax-season checklist, deadlines, and status. SQLite-backed."""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_client (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, entity_type TEXT NOT NULL DEFAULT 'individual',
  tax_year INTEGER, status TEXT NOT NULL DEFAULT 'not_started', deadline TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS doc_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', received_at TEXT
);
"""

# Standard requested documents by entity type.
STANDARD_DOCS = {
    "individual": ["W-2 (all employers)", "1099-INT / 1099-DIV", "1099-NEC / 1099-MISC", "1098 Mortgage Interest",
                   "Schedule K-1s", "Charitable contribution receipts", "Property tax statements",
                   "1095-A/B/C Health coverage", "Prior-year return"],
    "business": ["Year-end P&L", "Year-end Balance Sheet", "General ledger", "Payroll reports (941/W-3)",
                 "Fixed-asset additions/disposals", "Bank statements (Dec)", "Loan statements",
                 "1099s issued", "Prior-year return"],
}
CHECKLIST = ["Send engagement letter", "Deliver organizer & document request", "Collect source documents",
             "Reconcile to prior-year carryforwards", "Prepare return / workpapers", "Internal review",
             "Client review & e-file authorization", "E-file & confirm acceptance", "Deliver copies & invoice"]


class TaxOrganizer:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_TAXORG_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "tax_organizer.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add_client(self, name: str, *, entity_type: str = "individual", tax_year: Optional[int] = None,
                   deadline: Optional[str] = None, auto_request: bool = True) -> dict:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO tax_client (name,entity_type,tax_year,status,deadline,created_at) "
                "VALUES (?,?,?, 'not_started', ?, ?)",
                (name, entity_type, tax_year, deadline, datetime.now(timezone.utc).isoformat()))
            cid = cur.lastrowid
            if auto_request:
                for doc in STANDARD_DOCS.get(entity_type, STANDARD_DOCS["individual"]):
                    self.conn.execute("INSERT INTO doc_request (client_id,name,status) VALUES (?,?, 'pending')", (cid, doc))
            self.conn.commit()
        return self.get_client(cid)

    def get_client(self, cid: int) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM tax_client WHERE id=?", (cid,)).fetchone()
        if not r:
            return None
        c = dict(r)
        c["documents"] = [dict(x) for x in self.conn.execute("SELECT * FROM doc_request WHERE client_id=?", (cid,))]
        return c

    def mark_received(self, request_id: int) -> dict:
        with self._lock:
            self.conn.execute("UPDATE doc_request SET status='received', received_at=? WHERE id=?",
                              (datetime.now(timezone.utc).isoformat(), request_id))
            self.conn.commit()
        r = self.conn.execute("SELECT * FROM doc_request WHERE id=?", (request_id,)).fetchone()
        return dict(r)

    def set_status(self, cid: int, status: str) -> dict:
        with self._lock:
            self.conn.execute("UPDATE tax_client SET status=? WHERE id=?", (status, cid))
            self.conn.commit()
        return self.get_client(cid)

    def missing_documents(self, cid: int) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM doc_request WHERE client_id=? AND status='pending'", (cid,))]

    def checklist(self) -> list[str]:
        return CHECKLIST

    def dashboard(self) -> dict:
        clients = []
        for r in self.conn.execute("SELECT * FROM tax_client ORDER BY COALESCE(deadline,'9999')"):
            c = dict(r)
            missing = self.conn.execute("SELECT COUNT(*) n FROM doc_request WHERE client_id=? AND status='pending'",
                                        (c["id"],)).fetchone()["n"]
            total = self.conn.execute("SELECT COUNT(*) n FROM doc_request WHERE client_id=?", (c["id"],)).fetchone()["n"]
            clients.append({**c, "missing_documents": missing, "documents_total": total})
        return {"clients": clients, "count": len(clients),
                "awaiting_docs": sum(1 for c in clients if c["missing_documents"] > 0)}

    def close(self):
        self.conn.close()
