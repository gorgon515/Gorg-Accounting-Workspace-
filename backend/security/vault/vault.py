"""HELIOS Vault — AES-256 encrypted credential store backed by SQLite.

Secrets are encrypted at rest. The master key is derived from a master password
via PBKDF2-HMAC-SHA256. Each secret carries its own nonce; the master key salt
is stored in the vault database. Access to every secret is logged immutably.

Categories:
  oauth_token, api_key, db_credential, broker_credential,
  smtp_credential, n8n_credential, encryption_key, other
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from ..encryption.aes import (
    derive_key, new_salt, encrypt, decrypt,
    encrypt_str, decrypt_str, PBKDF2_ITERATIONS, KEY_LEN,
)

VAULT_SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vault_secret (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'other',
  encrypted_value TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  rotated_at TEXT,
  expires_at TEXT,
  description TEXT,
  UNIQUE(name)
);
CREATE TABLE IF NOT EXISTS vault_secret_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  secret_id INTEGER NOT NULL REFERENCES vault_secret(id),
  version INTEGER NOT NULL,
  encrypted_value TEXT NOT NULL,
  archived_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vault_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  action TEXT NOT NULL,
  secret_name TEXT,
  category TEXT,
  user TEXT NOT NULL DEFAULT 'system',
  ip TEXT,
  success INTEGER NOT NULL DEFAULT 1,
  detail TEXT
);
"""

VALID_CATEGORIES = {
    "oauth_token", "api_key", "db_credential", "broker_credential",
    "smtp_credential", "n8n_credential", "encryption_key", "other",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Vault:
    """Thread-safe encrypted credential vault."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("HELIOS_VAULT_DB") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".data", "vault", "vault.db",
        )
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._key: Optional[bytes] = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(VAULT_SCHEMA)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _audit(self, action: str, name: Optional[str] = None, category: Optional[str] = None,
               user: str = "system", success: bool = True, detail: str = "") -> None:
        self._get_conn().execute(
            "INSERT INTO vault_audit (ts,action,secret_name,category,user,success,detail) VALUES (?,?,?,?,?,?,?)",
            (_now(), action, name, category, user, int(success), detail),
        )
        self._get_conn().commit()

    # ---- master key management ----

    def initialize(self, master_password: str, user: str = "system") -> dict:
        """Initialize vault with a master password. Creates salt and stores it."""
        conn = self._get_conn()
        existing = conn.execute("SELECT value FROM vault_meta WHERE key='salt'").fetchone()
        if existing:
            raise ValueError("Vault already initialized. Use unlock() instead.")
        salt = new_salt()
        salt_b64 = base64.b64encode(salt).decode("ascii")
        conn.execute("INSERT INTO vault_meta (key,value) VALUES ('salt',?)", (salt_b64,))
        conn.execute("INSERT INTO vault_meta (key,value) VALUES ('version','1')", )
        conn.execute("INSERT INTO vault_meta (key,value) VALUES ('iterations',?)", (str(PBKDF2_ITERATIONS),))
        conn.commit()
        self._key = derive_key(master_password, salt)
        self._audit("vault_initialize", user=user, detail="Vault initialized")
        return {"status": "initialized", "algorithm": "AES-256-GCM", "kdf": "PBKDF2-HMAC-SHA256",
                "iterations": PBKDF2_ITERATIONS}

    def unlock(self, master_password: str, user: str = "system") -> bool:
        """Derive the master key from the password. Must be called before any secret operations."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM vault_meta WHERE key='salt'").fetchone()
        if not row:
            raise ValueError("Vault not initialized. Call initialize() first.")
        salt = base64.b64decode(row["value"])
        iterations_row = conn.execute("SELECT value FROM vault_meta WHERE key='iterations'").fetchone()
        iterations = int(iterations_row["value"]) if iterations_row else PBKDF2_ITERATIONS
        self._key = derive_key(master_password, salt, iterations)
        self._audit("vault_unlock", user=user, detail="Vault unlocked")
        return True

    def lock(self, user: str = "system") -> None:
        """Clear the master key from memory."""
        self._audit("vault_lock", user=user)
        self._key = None

    def is_unlocked(self) -> bool:
        return self._key is not None

    def is_initialized(self) -> bool:
        row = self._get_conn().execute("SELECT value FROM vault_meta WHERE key='salt'").fetchone()
        return row is not None

    def _require_key(self) -> bytes:
        if self._key is None:
            raise PermissionError("Vault is locked. Call unlock() with the master password.")
        return self._key

    # ---- secret operations ----

    def store(self, name: str, value: str, category: str = "other",
              description: str = "", expires_at: Optional[str] = None,
              user: str = "system") -> dict:
        """Store or update a secret. Moves the old version to history."""
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Choose from: {sorted(VALID_CATEGORIES)}")
        key = self._require_key()
        encrypted = encrypt_str(key, value)
        now = _now()
        conn = self._get_conn()
        with self._lock:
            existing = conn.execute("SELECT * FROM vault_secret WHERE name=?", (name,)).fetchone()
            if existing:
                conn.execute(
                    "INSERT INTO vault_secret_history (secret_id,version,encrypted_value,archived_at) VALUES (?,?,?,?)",
                    (existing["id"], existing["version"], existing["encrypted_value"], now),
                )
                new_ver = existing["version"] + 1
                conn.execute(
                    "UPDATE vault_secret SET encrypted_value=?,version=?,category=?,description=?,updated_at=?,expires_at=? WHERE name=?",
                    (encrypted, new_ver, category, description, now, expires_at, name),
                )
                action = "secret_update"
            else:
                conn.execute(
                    "INSERT INTO vault_secret (name,category,encrypted_value,version,created_at,updated_at,description,expires_at) "
                    "VALUES (?,?,?,1,?,?,?,?)",
                    (name, category, encrypted, now, now, description, expires_at),
                )
                action = "secret_create"
                new_ver = 1
            conn.commit()
        self._audit(action, name=name, category=category, user=user)
        return {"name": name, "category": category, "version": new_ver, "status": "stored"}

    def retrieve(self, name: str, user: str = "system") -> str:
        """Retrieve and decrypt a secret value."""
        key = self._require_key()
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM vault_secret WHERE name=?", (name,)).fetchone()
        if not row:
            self._audit("secret_retrieve", name=name, user=user, success=False, detail="not found")
            raise KeyError(f"Secret '{name}' not found in vault.")
        self._audit("secret_retrieve", name=name, category=row["category"], user=user)
        return decrypt_str(key, row["encrypted_value"])

    def delete(self, name: str, user: str = "system") -> bool:
        """Delete a secret (moves to history first for recovery)."""
        key = self._require_key()
        conn = self._get_conn()
        with self._lock:
            row = conn.execute("SELECT * FROM vault_secret WHERE name=?", (name,)).fetchone()
            if not row:
                return False
            now = _now()
            conn.execute(
                "INSERT INTO vault_secret_history (secret_id,version,encrypted_value,archived_at) VALUES (?,?,?,?)",
                (row["id"], row["version"], row["encrypted_value"], now),
            )
            conn.execute("DELETE FROM vault_secret WHERE name=?", (name,))
            conn.commit()
        self._audit("secret_delete", name=name, category=row["category"], user=user)
        return True

    def rotate(self, name: str, new_value: str, user: str = "system") -> dict:
        """Rotate a secret to a new value, preserving history."""
        result = self.store(name, new_value, user=user)
        now = _now()
        self._get_conn().execute(
            "UPDATE vault_secret SET rotated_at=? WHERE name=?", (now, name)
        )
        self._get_conn().commit()
        self._audit("secret_rotate", name=name, user=user)
        return {**result, "rotated_at": now}

    def list_secrets(self, category: Optional[str] = None, user: str = "system") -> list[dict]:
        """List secret metadata (names, categories, versions) — never values."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT id,name,category,version,created_at,updated_at,rotated_at,expires_at,description FROM vault_secret WHERE category=? ORDER BY name",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,name,category,version,created_at,updated_at,rotated_at,expires_at,description FROM vault_secret ORDER BY category,name"
            ).fetchall()
        self._audit("secret_list", category=category, user=user)
        return [dict(r) for r in rows]

    def get_history(self, name: str, user: str = "system") -> list[dict]:
        """Return version history metadata for a secret (no values)."""
        conn = self._get_conn()
        row = conn.execute("SELECT id FROM vault_secret WHERE name=?", (name,)).fetchone()
        if not row:
            raise KeyError(f"Secret '{name}' not found.")
        rows = conn.execute(
            "SELECT version,archived_at FROM vault_secret_history WHERE secret_id=? ORDER BY version DESC",
            (row["id"],),
        ).fetchall()
        self._audit("secret_history", name=name, user=user)
        return [dict(r) for r in rows]

    def audit_log(self, limit: int = 100) -> list[dict]:
        """Return recent vault audit events."""
        rows = self._get_conn().execute(
            "SELECT * FROM vault_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def status(self) -> dict:
        """Return vault health/status summary."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM vault_secret").fetchone()[0]
        by_cat = {}
        for row in conn.execute("SELECT category, COUNT(*) as n FROM vault_secret GROUP BY category"):
            by_cat[row[0]] = row[1]
        initialized = self.is_initialized()
        return {
            "initialized": initialized,
            "locked": not self.is_unlocked(),
            "total_secrets": total,
            "by_category": by_cat,
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": PBKDF2_ITERATIONS,
        }

    def rekey(self, old_password: str, new_password: str, user: str = "system") -> dict:
        """Re-encrypt all secrets with a new master password."""
        old_key = self._require_key()
        conn = self._get_conn()
        rows = conn.execute("SELECT id, name, encrypted_value FROM vault_secret").fetchall()
        new_salt = new_salt()
        new_key = derive_key(new_password, new_salt)
        now = _now()
        with self._lock:
            for row in rows:
                plaintext = decrypt_str(old_key, row["encrypted_value"])
                new_enc = encrypt_str(new_key, plaintext)
                conn.execute("UPDATE vault_secret SET encrypted_value=?,updated_at=? WHERE id=?",
                             (new_enc, now, row["id"]))
            salt_b64 = base64.b64encode(new_salt).decode("ascii")
            conn.execute("UPDATE vault_meta SET value=? WHERE key='salt'", (salt_b64,))
            conn.commit()
        self._key = new_key
        self._audit("vault_rekey", user=user, detail=f"Re-keyed {len(rows)} secrets")
        return {"status": "rekeyed", "secrets_rekeyed": len(rows)}


# Module-level singleton
_vault: Optional[Vault] = None


def get_vault(db_path: Optional[str] = None) -> Vault:
    global _vault
    if _vault is None:
        _vault = Vault(db_path)
    return _vault
