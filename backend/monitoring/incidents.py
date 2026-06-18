"""IncidentManager — incident lifecycle, timeline, and MTTR statistics."""
from __future__ import annotations

import statistics
import uuid
from datetime import datetime
from typing import Optional

from .db import get_connection, now

_STATES = ["open", "investigating", "resolved", "closed"]


class IncidentManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def create(self, title: str, description: str = "", severity: str = "medium",
               component: Optional[str] = None, detected_by: Optional[str] = None) -> dict:
        incident_id = "inc_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            ts = now()
            conn.execute(
                "INSERT INTO incident (id, title, description, severity, component, status, "
                "detected_by, created_at) VALUES (?,?,?,?,?, 'open', ?, ?)",
                (incident_id, title, description, severity, component, detected_by, ts),
            )
            conn.execute(
                "INSERT INTO incident_timeline (incident_id, event_type, description, actor, created_at) "
                "VALUES (?, 'created', ?, ?, ?)",
                (incident_id, f"Incident opened: {title}", detected_by, ts),
            )
            conn.commit()
            return self.get(incident_id)
        finally:
            conn.close()

    def list(self, status: Optional[str] = None, severity: Optional[str] = None,
             limit: int = 50) -> list[dict]:
        clauses, params = [], []
        if status:
            clauses.append("status=?")
            params.append(status)
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT * FROM incident {where} ORDER BY created_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get(self, incident_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM incident WHERE id=?", (incident_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            tl = conn.execute(
                "SELECT * FROM incident_timeline WHERE incident_id=? ORDER BY created_at",
                (incident_id,),
            ).fetchall()
            d["timeline"] = [dict(t) for t in tl]
            return d
        finally:
            conn.close()

    def update_status(self, incident_id: str, status: str, note: Optional[str] = None,
                      updated_by: Optional[str] = None) -> Optional[dict]:
        if status not in _STATES:
            raise ValueError(f"Invalid status: {status}")
        conn = self._conn()
        try:
            conn.execute("UPDATE incident SET status=? WHERE id=?", (status, incident_id))
            conn.execute(
                "INSERT INTO incident_timeline (incident_id, event_type, description, actor, created_at) "
                "VALUES (?, 'status_change', ?, ?, ?)",
                (incident_id, note or f"Status → {status}", updated_by, now()),
            )
            conn.commit()
            return self.get(incident_id)
        finally:
            conn.close()

    def add_timeline_event(self, incident_id: str, event_type: str, description: str,
                           actor: Optional[str] = None) -> dict:
        conn = self._conn()
        try:
            ts = now()
            cur = conn.execute(
                "INSERT INTO incident_timeline (incident_id, event_type, description, actor, created_at) "
                "VALUES (?,?,?,?,?)",
                (incident_id, event_type, description, actor, ts),
            )
            conn.commit()
            return {"id": cur.lastrowid, "incident_id": incident_id, "event_type": event_type,
                    "description": description, "actor": actor, "created_at": ts}
        finally:
            conn.close()

    def resolve(self, incident_id: str, resolution: str, resolved_by: Optional[str] = None) -> bool:
        conn = self._conn()
        try:
            ts = now()
            cur = conn.execute(
                "UPDATE incident SET status='resolved', resolution=?, resolved_by=?, resolved_at=? "
                "WHERE id=?",
                (resolution, resolved_by, ts, incident_id),
            )
            conn.execute(
                "INSERT INTO incident_timeline (incident_id, event_type, description, actor, created_at) "
                "VALUES (?, 'resolved', ?, ?, ?)",
                (incident_id, resolution, resolved_by, ts),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def mttr_stats(self) -> dict:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT severity, created_at, resolved_at FROM incident WHERE resolved_at IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()
        durations, by_sev = [], {}
        for r in rows:
            try:
                start = datetime.fromisoformat(r["created_at"])
                end = datetime.fromisoformat(r["resolved_at"])
                mins = (end - start).total_seconds() / 60.0
            except Exception:
                continue
            durations.append(mins)
            by_sev.setdefault(r["severity"], []).append(mins)
        return {
            "total_resolved": len(durations),
            "mean_minutes": round(statistics.mean(durations), 2) if durations else 0,
            "median_minutes": round(statistics.median(durations), 2) if durations else 0,
            "by_severity": {k: round(statistics.mean(v), 2) for k, v in by_sev.items()},
        }


_instance: Optional[IncidentManager] = None


def get_incident_manager() -> IncidentManager:
    global _instance
    if _instance is None:
        _instance = IncidentManager()
    return _instance
