"""SQLite storage for accounting-intelligence items.

Provides de-duplicated upsert (stable IntelItem.id as PK), historical tracking
(first_seen vs. retrieved_at), and the queries the briefing/research layers need.
SQLite is part of the standard library — no extra dependency, file-backed
persistence, fully testable with an in-memory database.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from typing import Optional

from ..schemas import IntelItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intel_item (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  doc_type TEXT,
  title TEXT NOT NULL,
  url TEXT,
  summary TEXT,
  published TEXT,
  effective_date TEXT,
  asc_codes TEXT,
  asu_number TEXT,
  guid TEXT,
  first_seen TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  seen INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_intel_source ON intel_item(source);
CREATE INDEX IF NOT EXISTS idx_intel_published ON intel_item(published);
CREATE INDEX IF NOT EXISTS idx_intel_effective ON intel_item(effective_date);
"""


def _default_path() -> str:
    env = os.environ.get("HELIOS_INTEL_DB")
    if env:
        return env
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "intel.db")


class IntelStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or _default_path()
        # check_same_thread=False so the FastAPI worker threads can share the
        # connection; a lock serializes writes (single-user local sidecar).
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert_many(self, items: list[IntelItem]) -> dict:
        """Insert new items, refresh existing ones. Returns counts + the new ids."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            existing = {row["id"] for row in self.conn.execute("SELECT id FROM intel_item")}
            inserted, updated = self._upsert_locked(items, existing, now)
        return {"inserted": len(inserted), "updated": updated, "new_ids": inserted}

    def _upsert_locked(self, items, existing, now):
        inserted, updated = [], 0
        for it in items:
            if it.id in existing:
                self.conn.execute(
                    "UPDATE intel_item SET retrieved_at=?, effective_date=COALESCE(?, effective_date), "
                    "summary=CASE WHEN length(?)>length(summary) THEN ? ELSE summary END WHERE id=?",
                    (now, it.effective_date, it.summary, it.summary, it.id),
                )
                updated += 1
            else:
                self.conn.execute(
                    "INSERT INTO intel_item (id, source, doc_type, title, url, summary, published, "
                    "effective_date, asc_codes, asu_number, guid, first_seen, retrieved_at, seen) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (it.id, it.source, it.doc_type, it.title, it.url, it.summary, it.published,
                     it.effective_date, json.dumps(it.asc_codes), it.asu_number, it.guid,
                     it.retrieved_at or now, now),
                )
                inserted.append(it.id)
        self.conn.commit()
        return inserted, updated

    def _row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["asc_codes"] = json.loads(d.get("asc_codes") or "[]")
        d["seen"] = bool(d.get("seen"))
        return d

    def query(self, source: Optional[str] = None, doc_type: Optional[str] = None,
              since: Optional[str] = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM intel_item WHERE 1=1"
        args: list = []
        if source:
            sql += " AND source=?"; args.append(source)
        if doc_type:
            sql += " AND doc_type=?"; args.append(doc_type)
        if since:
            sql += " AND COALESCE(published, first_seen) >= ?"; args.append(since)
        sql += " ORDER BY COALESCE(published, first_seen) DESC, first_seen DESC LIMIT ?"
        args.append(limit)
        return [self._row(r) for r in self.conn.execute(sql, args)]

    def new_since(self, iso_ts: str, limit: int = 100) -> list[dict]:
        """Items first seen on/after a timestamp — drives 'new developments'."""
        rows = self.conn.execute(
            "SELECT * FROM intel_item WHERE first_seen >= ? ORDER BY first_seen DESC LIMIT ?",
            (iso_ts, limit),
        )
        return [self._row(r) for r in rows]

    def upcoming_effective(self, today: Optional[str] = None, limit: int = 50) -> list[dict]:
        today = today or date.today().isoformat()
        rows = self.conn.execute(
            "SELECT * FROM intel_item WHERE effective_date IS NOT NULL AND effective_date >= ? "
            "ORDER BY effective_date ASC LIMIT ?",
            (today, limit),
        )
        return [self._row(r) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM intel_item").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
