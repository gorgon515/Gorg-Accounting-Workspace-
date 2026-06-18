"""Multi-device sync engine — delta sync with versioning + conflict resolution.

A hub-style synchroniser. Devices register, then push and pull deltas keyed by a
logical record key. The hub assigns a monotonic global version (a Lamport-style
server clock) to every accepted change, so devices pull only what changed since
their last seen version. Payloads are AES-256-GCM encrypted under a shared sync
key — the hub stores ciphertext, so transport and at-rest data are protected.

Conflict handling: a push carries the `base_version` the device last saw for a
key. If the key has since advanced (a different device wrote it), the conflict is
recorded and resolved last-write-wins (the newest push becomes current). Every
operation is audited.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from security import crypto

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_meta (id INTEGER PRIMARY KEY CHECK (id=1), version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS device (
  device_id TEXT PRIMARY KEY, name TEXT, registered_at TEXT, last_seen TEXT, last_pull_version INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS record (
  key TEXT PRIMARY KEY, version INTEGER NOT NULL, device_id TEXT, ts TEXT NOT NULL,
  blob TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS conflict (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, key TEXT, base_version INTEGER,
  current_version INTEGER, winner_device TEXT, loser_device TEXT, resolution TEXT);
CREATE TABLE IF NOT EXISTS sync_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, device_id TEXT, action TEXT, detail TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyncEngine:
    def __init__(self, key: bytes, path: Optional[str] = None):
        if not key or len(key) != crypto.KEY_BYTES:
            raise ValueError(f"sync key must be {crypto.KEY_BYTES} bytes")
        self._key = key
        self.path = path or os.environ.get("HELIOS_SYNC_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "sync.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.execute("INSERT OR IGNORE INTO sync_meta (id, version) VALUES (1, 0)")
        self.conn.commit()

    # ---- version clock ----
    def _bump(self) -> int:
        self.conn.execute("UPDATE sync_meta SET version = version + 1 WHERE id=1")
        return self.conn.execute("SELECT version FROM sync_meta WHERE id=1").fetchone()["version"]

    def version(self) -> int:
        return self.conn.execute("SELECT version FROM sync_meta WHERE id=1").fetchone()["version"]

    # ---- devices ----
    def register_device(self, name: str) -> dict:
        device_id = "dev_" + secrets.token_hex(8)
        with self._lock:
            self.conn.execute(
                "INSERT INTO device (device_id,name,registered_at,last_seen,last_pull_version) VALUES (?,?,?,?,0)",
                (device_id, name, _now(), _now()))
            self.conn.commit()
        self._audit(device_id, "register", name)
        return {"device_id": device_id, "name": name, "server_version": self.version()}

    def devices(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT device_id,name,registered_at,last_seen,last_pull_version FROM device ORDER BY registered_at")]

    def _touch(self, device_id: str):
        self.conn.execute("UPDATE device SET last_seen=? WHERE device_id=?", (_now(), device_id))

    # ---- push (delta in) ----
    def push(self, device_id: str, changes: list[dict]) -> dict:
        """Apply a device's changes. Each change: {key, value, base_version?, deleted?}.

        Returns the new server version, applied keys, and any conflicts recorded.
        """
        if not self.conn.execute("SELECT 1 FROM device WHERE device_id=?", (device_id,)).fetchone():
            raise ValueError(f"unknown device: {device_id}")
        applied, conflicts = [], []
        with self._lock:
            for ch in changes:
                key = ch["key"]
                base_version = int(ch.get("base_version", 0))
                deleted = bool(ch.get("deleted", False))
                cur = self.conn.execute("SELECT version, device_id FROM record WHERE key=?", (key,)).fetchone()
                if cur and cur["version"] > base_version and cur["device_id"] != device_id:
                    # Concurrent modification → record conflict, resolve last-write-wins.
                    self.conn.execute(
                        "INSERT INTO conflict (ts,key,base_version,current_version,winner_device,loser_device,resolution) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (_now(), key, base_version, cur["version"], device_id, cur["device_id"], "last-write-wins"))
                    conflicts.append({"key": key, "base_version": base_version,
                                      "current_version": cur["version"], "resolution": "last-write-wins"})
                new_version = self._bump()
                blob = crypto.encrypt_json(self._key, ch.get("value"), aad=key.encode())
                self.conn.execute(
                    "INSERT INTO record (key,version,device_id,ts,blob,deleted) VALUES (?,?,?,?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET version=excluded.version, device_id=excluded.device_id, "
                    "ts=excluded.ts, blob=excluded.blob, deleted=excluded.deleted",
                    (key, new_version, device_id, _now(), blob, 1 if deleted else 0))
                applied.append({"key": key, "version": new_version})
            self._touch(device_id)
            self.conn.commit()
        self._audit(device_id, "push", f"{len(applied)} changes, {len(conflicts)} conflicts")
        return {"server_version": self.version(), "applied": applied, "conflicts": conflicts}

    # ---- pull (delta out) ----
    def pull(self, device_id: str, since: Optional[int] = None) -> dict:
        """Return records changed after `since` (defaults to the device's last pull)."""
        row = self.conn.execute("SELECT last_pull_version FROM device WHERE device_id=?", (device_id,)).fetchone()
        if not row:
            raise ValueError(f"unknown device: {device_id}")
        since = row["last_pull_version"] if since is None else since
        changes = []
        for r in self.conn.execute(
                "SELECT key,version,device_id,ts,blob,deleted FROM record WHERE version>? ORDER BY version", (since,)):
            changes.append({"key": r["key"], "version": r["version"], "origin": r["device_id"],
                            "ts": r["ts"], "deleted": bool(r["deleted"]),
                            "value": crypto.decrypt_json(self._key, r["blob"], aad=r["key"].encode())})
        server_version = self.version()
        with self._lock:
            self.conn.execute("UPDATE device SET last_pull_version=?, last_seen=? WHERE device_id=?",
                              (server_version, _now(), device_id))
            self.conn.commit()
        self._audit(device_id, "pull", f"{len(changes)} changes since {since}")
        return {"server_version": server_version, "since": since, "changes": changes}

    # ---- introspection ----
    def conflicts(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT ts,key,base_version,current_version,winner_device,loser_device,resolution "
            "FROM conflict ORDER BY id DESC LIMIT ?", (limit,))]

    def _audit(self, device_id, action, detail=""):
        self.conn.execute("INSERT INTO sync_audit (ts,device_id,action,detail) VALUES (?,?,?,?)",
                          (_now(), device_id, action, detail))
        self.conn.commit()

    def audit_log(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT ts,device_id,action,detail FROM sync_audit ORDER BY id DESC LIMIT ?", (limit,))]

    def status(self) -> dict:
        return {"server_version": self.version(),
                "devices": self.conn.execute("SELECT COUNT(*) n FROM device").fetchone()["n"],
                "records": self.conn.execute("SELECT COUNT(*) n FROM record").fetchone()["n"],
                "conflicts": self.conn.execute("SELECT COUNT(*) n FROM conflict").fetchone()["n"],
                "algorithm": "AES-256-GCM"}

    def close(self):
        self.conn.close()
