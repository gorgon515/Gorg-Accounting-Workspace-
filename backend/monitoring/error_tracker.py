"""ErrorTracker — records and aggregates application errors."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import get_connection, now


class ErrorTracker:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def record(self, error_type: str, message: str, stack_trace: Optional[str] = None,
               component: Optional[str] = None, severity: str = "error",
               context: Optional[dict] = None) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO error_event (error_type, message, stack_trace, component, severity, "
                "context, created_at) VALUES (?,?,?,?,?,?,?)",
                (error_type, message, stack_trace, component, severity,
                 json.dumps(context) if context else None, now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list(self, severity: Optional[str] = None, component: Optional[str] = None,
             resolved: Optional[bool] = None, limit: int = 100) -> list[dict]:
        clauses, params = [], []
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        if component:
            clauses.append("component=?")
            params.append(component)
        if resolved is not None:
            clauses.append("resolved=?")
            params.append(1 if resolved else 0)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT * FROM error_event {where} ORDER BY created_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, error_id: int) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM error_event WHERE id=?", (error_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def resolve(self, error_id: int, resolved_by: Optional[str] = None) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE error_event SET resolved=1, resolved_by=?, resolved_at=? WHERE id=?",
                (resolved_by, now(), error_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) c FROM error_event").fetchone()["c"]
            unresolved = conn.execute(
                "SELECT COUNT(*) c FROM error_event WHERE resolved=0"
            ).fetchone()["c"]
            by_sev = {
                r["severity"]: r["c"]
                for r in conn.execute(
                    "SELECT severity, COUNT(*) c FROM error_event GROUP BY severity"
                ).fetchall()
            }
            by_comp = {
                (r["component"] or "unknown"): r["c"]
                for r in conn.execute(
                    "SELECT component, COUNT(*) c FROM error_event GROUP BY component"
                ).fetchall()
            }
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            recent = conn.execute(
                "SELECT COUNT(*) c FROM error_event WHERE created_at >= ?", (cutoff,)
            ).fetchone()["c"]
            return {
                "total": total, "unresolved": unresolved, "recent_24h": recent,
                "by_severity": by_sev, "by_component": by_comp,
            }
        finally:
            conn.close()

    def cleanup_old(self, days: int = 30) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()
        try:
            cur = conn.execute(
                "DELETE FROM error_event WHERE resolved=1 AND created_at < ?", (cutoff,)
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        if d.get("context"):
            try:
                d["context"] = json.loads(d["context"])
            except Exception:
                pass
        d["resolved"] = bool(d["resolved"])
        return d


_instance: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    global _instance
    if _instance is None:
        _instance = ErrorTracker()
    return _instance
