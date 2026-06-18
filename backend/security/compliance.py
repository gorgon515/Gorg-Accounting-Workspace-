"""Immutable compliance log — append-only, hash-chained for tamper evidence.

Each event's hash includes the previous event's hash, so altering any past record
breaks the chain. verify() recomputes the chain and reports the first break.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from . import crypto

CATEGORIES = ("login", "approval", "execution", "accounting", "document_access",
              "memory_access", "vault_access", "sync", "backup", "admin")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compliance_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, category TEXT NOT NULL,
  actor TEXT, action TEXT NOT NULL, detail TEXT, prev_hash TEXT, hash TEXT NOT NULL);
"""
_GENESIS = "0" * 64


class ComplianceLog:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_COMPLIANCE_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "compliance.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _last_hash(self) -> str:
        r = self.conn.execute("SELECT hash FROM compliance_event ORDER BY id DESC LIMIT 1").fetchone()
        return r["hash"] if r else _GENESIS

    def record(self, category: str, action: str, *, actor: str = "system", detail: Optional[dict] = None) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        detail_json = json.dumps(detail or {}, sort_keys=True)
        with self._lock:
            prev = self._last_hash()
            payload = f"{prev}|{ts}|{category}|{actor}|{action}|{detail_json}"
            h = crypto.sha256(payload.encode("utf-8"))
            self.conn.execute(
                "INSERT INTO compliance_event (ts,category,actor,action,detail,prev_hash,hash) "
                "VALUES (?,?,?,?,?,?,?)", (ts, category, actor, action, detail_json, prev, h))
            self.conn.commit()
        return {"ts": ts, "category": category, "action": action, "hash": h}

    def verify(self) -> dict:
        """Recompute the chain; report integrity and the first broken id (if any)."""
        prev = _GENESIS
        checked = 0
        for r in self.conn.execute("SELECT * FROM compliance_event ORDER BY id"):
            payload = f"{prev}|{r['ts']}|{r['category']}|{r['actor']}|{r['action']}|{r['detail']}"
            expected = crypto.sha256(payload.encode("utf-8"))
            if r["prev_hash"] != prev or r["hash"] != expected:
                return {"valid": False, "broken_at": r["id"], "events_checked": checked}
            prev = r["hash"]
            checked += 1
        return {"valid": True, "events_checked": checked}

    def query(self, category: Optional[str] = None, limit: int = 100) -> list[dict]:
        sql, args = "SELECT id,ts,category,actor,action,detail FROM compliance_event", []
        if category:
            sql += " WHERE category=?"; args.append(category)
        sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
        out = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            d["detail"] = json.loads(d["detail"]) if d["detail"] else {}
            out.append(d)
        return out

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT category, COUNT(*) n FROM compliance_event GROUP BY category")
        return {"total": self.conn.execute("SELECT COUNT(*) n FROM compliance_event").fetchone()["n"],
                "by_category": {r["category"]: r["n"] for r in rows}, "chain": self.verify()}

    def close(self):
        self.conn.close()
