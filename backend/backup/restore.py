"""RestoreEngine — validates and restores from encrypted HELIOS backups."""
from __future__ import annotations

import io
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from typing import Optional

from security.encryption.aes import decrypt, sha256_hex
from .catalog import BackupCatalog, get_catalog

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")


class RestoreEngine:
    def __init__(self, backup_dir: Optional[str] = None, key: Optional[bytes] = None):
        self._backup_dir = backup_dir or os.environ.get("HELIOS_BACKUP_DIR") or os.path.join(BASE_DIR, "backups")
        self._key: Optional[bytes] = key
        self._catalog: BackupCatalog = get_catalog()

    def set_key(self, key: bytes) -> None:
        self._key = key

    def _require_key(self) -> bytes:
        if self._key is None:
            raise PermissionError("Decryption key not set. Call set_key() first.")
        return self._key

    def _decrypt_backup(self, file_path: str) -> bytes:
        key = self._require_key()
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        return decrypt(key, encrypted_data)

    def validate(self, backup_id: str) -> dict:
        issues = []
        try:
            record = self._catalog.get(backup_id)
        except KeyError:
            return {"valid": False, "issues": ["Backup record not found"], "size_bytes": 0, "components": []}
        file_path = record["file_path"]
        if not os.path.exists(file_path):
            return {"valid": False, "issues": ["Backup file missing from disk"], "size_bytes": 0,
                    "components": record["components"]}
        size_bytes = os.path.getsize(file_path)
        try:
            tar_gz_data = self._decrypt_backup(file_path)
        except Exception as e:
            return {"valid": False, "issues": [f"Decryption failed: {e}"], "size_bytes": size_bytes,
                    "components": record["components"]}
        computed_hash = sha256_hex(tar_gz_data)
        if record.get("verification_hash") and computed_hash != record["verification_hash"]:
            issues.append("Hash mismatch — backup may be corrupted")
        try:
            buf = io.BytesIO(tar_gz_data)
            with tarfile.open(fileobj=buf, mode="r:gz") as tar:
                members = tar.getmembers()
        except Exception as e:
            issues.append(f"Invalid tar.gz archive: {e}")
        valid = len(issues) == 0
        return {
            "valid": valid,
            "issues": issues,
            "size_bytes": size_bytes,
            "components": record["components"],
            "file_count": len(members) if valid else 0,
        }

    def _extract_backup(self, backup_id: str, target_dir: str,
                        filter_components: Optional[list[str]] = None, dry_run: bool = False) -> dict:
        validation = self.validate(backup_id)
        if not validation["valid"]:
            return {"success": False, "errors": validation["issues"], "dry_run": dry_run}
        record = self._catalog.get(backup_id)
        tar_gz_data = self._decrypt_backup(record["file_path"])
        buf = io.BytesIO(tar_gz_data)
        restored_files = []
        skipped_files = []
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                # Filter by component if specified
                if filter_components:
                    match = any(comp in member.name for comp in filter_components)
                    if not match:
                        skipped_files.append(member.name)
                        continue
                restored_files.append(member.name)
                if not dry_run:
                    member.name = member.name.lstrip("/")
                    out_path = os.path.join(target_dir, member.name)
                    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else target_dir, exist_ok=True)
                    if member.isfile():
                        f = tar.extractfile(member)
                        if f:
                            with open(out_path, "wb") as out:
                                out.write(f.read())
        return {
            "success": True,
            "dry_run": dry_run,
            "backup_id": backup_id,
            "restored_files": restored_files,
            "skipped_files": skipped_files,
            "target_dir": target_dir,
        }

    def restore_full(self, backup_id: str, target_dir: str = None, dry_run: bool = False) -> dict:
        if target_dir is None:
            target_dir = BASE_DIR
        return self._extract_backup(backup_id, target_dir, dry_run=dry_run)

    def restore_selective(self, backup_id: str, components: list[str],
                          target_dir: str = None, dry_run: bool = False) -> dict:
        if target_dir is None:
            target_dir = BASE_DIR
        return self._extract_backup(backup_id, target_dir, filter_components=components, dry_run=dry_run)

    def restore_point_in_time(self, before_timestamp: str, component: str,
                               target_dir: str = None) -> dict:
        if target_dir is None:
            target_dir = BASE_DIR
        # Find closest backup before timestamp that contains the component
        all_backups = self._catalog.list(status="complete")
        candidates = []
        for backup in all_backups:
            if backup["created_at"] <= before_timestamp:
                if component == "all" or component in backup["components"] or "all" in backup["components"]:
                    candidates.append(backup)
        if not candidates:
            return {"success": False, "errors": [f"No backup found before {before_timestamp} for component {component}"]}
        # Pick the most recent one before the timestamp
        closest = max(candidates, key=lambda b: b["created_at"])
        return self.restore_selective(closest["backup_id"], [component], target_dir=target_dir)

    def list_restore_points(self, component: Optional[str] = None) -> list[dict]:
        all_backups = self._catalog.list(status="complete")
        if component and component != "all":
            return [b for b in all_backups if component in b["components"] or "all" in b["components"]]
        return all_backups


_restore_engine: Optional[RestoreEngine] = None

def get_restore_engine(key: Optional[bytes] = None) -> RestoreEngine:
    global _restore_engine
    if _restore_engine is None:
        _restore_engine = RestoreEngine(key=key)
    elif key is not None:
        _restore_engine.set_key(key)
    return _restore_engine
