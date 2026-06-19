"""BackupCatalog — tracks all HELIOS backup records."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS backup_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  backup_id TEXT NOT NULL UNIQUE,
  backup_type TEXT NOT NULL,
  components TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  size_bytes INTEGER,
  compressed_size_bytes INTEGER,
  encrypted INTEGER NOT NULL DEFAULT 1,
  verified INTEGER NOT NULL DEFAULT 0,
  verification_hash TEXT,
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'creating',
  retention_days INTEGER NOT NULL DEFAULT 30,
  notes TEXT
);
"""

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class BackupCatalog:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("HELIOS_BACKUP_CATALOG_DB") or os.path.join(
            BASE_DIR, "backups", "catalog.db"
        )
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
        conn.executescript(CATALOG_SCHEMA)
        conn.commit()

    def _row_to_dict(self, row) -> dict:
        if row is None:
            return {}
        d = dict(row)
        d["components"] = json.loads(d["components"])
        d["encrypted"] = bool(d["encrypted"])
        d["verified"] = bool(d["verified"])
        return d

    def register(self, backup_id: str, backup_type: str, components: list,
                 file_path: str, retention_days: int = 30) -> dict:
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "INSERT INTO backup_record (backup_id,backup_type,components,created_at,file_path,status,retention_days) "
                "VALUES (?,?,?,?,?,'creating',?)",
                (backup_id, backup_type, json.dumps(components), now, file_path, retention_days),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute("SELECT * FROM backup_record WHERE backup_id=?", (backup_id,)).fetchone()
        )

    def complete(self, backup_id: str, size_bytes: int, compressed_size_bytes: int,
                 verification_hash: str) -> dict:
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "UPDATE backup_record SET status='complete',completed_at=?,size_bytes=?,"
                "compressed_size_bytes=?,verification_hash=? WHERE backup_id=?",
                (now, size_bytes, compressed_size_bytes, verification_hash, backup_id),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute("SELECT * FROM backup_record WHERE backup_id=?", (backup_id,)).fetchone()
        )

    def fail(self, backup_id: str, reason: str) -> dict:
        now = _now()
        with self._lock:
            self._get_conn().execute(
                "UPDATE backup_record SET status='failed',completed_at=?,notes=? WHERE backup_id=?",
                (now, reason, backup_id),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute("SELECT * FROM backup_record WHERE backup_id=?", (backup_id,)).fetchone()
        )

    def get(self, backup_id: str) -> dict:
        row = self._get_conn().execute("SELECT * FROM backup_record WHERE backup_id=?", (backup_id,)).fetchone()
        if not row:
            raise KeyError(f"Backup '{backup_id}' not found.")
        return self._row_to_dict(row)

    def list(self, backup_type: Optional[str] = None, status: Optional[str] = None,
             limit: int = 50) -> list[dict]:
        where = []
        params = []
        if backup_type:
            where.append("backup_type = ?"); params.append(backup_type)
        if status:
            where.append("status = ?"); params.append(status)
        sql = "SELECT * FROM backup_record"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._get_conn().execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_expired(self) -> int:
        conn = self._get_conn()
        # Find expired records
        rows = conn.execute("SELECT backup_id, file_path, created_at, retention_days FROM backup_record WHERE status='complete'").fetchall()
        deleted = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            retention = timedelta(days=row["retention_days"])
            if now > created + retention:
                file_path = row["file_path"]
                if os.path.exists(file_path):
                    os.remove(file_path)
                with self._lock:
                    conn.execute("DELETE FROM backup_record WHERE backup_id=?", (row["backup_id"],))
                    conn.commit()
                deleted += 1
        return deleted

    def mark_verified(self, backup_id: str, ok: bool) -> dict:
        status = "complete" if ok else "corrupted"
        with self._lock:
            self._get_conn().execute(
                "UPDATE backup_record SET verified=?,status=? WHERE backup_id=?",
                (int(ok), status, backup_id),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute("SELECT * FROM backup_record WHERE backup_id=?", (backup_id,)).fetchone()
        )


_catalog: Optional[BackupCatalog] = None

def get_catalog() -> BackupCatalog:
    global _catalog
    if _catalog is None:
        _catalog = BackupCatalog()
    return _catalog
