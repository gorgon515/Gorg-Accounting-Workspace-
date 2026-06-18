"""Backup engine — encrypted, compressed, catalogued snapshots of HELIOS data.

Backs up the platform's SQLite stores (and any registered files) into a single
encrypted, gzip-compressed archive. Each archive is AES-256-GCM encrypted under a
key derived from a backup password (scrypt), checksummed (SHA-256), and recorded
in a catalog with size/checksum/type for verification and retention. Supports
full and incremental backups; incremental skips sources whose checksum is
unchanged since the last full backup.
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from security import crypto

_SCHEMA = """
CREATE TABLE IF NOT EXISTS backup (
  id INTEGER PRIMARY KEY AUTOINCREMENT, backup_id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
  created_at TEXT NOT NULL, archive_path TEXT NOT NULL, checksum TEXT NOT NULL,
  size_bytes INTEGER NOT NULL, source_count INTEGER NOT NULL, salt TEXT NOT NULL,
  manifest TEXT NOT NULL, note TEXT);
"""


# One-byte type tag prepended to each member before compression, so restore knows
# whether a member is a SQLite dump ("S") or opaque bytes ("B").
_TYPE_TAGS = {"sqlite": b"S", "bytes": b"B"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


class BackupError(RuntimeError):
    pass


class BackupEngine:
    """Manages backup sources, encrypted archive creation, catalog, and retention.

    A "source" is a named blob of bytes to protect. Register SQLite databases with
    `add_db_source` (snapshotted consistently) or arbitrary bytes with `add_source`.
    """

    def __init__(self, catalog_path: Optional[str] = None, archive_dir: Optional[str] = None):
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
        self.catalog_path = catalog_path or os.environ.get("HELIOS_BACKUP_DB") or os.path.join(base, "backup_catalog.db")
        self.archive_dir = archive_dir or os.environ.get("HELIOS_BACKUP_DIR") or os.path.join(base, "backups")
        os.makedirs(self.archive_dir, exist_ok=True)
        if self.catalog_path != ":memory:":
            os.makedirs(os.path.dirname(self.catalog_path), exist_ok=True)
        self.conn = sqlite3.connect(self.catalog_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self._sources: dict[str, dict] = {}

    # ---- source registration ----
    def add_db_source(self, name: str, db_path: str) -> None:
        self._sources[name] = {"type": "sqlite", "path": db_path}

    def add_source(self, name: str, data: bytes) -> None:
        self._sources[name] = {"type": "bytes", "data": data}

    def _read_source(self, spec: dict) -> bytes:
        if spec["type"] == "bytes":
            return spec["data"]
        path = spec["path"]
        if not os.path.exists(path):
            return b""
        # Consistent snapshot via SQLite's backup API into an in-memory db, dumped to bytes.
        src = sqlite3.connect(path)
        try:
            buf = sqlite3.connect(":memory:")
            src.backup(buf)
            dump = "\n".join(buf.iterdump())
            buf.close()
            return dump.encode("utf-8")
        finally:
            src.close()

    # ---- backup creation ----
    def create_backup(self, password: str, *, kind: str = "full", note: str = "") -> dict:
        if kind not in ("full", "incremental"):
            raise BackupError("kind must be 'full' or 'incremental'")
        if not self._sources:
            raise BackupError("no sources registered")

        prior = self._last_full_manifest() if kind == "incremental" else {}
        members: dict[str, str] = {}        # name -> base64(encrypted member)
        member_meta: dict[str, dict] = {}   # name -> {checksum, size, skipped}
        salt = crypto.new_salt()
        key = crypto.derive_key(password, salt)

        for name, spec in sorted(self._sources.items()):
            raw = self._read_source(spec)
            checksum = crypto.sha256(raw)
            if kind == "incremental" and prior.get(name, {}).get("checksum") == checksum:
                member_meta[name] = {"checksum": checksum, "size": len(raw), "type": spec["type"], "skipped": True}
                continue
            tagged = _TYPE_TAGS[spec["type"]] + raw
            members[name] = crypto.encrypt(key, gzip.compress(tagged), aad=name.encode())
            member_meta[name] = {"checksum": checksum, "size": len(raw), "type": spec["type"], "skipped": False}

        backup_id = f"{kind}-{_stamp()}"
        archive_obj = {"backup_id": backup_id, "kind": kind, "created_at": _now(), "members": members}
        archive_bytes = json.dumps(archive_obj).encode("utf-8")
        archive_path = os.path.join(self.archive_dir, backup_id + ".helios-backup")
        with open(archive_path, "wb") as f:
            f.write(archive_bytes)
        checksum = crypto.sha256(archive_bytes)
        manifest = {"members": member_meta}

        with self._lock:
            self.conn.execute(
                "INSERT INTO backup (backup_id,kind,created_at,archive_path,checksum,size_bytes,"
                "source_count,salt,manifest,note) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (backup_id, kind, archive_obj["created_at"], archive_path, checksum, len(archive_bytes),
                 len(self._sources), __import__("base64").b64encode(salt).decode(),
                 json.dumps(manifest), note))
            self.conn.commit()
        return {"backup_id": backup_id, "kind": kind, "archive_path": archive_path,
                "checksum": checksum, "size_bytes": len(archive_bytes),
                "members_written": len(members), "members_total": len(self._sources)}

    def _last_full_manifest(self) -> dict:
        row = self.conn.execute(
            "SELECT manifest FROM backup WHERE kind='full' ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row["manifest"])["members"] if row else {}

    # ---- catalog / verification / retention ----
    def list_backups(self, limit: int = 100) -> list[dict]:
        return [{"backup_id": r["backup_id"], "kind": r["kind"], "created_at": r["created_at"],
                 "size_bytes": r["size_bytes"], "checksum": r["checksum"], "note": r["note"]}
                for r in self.conn.execute(
                    "SELECT * FROM backup ORDER BY id DESC LIMIT ?", (limit,))]

    def get_record(self, backup_id: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM backup WHERE backup_id=?", (backup_id,)).fetchone()
        return dict(r) if r else None

    def verify(self, backup_id: str) -> dict:
        """Confirm the archive exists and its bytes still match the catalog checksum."""
        rec = self.get_record(backup_id)
        if not rec:
            return {"backup_id": backup_id, "valid": False, "reason": "not found"}
        if not os.path.exists(rec["archive_path"]):
            return {"backup_id": backup_id, "valid": False, "reason": "archive missing"}
        actual = crypto.sha256_file(rec["archive_path"])
        ok = actual == rec["checksum"]
        return {"backup_id": backup_id, "valid": ok,
                "reason": "ok" if ok else "checksum mismatch",
                "expected": rec["checksum"], "actual": actual}

    def apply_retention(self, keep: int) -> dict:
        """Keep the newest `keep` backups; delete older archives + catalog rows."""
        if keep < 1:
            raise BackupError("keep must be >= 1")
        rows = self.conn.execute("SELECT id, backup_id, archive_path FROM backup ORDER BY id DESC").fetchall()
        removed = []
        with self._lock:
            for r in rows[keep:]:
                try:
                    if os.path.exists(r["archive_path"]):
                        os.remove(r["archive_path"])
                except OSError:
                    pass
                self.conn.execute("DELETE FROM backup WHERE id=?", (r["id"],))
                removed.append(r["backup_id"])
            self.conn.commit()
        return {"removed": removed, "kept": min(keep, len(rows))}

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT kind, COUNT(*) n, COALESCE(SUM(size_bytes),0) s FROM backup GROUP BY kind")
        by_kind = {r["kind"]: {"count": r["n"], "bytes": r["s"]} for r in rows}
        total = self.conn.execute("SELECT COUNT(*) n, COALESCE(SUM(size_bytes),0) s FROM backup").fetchone()
        latest = self.conn.execute("SELECT backup_id, created_at FROM backup ORDER BY id DESC LIMIT 1").fetchone()
        return {"total": total["n"], "total_bytes": total["s"], "by_kind": by_kind,
                "latest": dict(latest) if latest else None, "archive_dir": self.archive_dir}

    def close(self):
        self.conn.close()
