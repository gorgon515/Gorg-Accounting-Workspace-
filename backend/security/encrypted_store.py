"""Encrypted key-value store — AES-256-GCM at rest for memory and documents.

A generic store used for HELIOS objectives "Encrypted Memory" and "Encrypted
Document Storage". Values are encrypted under a 32-byte key (supplied by the
vault) before they touch disk; the key/ref binding is enforced as AAD so a blob
cannot be replayed under a different key. Every read and write is access-logged.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from . import crypto

_SCHEMA = """
CREATE TABLE IF NOT EXISTS enc_item (
  ns TEXT NOT NULL, key TEXT NOT NULL, blob TEXT NOT NULL, meta TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (ns, key));
CREATE TABLE IF NOT EXISTS enc_access (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, ns TEXT, key TEXT,
  action TEXT, actor TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EncryptedStore:
    """Namespaced encrypted KV. `key` may be any 32-byte value (e.g. from the vault)."""

    def __init__(self, key: bytes, path: Optional[str] = None):
        if not key or len(key) != crypto.KEY_BYTES:
            raise ValueError(f"encryption key must be {crypto.KEY_BYTES} bytes")
        self._key = key
        self.path = path or os.environ.get("HELIOS_ENCSTORE_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "encrypted_store.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _aad(self, ns: str, key: str) -> bytes:
        return f"{ns}:{key}".encode("utf-8")

    def put(self, ns: str, key: str, value, *, meta: str = "", actor: str = "system") -> dict:
        """Encrypt and store a JSON-serialisable value under (ns, key)."""
        blob = crypto.encrypt_json(self._key, value, aad=self._aad(ns, key))
        now = _now()
        with self._lock:
            existing = self.conn.execute(
                "SELECT created_at FROM enc_item WHERE ns=? AND key=?", (ns, key)).fetchone()
            created = existing["created_at"] if existing else now
            self.conn.execute(
                "INSERT INTO enc_item (ns,key,blob,meta,created_at,updated_at) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(ns,key) DO UPDATE SET blob=excluded.blob, meta=excluded.meta, "
                "updated_at=excluded.updated_at",
                (ns, key, blob, meta, created, now))
            self.conn.commit()
        self._audit(ns, key, "write", actor)
        return {"ns": ns, "key": key, "updated_at": now}

    def get(self, ns: str, key: str, *, actor: str = "system"):
        """Decrypt and return a value, or None if absent."""
        row = self.conn.execute("SELECT blob FROM enc_item WHERE ns=? AND key=?", (ns, key)).fetchone()
        if not row:
            return None
        self._audit(ns, key, "read", actor)
        return crypto.decrypt_json(self._key, row["blob"], aad=self._aad(ns, key))

    def delete(self, ns: str, key: str, *, actor: str = "system") -> dict:
        with self._lock:
            self.conn.execute("DELETE FROM enc_item WHERE ns=? AND key=?", (ns, key))
            self.conn.commit()
        self._audit(ns, key, "delete", actor)
        return {"deleted": f"{ns}:{key}"}

    def keys(self, ns: Optional[str] = None) -> list[dict]:
        """Metadata listing — never decrypts or exposes plaintext."""
        sql = "SELECT ns,key,meta,updated_at FROM enc_item"
        args: list = []
        if ns:
            sql += " WHERE ns=?"; args.append(ns)
        sql += " ORDER BY ns, key"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def reencrypt(self, new_key: bytes) -> int:
        """Re-key every item under a new encryption key (used on master rotation)."""
        if len(new_key) != crypto.KEY_BYTES:
            raise ValueError("new key must be 32 bytes")
        n = 0
        with self._lock:
            for r in self.conn.execute("SELECT ns,key,blob FROM enc_item").fetchall():
                aad = self._aad(r["ns"], r["key"])
                pt = crypto.decrypt(self._key, r["blob"], aad=aad)
                self.conn.execute("UPDATE enc_item SET blob=? WHERE ns=? AND key=?",
                                  (crypto.encrypt(new_key, pt, aad=aad), r["ns"], r["key"]))
                n += 1
            self.conn.commit()
        self._key = new_key
        return n

    def _audit(self, ns, key, action, actor):
        self.conn.execute("INSERT INTO enc_access (ts,ns,key,action,actor) VALUES (?,?,?,?,?)",
                          (_now(), ns, key, action, actor))
        self.conn.commit()

    def access_log(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT ts,ns,key,action,actor FROM enc_access ORDER BY id DESC LIMIT ?", (limit,))]

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT ns, COUNT(*) n FROM enc_item GROUP BY ns")
        return {"total": self.conn.execute("SELECT COUNT(*) n FROM enc_item").fetchone()["n"],
                "by_namespace": {r["ns"]: r["n"] for r in rows},
                "algorithm": "AES-256-GCM"}

    def close(self):
        self.conn.close()
