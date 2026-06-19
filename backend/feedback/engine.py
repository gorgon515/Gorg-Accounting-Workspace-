"""
Feedback engine.
Captures errors, user actions, feature usage, workflow completion,
suggestions, friction points, and failures. Dedup by signature
increments frequency.
SQLite persistence at ~/.helios/feedback.db.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "feedback.db"

KINDS = ("error", "action", "usage", "completion", "suggestion", "friction", "failure")
SEVERITIES = ("low", "medium", "high", "critical")

_FB_COLS = [
    "id", "kind", "title", "detail", "severity", "frequency", "impact",
    "suggested_fix", "context_json", "signature", "status",
    "created_at", "updated_at",
]


class FeedbackEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                kind TEXT,
                title TEXT,
                detail TEXT,
                severity TEXT,
                frequency INTEGER,
                impact TEXT,
                suggested_fix TEXT,
                context_json TEXT DEFAULT '{}',
                signature TEXT,
                status TEXT,
                created_at REAL,
                updated_at REAL
            );
            """)

    def _row_to_dict(self, row) -> dict:
        d = dict(zip(_FB_COLS, row))
        try:
            d["context"] = json.loads(d.pop("context_json") or "{}")
        except Exception:
            d["context"] = {}
        return d

    def _signature(self, kind: str, title: str) -> str:
        return hashlib.sha256(
            f"{kind}|{title}".lower().encode("utf-8")
        ).hexdigest()[:16]

    def capture(self, kind: str, title: str, detail: str = "",
                severity: str = "medium", impact: str = "",
                suggested_fix: str = "", context: dict = None) -> dict:
        if kind not in KINDS:
            raise ValueError(f"Unknown kind: {kind}")
        signature = self._signature(kind, title)
        now = time.time()
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT * FROM feedback WHERE signature=? AND status!='resolved' "
                "ORDER BY created_at ASC LIMIT 1", (signature,)
            ).fetchone()
            if row:
                existing = self._row_to_dict(row)
                new_detail = existing["detail"] or ""
                if detail and len(detail) > len(new_detail):
                    new_detail = detail
                c.execute(
                    "UPDATE feedback SET frequency=frequency+1, updated_at=?, "
                    "detail=? WHERE id=?",
                    (now, new_detail, existing["id"])
                )
                fid = existing["id"]
            else:
                fid = str(uuid.uuid4())
                c.execute(
                    "INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fid, kind, title, detail, severity, 1, impact,
                     suggested_fix, json.dumps(context or {}), signature,
                     "open", now, now)
                )
        return self.get(fid)

    def get(self, fid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT * FROM feedback WHERE id=?", (fid,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, kind: str = None, status: str = None,
             severity: str = None, limit: int = 100) -> list:
        clauses = []
        params = []
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        if status:
            clauses.append("status=?")
            params.append(status)
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                f"SELECT * FROM feedback{where} "
                "ORDER BY frequency DESC, created_at DESC LIMIT ?", params
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_status(self, fid: str, status: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE feedback SET status=?, updated_at=? WHERE id=?",
                (status, time.time(), fid)
            )
        return self.get(fid)

    def resolve(self, fid: str, suggested_fix: str = None) -> Optional[dict]:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            if suggested_fix is not None:
                c.execute(
                    "UPDATE feedback SET status='resolved', suggested_fix=?, "
                    "updated_at=? WHERE id=?", (suggested_fix, now, fid)
                )
            else:
                c.execute(
                    "UPDATE feedback SET status='resolved', updated_at=? WHERE id=?",
                    (now, fid)
                )
        return self.get(fid)

    def top_friction(self, limit: int = 10) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM feedback WHERE kind IN ('friction','failure','error') "
                "ORDER BY frequency DESC, created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def top_failures(self, limit: int = 10) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM feedback WHERE kind='failure' "
                "ORDER BY frequency DESC, created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def by_severity(self) -> dict:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT severity, COUNT(*) FROM feedback GROUP BY severity"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def summary(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            open_count = c.execute(
                "SELECT COUNT(*) FROM feedback WHERE status='open'"
            ).fetchone()[0]
            resolved = c.execute(
                "SELECT COUNT(*) FROM feedback WHERE status='resolved'"
            ).fetchone()[0]
            kind_rows = c.execute(
                "SELECT kind, COUNT(*) FROM feedback GROUP BY kind"
            ).fetchall()
        return {
            "total": total,
            "open": open_count,
            "resolved": resolved,
            "by_kind": {r[0]: r[1] for r in kind_rows},
            "by_severity": self.by_severity(),
            "top_friction": self.top_friction(5),
        }

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            open_count = c.execute(
                "SELECT COUNT(*) FROM feedback WHERE status='open'"
            ).fetchone()[0]
            kind_rows = c.execute(
                "SELECT kind, COUNT(*) FROM feedback GROUP BY kind"
            ).fetchall()
            total_occurrences = c.execute(
                "SELECT COALESCE(SUM(frequency), 0) FROM feedback"
            ).fetchone()[0]
        return {
            "total": total,
            "open": open_count,
            "by_kind": {r[0]: r[1] for r in kind_rows},
            "total_occurrences": total_occurrences,
        }


_instance: Optional[FeedbackEngine] = None


def get_feedback_engine() -> FeedbackEngine:
    global _instance
    if _instance is None:
        _instance = FeedbackEngine()
    return _instance
