"""HELIOS Vault — encrypted credential store.

Secrets (OAuth tokens, API keys, broker/SMTP/N8N/DB credentials, encryption keys)
are encrypted with AES-256-GCM under a key derived from a master password via
scrypt. The vault locks/unlocks with the master password, versions every secret,
supports rotation (secret + master), and audits every access. Plaintext is never
persisted and never returned in listings.
"""
from __future__ import annotations

import base64
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from . import crypto

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (id INTEGER PRIMARY KEY CHECK (id=1),
  salt TEXT NOT NULL, check_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS secret (
  ref TEXT PRIMARY KEY, category TEXT, blob TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS secret_version (
  ref TEXT, version INTEGER, blob TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vault_access (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, ref TEXT, action TEXT, actor TEXT);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


class VaultLocked(RuntimeError):
    pass


class Vault:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_VAULT_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "vault.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._key: Optional[bytes] = None
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ---- lifecycle ----
    @property
    def initialized(self) -> bool:
        return self.conn.execute("SELECT 1 FROM vault_meta WHERE id=1").fetchone() is not None

    @property
    def unlocked(self) -> bool:
        return self._key is not None

    def initialize(self, master_password: str) -> dict:
        if self.initialized:
            raise RuntimeError("vault already initialized")
        salt = crypto.new_salt()
        key = crypto.derive_key(master_password, salt)
        with self._lock:
            self.conn.execute("INSERT INTO vault_meta (id,salt,check_hash,created_at) VALUES (1,?,?,?)",
                              (base64.b64encode(salt).decode(), crypto.sha256(key), _now()))
            self.conn.commit()
        self._key = key
        self._audit(None, "initialize")
        return {"initialized": True}

    def unlock(self, master_password: str) -> bool:
        row = self.conn.execute("SELECT salt, check_hash FROM vault_meta WHERE id=1").fetchone()
        if not row:
            raise RuntimeError("vault not initialized")
        salt = base64.b64decode(row["salt"])
        if not crypto.verify_password(master_password, salt, row["check_hash"]):
            self._audit(None, "unlock_failed")
            return False
        self._key = crypto.derive_key(master_password, salt)
        self._audit(None, "unlock")
        return True

    def lock(self) -> None:
        self._key = None
        self._audit(None, "lock")

    def _require(self):
        if not self._key:
            raise VaultLocked("vault is locked — unlock with the master password first")

    # ---- secrets ----
    def set_secret(self, ref: str, plaintext: str, *, category: str = "general", actor: str = "user") -> dict:
        self._require()
        blob = crypto.encrypt(self._key, plaintext.encode("utf-8"), aad=ref.encode())
        now = _now()
        with self._lock:
            existing = self.conn.execute("SELECT version FROM secret WHERE ref=?", (ref,)).fetchone()
            version = (existing["version"] + 1) if existing else 1
            if existing:
                self.conn.execute("INSERT INTO secret_version (ref,version,blob,created_at) "
                                  "SELECT ref,version,blob,updated_at FROM secret WHERE ref=?", (ref,))
                self.conn.execute("UPDATE secret SET blob=?, version=?, category=?, updated_at=? WHERE ref=?",
                                  (blob, version, category, now, ref))
            else:
                self.conn.execute("INSERT INTO secret (ref,category,blob,version,created_at,updated_at) "
                                  "VALUES (?,?,?,1,?,?)", (ref, category, blob, now, now))
            self.conn.commit()
        self._audit(ref, "write", actor)
        return {"ref": ref, "version": version, "category": category}

    def get_secret(self, ref: str, *, actor: str = "user") -> Optional[str]:
        self._require()
        row = self.conn.execute("SELECT blob FROM secret WHERE ref=?", (ref,)).fetchone()
        if not row:
            return None
        self._audit(ref, "read", actor)
        return crypto.decrypt(self._key, row["blob"], aad=ref.encode()).decode("utf-8")

    def rotate_secret(self, ref: str, new_plaintext: str, *, actor: str = "user") -> dict:
        if not self.conn.execute("SELECT 1 FROM secret WHERE ref=?", (ref,)).fetchone():
            raise ValueError("no such secret to rotate")
        out = self.set_secret(ref, new_plaintext, actor=actor)
        self._audit(ref, "rotate", actor)
        return out

    def delete_secret(self, ref: str, *, actor: str = "user") -> dict:
        with self._lock:
            self.conn.execute("DELETE FROM secret WHERE ref=?", (ref,))
            self.conn.commit()
        self._audit(ref, "delete", actor)
        return {"deleted": ref}

    def list_refs(self) -> list[dict]:
        """Metadata only — plaintext is never exposed in listings."""
        return [{"ref": r["ref"], "category": r["category"], "version": r["version"],
                 "updated_at": r["updated_at"]}
                for r in self.conn.execute("SELECT ref,category,version,updated_at FROM secret ORDER BY ref")]

    def rotate_master(self, old_password: str, new_password: str) -> dict:
        """Re-key every secret under a new master password."""
        if not self.unlock(old_password):
            raise ValueError("current master password is incorrect")
        old_key = self._key
        new_salt = crypto.new_salt()
        new_key = crypto.derive_key(new_password, new_salt)
        with self._lock:
            for r in self.conn.execute("SELECT ref, blob FROM secret").fetchall():
                pt = crypto.decrypt(old_key, r["blob"], aad=r["ref"].encode())
                self.conn.execute("UPDATE secret SET blob=? WHERE ref=?",
                                  (crypto.encrypt(new_key, pt, aad=r["ref"].encode()), r["ref"]))
            self.conn.execute("UPDATE vault_meta SET salt=?, check_hash=? WHERE id=1",
                              (base64.b64encode(new_salt).decode(), crypto.sha256(new_key)))
            self.conn.commit()
        self._key = new_key
        self._audit(None, "rotate_master")
        return {"rotated": True}

    def _audit(self, ref, action, actor="system"):
        self.conn.execute("INSERT INTO vault_access (ts,ref,action,actor) VALUES (?,?,?,?)",
                          (_now(), ref, action, actor))
        self.conn.commit()

    def access_log(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT ts,ref,action,actor FROM vault_access ORDER BY id DESC LIMIT ?", (limit,))]

    def status(self) -> dict:
        return {"initialized": self.initialized, "unlocked": self.unlocked,
                "secret_count": self.conn.execute("SELECT COUNT(*) n FROM secret").fetchone()["n"],
                "algorithm": "AES-256-GCM", "kdf": "scrypt"}

    def close(self):
        self.conn.close()
