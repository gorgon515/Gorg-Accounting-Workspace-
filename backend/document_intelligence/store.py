"""Persistence + indexing for processed documents, with links to clients,
projects, accounting records, research, tasks, and goals."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS extraction (
  id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, doc_type TEXT, confidence REAL,
  fields TEXT NOT NULL DEFAULT '{}', summary TEXT, text TEXT, text_length INTEGER,
  client_id INTEGER, link_entity TEXT, link_id INTEGER, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_extraction_type ON extraction(doc_type);
"""


class DocStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_DOCINTEL_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "docintel.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def save(self, result: dict, *, client_id: Optional[int] = None,
             link_entity: Optional[str] = None, link_id: Optional[int] = None) -> dict:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO extraction (filename,doc_type,confidence,fields,summary,text,text_length,"
                "client_id,link_entity,link_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (result.get("filename"), result.get("doc_type"), result.get("classification_confidence"),
                 json.dumps(result.get("fields", {})), result.get("summary"), result.get("text_preview"),
                 result.get("text_length"), client_id, link_entity, link_id,
                 datetime.now(timezone.utc).isoformat()))
            self.conn.commit()
        return self.get(cur.lastrowid)

    def _row(self, r) -> dict:
        d = dict(r)
        d["fields"] = json.loads(d.get("fields") or "{}")
        return d

    def get(self, doc_id: int) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM extraction WHERE id=?", (doc_id,)).fetchone()
        return self._row(r) if r else None

    def search(self, query: str = "", *, doc_type: Optional[str] = None,
               client_id: Optional[int] = None, limit: int = 50) -> list[dict]:
        rows = [self._row(r) for r in self.conn.execute("SELECT * FROM extraction ORDER BY id DESC LIMIT 500")]
        q = query.lower()
        out = []
        for r in rows:
            blob = f"{r.get('filename','')} {r.get('doc_type','')} {r.get('summary','')} {r.get('text','')} {json.dumps(r['fields'])}".lower()
            if q and q not in blob:
                continue
            if doc_type and r["doc_type"] != doc_type:
                continue
            if client_id and r["client_id"] != client_id:
                continue
            out.append(r)
            if len(out) >= limit:
                break
        return out

    def link(self, doc_id: int, *, entity: str, entity_id: int) -> dict:
        with self._lock:
            self.conn.execute("UPDATE extraction SET link_entity=?, link_id=? WHERE id=?",
                              (entity, entity_id, doc_id))
            self.conn.commit()
        return self.get(doc_id)

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT doc_type, COUNT(*) n FROM extraction GROUP BY doc_type")
        return {"total": self.conn.execute("SELECT COUNT(*) FROM extraction").fetchone()[0],
                "by_type": {r["doc_type"]: r["n"] for r in rows}}

    def close(self):
        self.conn.close()
