from __future__ import annotations

"""ImmutableComplianceLogger backed by SQLite at .data/compliance.db"""

import csv
import hashlib
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

COMPLIANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS compliance_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL DEFAULT 'system',
  resource TEXT,
  resource_id TEXT,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL DEFAULT 'success',
  ip_address TEXT,
  session_id TEXT,
  detail TEXT,
  checksum TEXT NOT NULL
);
"""

VALID_EVENT_TYPES = {
    "login", "logout", "approval", "rejection", "execution", "accounting_action",
    "document_access", "memory_access", "vault_access", "sync_event", "backup_event",
    "admin_action", "security_event",
}


class ImmutableComplianceLogger:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("HELIOS_COMPLIANCE_DB") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".data", "compliance.db",
        )
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(COMPLIANCE_SCHEMA)
        conn.commit()

    @staticmethod
    def _compute_checksum(ts: str, event_type: str, actor: str, action: str, detail: str) -> str:
        payload = f"{ts}|{event_type}|{actor}|{action}|{detail or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def log(
        self,
        event_type: str,
        action: str,
        actor: str = "system",
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        outcome: str = "success",
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> int:
        if event_type not in VALID_EVENT_TYPES:
            event_type = "security_event"
        ts = datetime.now(timezone.utc).isoformat()
        checksum = self._compute_checksum(ts, event_type, actor, action, detail)
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO compliance_log "
            "(ts,event_type,actor,resource,resource_id,action,outcome,ip_address,session_id,detail,checksum) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (ts, event_type, actor, resource, resource_id, action, outcome,
             ip_address, session_id, detail, checksum),
        )
        conn.commit()
        return cur.lastrowid

    def query(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        where: list[str] = []
        params: list = []
        if event_type:
            where.append("event_type = ?")
            params.append(event_type)
        if actor:
            where.append("actor = ?")
            params.append(actor)
        if resource:
            where.append("resource = ?")
            params.append(resource)
        if start:
            where.append("ts >= ?")
            params.append(start)
        if end:
            where.append("ts <= ?")
            params.append(end)
        sql = "SELECT * FROM compliance_log"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self._get_conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def verify_integrity(self, entry_id: int) -> bool:
        row = self._get_conn().execute(
            "SELECT * FROM compliance_log WHERE id=?", (entry_id,)
        ).fetchone()
        if not row:
            return False
        expected = self._compute_checksum(
            row["ts"], row["event_type"], row["actor"], row["action"], row["detail"]
        )
        return expected == row["checksum"]

    def verify_chain(self, limit: int = 1000) -> dict:
        rows = self._get_conn().execute(
            "SELECT * FROM compliance_log ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
        total = len(rows)
        valid = 0
        invalid = 0
        tampered_ids: list[int] = []
        for row in rows:
            expected = self._compute_checksum(
                row["ts"], row["event_type"], row["actor"], row["action"], row["detail"]
            )
            if expected == row["checksum"]:
                valid += 1
            else:
                invalid += 1
                tampered_ids.append(row["id"])
        return {"total": total, "valid": valid, "invalid": invalid, "tampered_ids": tampered_ids}

    def export_csv(self, start: Optional[str] = None, end: Optional[str] = None) -> str:
        where: list[str] = []
        params: list = []
        if start:
            where.append("ts >= ?")
            params.append(start)
        if end:
            where.append("ts <= ?")
            params.append(end)
        sql = "SELECT * FROM compliance_log"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id"
        rows = self._get_conn().execute(sql, params).fetchall()
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        return output.getvalue()


    def count(self) -> int:
        """Return total number of compliance log entries."""
        row = self._get_conn().execute("SELECT COUNT(*) FROM compliance_log").fetchone()
        return row[0] if row else 0


_logger_instance: Optional[ImmutableComplianceLogger] = None


def get_compliance_logger() -> ImmutableComplianceLogger:
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ImmutableComplianceLogger()
    return _logger_instance


# Alias used by security_router
get_logger = get_compliance_logger
