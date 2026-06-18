"""Restore engine — decrypt, validate, and rebuild data from backup archives.

Reads an encrypted archive produced by the backup engine, derives the key from
the backup password (scrypt + stored salt), decrypts and decompresses each
member, and reconstructs SQLite databases. Supports full restore (all members),
selective restore (named members only), and point-in-time restore (the newest
backup at or before a timestamp, layering the last full backup with later
incrementals). Validates the archive checksum before touching anything.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import sqlite3
from typing import Iterable, Optional

from security import crypto


class RestoreError(RuntimeError):
    pass


class RestoreEngine:
    def __init__(self, backup_engine):
        self.backups = backup_engine

    def _load_archive(self, record: dict, password: str) -> dict:
        path = record["archive_path"]
        if not os.path.exists(path):
            raise RestoreError(f"archive missing: {path}")
        if crypto.sha256_file(path) != record["checksum"]:
            raise RestoreError("archive checksum mismatch — refusing to restore corrupt backup")
        with open(path, "rb") as f:
            archive = json.loads(f.read().decode("utf-8"))
        salt = base64.b64decode(record["salt"])
        key = crypto.derive_key(password, salt)
        return {"key": key, "archive": archive}

    def _decrypt_members(self, archive: dict, key: bytes, names: Optional[Iterable[str]]) -> dict:
        """Returns name -> {"type": "sqlite"|"bytes", "data": bytes}."""
        want = set(names) if names is not None else None
        out: dict[str, dict] = {}
        for name, blob in archive["members"].items():
            if want is not None and name not in want:
                continue
            try:
                tagged = gzip.decompress(crypto.decrypt(key, blob, aad=name.encode()))
            except crypto.DecryptionError as exc:
                raise RestoreError(f"decryption failed for '{name}' — wrong password or tampered") from exc
            kind = "sqlite" if tagged[:1] == b"S" else "bytes"
            out[name] = {"type": kind, "data": tagged[1:]}
        return out

    def _write_member(self, member: dict, dest_path: str) -> dict:
        """Materialise a decrypted member to disk by its type."""
        if member["type"] == "sqlite":
            return self.restore_to_sqlite(member["data"], dest_path)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(member["data"])
        return {"dest": dest_path, "tables": 0, "bytes": len(member["data"])}

    def inspect(self, backup_id: str, password: str) -> dict:
        """Decrypt and report what a backup contains, without writing anything."""
        rec = self.backups.get_record(backup_id)
        if not rec:
            raise RestoreError(f"no such backup: {backup_id}")
        loaded = self._load_archive(rec, password)
        members = self._decrypt_members(loaded["archive"], loaded["key"], None)
        return {"backup_id": backup_id, "kind": rec["kind"], "created_at": rec["created_at"],
                "members": {n: len(m["data"]) for n, m in members.items()}}

    def restore_to_sqlite(self, data: bytes, dest_path: str) -> dict:
        """Rebuild a SQLite DB from a backup member (iterdump SQL or empty)."""
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        conn = sqlite3.connect(dest_path)
        try:
            if data:
                conn.executescript(data.decode("utf-8"))
                conn.commit()
            n = conn.execute("SELECT COUNT(*) c FROM sqlite_master WHERE type='table'").fetchone()[0]
        finally:
            conn.close()
        return {"dest": dest_path, "tables": n, "bytes": len(data)}

    def restore(self, backup_id: str, password: str, targets: dict, *,
                members: Optional[Iterable[str]] = None) -> dict:
        """Full or selective restore. `targets` maps member name -> destination path.

        `members=None` restores all members present in the archive; otherwise only
        the named ones. Members without a target path are decrypted but skipped.
        """
        rec = self.backups.get_record(backup_id)
        if not rec:
            raise RestoreError(f"no such backup: {backup_id}")
        loaded = self._load_archive(rec, password)
        decrypted = self._decrypt_members(loaded["archive"], loaded["key"], members)
        results = {}
        for name, member in decrypted.items():
            dest = targets.get(name)
            if not dest:
                continue
            results[name] = self._write_member(member, dest)
        return {"backup_id": backup_id, "restored": results, "restored_count": len(results)}

    def restore_point_in_time(self, password: str, as_of: str, targets: dict) -> dict:
        """Restore the data as it stood at-or-before `as_of` (ISO timestamp).

        Picks the newest full backup at/before `as_of`, then layers every later
        incremental (up to `as_of`) on top so changed members reflect the latest
        version within the window.
        """
        records = sorted(self.backups.list_backups(limit=10_000), key=lambda r: r["created_at"])
        eligible = [r for r in records if r["created_at"] <= as_of]
        fulls = [r for r in eligible if r["kind"] == "full"]
        if not fulls:
            raise RestoreError(f"no full backup at or before {as_of}")
        base = fulls[-1]
        chain = [base] + [r for r in eligible if r["kind"] == "incremental" and r["created_at"] > base["created_at"]]
        merged: dict[str, dict] = {}
        for r in chain:
            rec = self.backups.get_record(r["backup_id"])
            loaded = self._load_archive(rec, password)
            merged.update(self._decrypt_members(loaded["archive"], loaded["key"], None))
        results = {}
        for name, member in merged.items():
            dest = targets.get(name)
            if dest:
                results[name] = self._write_member(member, dest)
        return {"as_of": as_of, "base_backup": base["backup_id"],
                "layers": [r["backup_id"] for r in chain], "restored": results,
                "restored_count": len(results)}

    def validate(self, backup_id: str, password: str) -> dict:
        """Verify the archive checksum and that every member decrypts cleanly."""
        rec = self.backups.get_record(backup_id)
        if not rec:
            return {"backup_id": backup_id, "valid": False, "reason": "not found"}
        try:
            loaded = self._load_archive(rec, password)
            members = self._decrypt_members(loaded["archive"], loaded["key"], None)
        except RestoreError as exc:
            return {"backup_id": backup_id, "valid": False, "reason": str(exc)}
        return {"backup_id": backup_id, "valid": True, "members": len(members),
                "member_bytes": {n: len(m["data"]) for n, m in members.items()}}
