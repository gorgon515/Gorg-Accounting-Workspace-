"""EncryptedMemoryStore — encrypts memory items at rest."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from .aes import encrypt_str, decrypt_str, sha256_hex

MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL DEFAULT 'general',
  encrypted_content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  agent_name TEXT,
  ttl_expires TEXT
);
CREATE TABLE IF NOT EXISTS memory_access_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  item_id TEXT NOT NULL,
  action TEXT NOT NULL,
  accessor TEXT NOT NULL DEFAULT 'system',
  success INTEGER NOT NULL DEFAULT 1
);
"""

VALID_CATEGORIES = {
    "long_term", "user_memory", "goal", "task", "agent_memory",
    "knowledge_graph", "research_history", "document_metadata", "general",
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    ".data",
)

class EncryptedMemoryStore:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("HELIOS_ENC_MEMORY_DB") or os.path.join(
            BASE_DIR, "enc_memory", "memory.db"
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
        conn.executescript(MEMORY_SCHEMA)
        conn.commit()

    def _log_access(self, item_id: str, action: str, accessor: str, success: bool = True) -> None:
        self._get_conn().execute(
            "INSERT INTO memory_access_log (ts,item_id,action,accessor,success) VALUES (?,?,?,?,?)",
            (_now(), item_id, action, accessor, int(success)),
        )
        self._get_conn().commit()

    def store(self, key: bytes, item_id: str, content: dict, category: str,
              agent_name: Optional[str] = None, tags: list = None, ttl_days: Optional[int] = None) -> dict:
        if tags is None:
            tags = []
        if category not in VALID_CATEGORIES:
            category = "general"
        now = _now()
        content_str = json.dumps(content, separators=(",", ":"))
        content_hash = sha256_hex(content_str.encode("utf-8"))
        encrypted = encrypt_str(key, content_str)
        ttl_expires = None
        if ttl_days is not None:
            ttl_expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
        conn = self._get_conn()
        existing = conn.execute("SELECT * FROM memory_item WHERE item_id=?", (item_id,)).fetchone()
        with self._lock:
            if existing:
                new_version = existing["version"] + 1
                conn.execute(
                    "UPDATE memory_item SET encrypted_content=?,content_hash=?,version=?,updated_at=?,"
                    "tags=?,agent_name=?,ttl_expires=?,category=? WHERE item_id=?",
                    (encrypted, content_hash, new_version, now, json.dumps(tags), agent_name, ttl_expires, category, item_id),
                )
                conn.commit()
                version = new_version
            else:
                conn.execute(
                    "INSERT INTO memory_item (item_id,category,encrypted_content,content_hash,version,"
                    "created_at,updated_at,tags,agent_name,ttl_expires) VALUES (?,?,?,?,1,?,?,?,?,?)",
                    (item_id, category, encrypted, content_hash, now, now, json.dumps(tags), agent_name, ttl_expires),
                )
                conn.commit()
                version = 1
        self._log_access(item_id, "store", agent_name or "system")
        return {
            "item_id": item_id, "category": category, "version": version,
            "content_hash": content_hash, "updated_at": now, "ttl_expires": ttl_expires,
        }

    def retrieve(self, key: bytes, item_id: str, accessor: str = "system") -> dict:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM memory_item WHERE item_id=?", (item_id,)).fetchone()
        if not row:
            self._log_access(item_id, "retrieve", accessor, success=False)
            raise KeyError(f"Memory item '{item_id}' not found.")
        # Check TTL
        if row["ttl_expires"] and _now() > row["ttl_expires"]:
            self._log_access(item_id, "retrieve_expired", accessor, success=False)
            raise KeyError(f"Memory item '{item_id}' has expired.")
        content_str = decrypt_str(key, row["encrypted_content"])
        content = json.loads(content_str)
        self._log_access(item_id, "retrieve", accessor)
        return {
            "item_id": item_id,
            "category": row["category"],
            "content": content,
            "content_hash": row["content_hash"],
            "version": row["version"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "tags": json.loads(row["tags"]),
            "agent_name": row["agent_name"],
            "ttl_expires": row["ttl_expires"],
        }

    def search(self, key: bytes, category: Optional[str] = None,
               agent_name: Optional[str] = None, tags: list = None) -> list[dict]:
        where = ["(ttl_expires IS NULL OR ttl_expires > ?)"]
        params: list = [_now()]
        if category:
            where.append("category = ?"); params.append(category)
        if agent_name:
            where.append("agent_name = ?"); params.append(agent_name)
        sql = "SELECT * FROM memory_item WHERE " + " AND ".join(where) + " ORDER BY updated_at DESC"
        rows = self._get_conn().execute(sql, params).fetchall()
        results = []
        for row in rows:
            item_tags = json.loads(row["tags"])
            if tags:
                if not all(t in item_tags for t in tags):
                    continue
            content_str = decrypt_str(key, row["encrypted_content"])
            results.append({
                "item_id": row["item_id"],
                "category": row["category"],
                "content": json.loads(content_str),
                "content_hash": row["content_hash"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "tags": item_tags,
                "agent_name": row["agent_name"],
                "ttl_expires": row["ttl_expires"],
            })
        return results

    def delete(self, item_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT id FROM memory_item WHERE item_id=?", (item_id,)).fetchone()
        if not row:
            return False
        with self._lock:
            conn.execute("DELETE FROM memory_item WHERE item_id=?", (item_id,))
            conn.commit()
        self._log_access(item_id, "delete", "system")
        return True

    def access_log(self, item_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        if item_id:
            rows = self._get_conn().execute(
                "SELECT * FROM memory_access_log WHERE item_id=? ORDER BY id DESC LIMIT ?",
                (item_id, limit),
            ).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT * FROM memory_access_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def purge_expired(self) -> int:
        now = _now()
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM memory_item WHERE ttl_expires IS NOT NULL AND ttl_expires <= ?", (now,))
        conn.commit()
        return cur.rowcount


_memory_store: Optional[EncryptedMemoryStore] = None

def get_memory_store() -> EncryptedMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = EncryptedMemoryStore()
    return _memory_store
