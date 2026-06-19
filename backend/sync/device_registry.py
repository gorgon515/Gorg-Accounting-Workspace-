"""DeviceRegistry — tracks devices and sync sessions."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

DEVICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS device (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL UNIQUE,
  device_name TEXT NOT NULL,
  device_type TEXT NOT NULL DEFAULT 'desktop',
  platform TEXT,
  last_seen TEXT,
  registered_at TEXT NOT NULL,
  public_key TEXT,
  status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS sync_session (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL UNIQUE,
  device_id TEXT NOT NULL REFERENCES device(device_id),
  started_at TEXT NOT NULL,
  completed_at TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  records_synced INTEGER NOT NULL DEFAULT 0,
  conflicts_resolved INTEGER NOT NULL DEFAULT 0
);
"""

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class DeviceRegistry:
    def __init__(self, db_path: Optional[str] = None):
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
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(DEVICE_SCHEMA)
        conn.commit()

    def register(self, device_name: str, device_type: str = "desktop",
                 platform: Optional[str] = None, public_key: Optional[str] = None) -> dict:
        device_id = str(uuid.uuid4())
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "INSERT INTO device (device_id,device_name,device_type,platform,last_seen,registered_at,public_key,status) "
                "VALUES (?,?,?,?,?,?,?,'active')",
                (device_id, device_name, device_type, platform, now, now, public_key),
            )
            self._get_conn().commit()
        return dict(self._get_conn().execute("SELECT * FROM device WHERE device_id=?", (device_id,)).fetchone())

    def heartbeat(self, device_id: str) -> bool:
        row = self._get_conn().execute("SELECT id FROM device WHERE device_id=?", (device_id,)).fetchone()
        if not row:
            return False
        self._get_conn().execute("UPDATE device SET last_seen=? WHERE device_id=?", (_now(), device_id))
        self._get_conn().commit()
        return True

    def deregister(self, device_id: str) -> bool:
        row = self._get_conn().execute("SELECT id FROM device WHERE device_id=?", (device_id,)).fetchone()
        if not row:
            return False
        with self._lock:
            self._get_conn().execute("UPDATE device SET status='inactive' WHERE device_id=?", (device_id,))
            self._get_conn().commit()
        return True

    def list_devices(self) -> list[dict]:
        rows = self._get_conn().execute("SELECT * FROM device ORDER BY registered_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get(self, device_id: str) -> dict:
        row = self._get_conn().execute("SELECT * FROM device WHERE device_id=?", (device_id,)).fetchone()
        if not row:
            raise KeyError(f"Device '{device_id}' not found.")
        return dict(row)

    def start_session(self, device_id: str) -> dict:
        # Ensure device exists
        self.get(device_id)
        session_id = str(uuid.uuid4())
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "INSERT INTO sync_session (session_id,device_id,started_at,status) VALUES (?,?,?,'active')",
                (session_id, device_id, now),
            )
            # Update device last_seen
            self._get_conn().execute("UPDATE device SET last_seen=? WHERE device_id=?", (now, device_id))
            self._get_conn().commit()
        return dict(self._get_conn().execute("SELECT * FROM sync_session WHERE session_id=?", (session_id,)).fetchone())

    def complete_session(self, session_id: str, records_synced: int, conflicts_resolved: int) -> dict:
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "UPDATE sync_session SET status='complete',completed_at=?,records_synced=?,conflicts_resolved=? "
                "WHERE session_id=?",
                (now, records_synced, conflicts_resolved, session_id),
            )
            self._get_conn().commit()
        row = self._get_conn().execute("SELECT * FROM sync_session WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            raise KeyError(f"Session '{session_id}' not found.")
        return dict(row)


_registry: Optional[DeviceRegistry] = None

def get_device_registry() -> DeviceRegistry:
    global _registry
    if _registry is None:
        _registry = DeviceRegistry()
    return _registry
