"""SyncEngine — delta synchronization across devices."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .device_registry import DeviceRegistry, get_device_registry

SYNC_ENGINE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  component TEXT NOT NULL,
  record_id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  data_hash TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  device_id TEXT NOT NULL,
  tombstone INTEGER NOT NULL DEFAULT 0,
  UNIQUE(component, record_id)
);
CREATE TABLE IF NOT EXISTS sync_conflict (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  component TEXT NOT NULL,
  record_id TEXT NOT NULL,
  local_version INTEGER,
  remote_version INTEGER,
  resolution TEXT,
  resolved_at TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  device_id TEXT NOT NULL,
  component TEXT NOT NULL,
  action TEXT NOT NULL,
  record_count INTEGER NOT NULL DEFAULT 0,
  session_id TEXT
);
"""

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SyncRecord:
    component: str
    record_id: str
    version: int = 1
    data_hash: str = ""
    updated_at: str = ""
    device_id: str = ""
    tombstone: bool = False


class SyncEngine:
    def __init__(self, device_registry: Optional[DeviceRegistry] = None, db_path: Optional[str] = None):
        self._registry = device_registry or get_device_registry()
        self._db_path = db_path or os.environ.get("HELIOS_SYNC_DB") or os.path.join(BASE_DIR, "sync", "sync.db")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(SYNC_ENGINE_SCHEMA)
        conn.commit()

    def get_delta(self, device_id: str, component: str, since_version: int = 0) -> list[dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM sync_record WHERE component=? AND version > ? ORDER BY version ASC",
            (component, since_version),
        ).fetchall()
        self._get_conn().execute(
            "INSERT INTO sync_audit (ts,device_id,component,action,record_count) VALUES (?,?,?,'get_delta',?)",
            (_now(), device_id, component, len(rows)),
        )
        self._get_conn().commit()
        return [dict(r) for r in rows]

    def push(self, device_id: str, component: str, records: list[dict]) -> dict:
        accepted = 0
        conflicts = 0
        rejected = 0
        conflict_ids = []
        conn = self._get_conn()
        now = _now()
        for record in records:
            record_id = record.get("record_id")
            if not record_id:
                rejected += 1
                continue
            data_hash = record.get("data_hash", "")
            version = record.get("version", 1)
            tombstone = int(record.get("tombstone", False))
            existing = conn.execute(
                "SELECT * FROM sync_record WHERE component=? AND record_id=?",
                (component, record_id),
            ).fetchone()
            with self._lock:
                if existing is None:
                    conn.execute(
                        "INSERT INTO sync_record (component,record_id,version,data_hash,updated_at,device_id,tombstone) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (component, record_id, version, data_hash, now, device_id, tombstone),
                    )
                    accepted += 1
                elif version > existing["version"]:
                    conn.execute(
                        "UPDATE sync_record SET version=?,data_hash=?,updated_at=?,device_id=?,tombstone=? "
                        "WHERE component=? AND record_id=?",
                        (version, data_hash, now, device_id, tombstone, component, record_id),
                    )
                    accepted += 1
                elif version == existing["version"] and data_hash != existing["data_hash"]:
                    # Conflict: same version, different data
                    cur = conn.execute(
                        "INSERT INTO sync_conflict (component,record_id,local_version,remote_version,created_at) "
                        "VALUES (?,?,?,?,?)",
                        (component, record_id, existing["version"], version, now),
                    )
                    conflicts += 1
                    conflict_ids.append(cur.lastrowid)
                else:
                    # Already up to date or older version
                    accepted += 1
            conn.commit()
        conn.execute(
            "INSERT INTO sync_audit (ts,device_id,component,action,record_count) VALUES (?,?,?,'push',?)",
            (now, device_id, component, len(records)),
        )
        conn.commit()
        return {"accepted": accepted, "conflicts": conflicts, "rejected": rejected, "conflict_ids": conflict_ids}

    def resolve_conflict(self, conflict_id: int, resolution: str, winning_data: Optional[dict] = None) -> dict:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM sync_conflict WHERE id=?", (conflict_id,)).fetchone()
        if not row:
            raise KeyError(f"Conflict {conflict_id} not found.")
        now = _now()
        if resolution == "last_write_wins":
            # Accept the remote (higher version wins)
            pass
        elif resolution in ("manual", "merge") and winning_data:
            # Apply winning data to sync_record
            data_hash = winning_data.get("data_hash", "")
            version = max(row["local_version"] or 0, row["remote_version"] or 0) + 1
            existing = conn.execute(
                "SELECT * FROM sync_record WHERE component=? AND record_id=?",
                (row["component"], row["record_id"]),
            ).fetchone()
            with self._lock:
                if existing:
                    conn.execute(
                        "UPDATE sync_record SET version=?,data_hash=?,updated_at=? WHERE component=? AND record_id=?",
                        (version, data_hash, now, row["component"], row["record_id"]),
                    )
                conn.commit()
        with self._lock:
            conn.execute(
                "UPDATE sync_conflict SET resolution=?,resolved_at=? WHERE id=?",
                (resolution, now, conflict_id),
            )
            conn.commit()
        return dict(conn.execute("SELECT * FROM sync_conflict WHERE id=?", (conflict_id,)).fetchone())

    def get_sync_status(self, device_id: str) -> dict:
        conn = self._get_conn()
        # Get last sync time from audit
        last_audit = conn.execute(
            "SELECT ts FROM sync_audit WHERE device_id=? ORDER BY id DESC LIMIT 1",
            (device_id,),
        ).fetchone()
        pending = conn.execute(
            "SELECT COUNT(*) FROM sync_record WHERE device_id != ? AND tombstone=0",
            (device_id,),
        ).fetchone()[0]
        unresolved_conflicts = conn.execute(
            "SELECT COUNT(*) FROM sync_conflict WHERE resolution IS NULL"
        ).fetchone()[0]
        return {
            "device_id": device_id,
            "last_sync": last_audit["ts"] if last_audit else None,
            "pending_records": pending,
            "unresolved_conflicts": unresolved_conflicts,
        }

    def list_conflicts(self, resolved: bool = False) -> list[dict]:
        if resolved:
            rows = self._get_conn().execute(
                "SELECT * FROM sync_conflict WHERE resolution IS NOT NULL ORDER BY id DESC"
            ).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT * FROM sync_conflict WHERE resolution IS NULL ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def sync_audit_log(self, device_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        if device_id:
            rows = self._get_conn().execute(
                "SELECT * FROM sync_audit WHERE device_id=? ORDER BY id DESC LIMIT ?",
                (device_id, limit),
            ).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT * FROM sync_audit ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


_sync_engine: Optional[SyncEngine] = None

def get_sync_engine() -> SyncEngine:
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = SyncEngine()
    return _sync_engine
