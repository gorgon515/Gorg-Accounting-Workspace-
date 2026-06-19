"""BackupEngine — creates encrypted, compressed backups of HELIOS data."""
from __future__ import annotations

import gzip
import io
import os
import shutil
import tarfile
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from security.encryption.aes import encrypt, decrypt, sha256_hex
from .catalog import BackupCatalog, get_catalog

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")

COMPONENT_PATHS = {
    "accounting": [os.path.join(BASE_DIR, "accounting.db")],
    "vault": [os.path.join(BASE_DIR, "vault", "vault.db")],
    "documents": [os.path.join(BASE_DIR, "enc_docs")],
    "memory": [os.path.join(BASE_DIR, "enc_memory")],
    "compliance": [os.path.join(BASE_DIR, "compliance.db")],
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_all_paths() -> list[str]:
    """Get all paths that make up the 'all' component."""
    paths = []
    for component_paths in COMPONENT_PATHS.values():
        paths.extend(component_paths)
    return paths

def _resolve_components(components: list[str]) -> list[str]:
    """Expand 'all' to all component names."""
    if "all" in components:
        return list(COMPONENT_PATHS.keys())
    return [c for c in components if c in COMPONENT_PATHS]


class BackupEngine:
    def __init__(self, backup_dir: Optional[str] = None, key: Optional[bytes] = None):
        self._backup_dir = backup_dir or os.environ.get("HELIOS_BACKUP_DIR") or os.path.join(BASE_DIR, "backups")
        os.makedirs(self._backup_dir, exist_ok=True)
        self._key: Optional[bytes] = key
        self._catalog: BackupCatalog = get_catalog()
        self._lock = threading.Lock()

    def set_key(self, key: bytes) -> None:
        self._key = key

    def _require_key(self) -> bytes:
        if self._key is None:
            raise PermissionError("Encryption key not set. Call set_key() first.")
        return self._key

    def _create_tar_gz(self, paths: list[str]) -> bytes:
        """Create an in-memory gzip-compressed tar archive from a list of paths."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path in paths:
                if os.path.exists(path):
                    arcname = os.path.relpath(path, BASE_DIR)
                    tar.add(path, arcname=arcname)
        return buf.getvalue()

    def _save_encrypted_backup(self, backup_id: str, tar_gz_data: bytes) -> str:
        """Encrypt and save the tar.gz data. Returns the file path."""
        key = self._require_key()
        encrypted_blob = encrypt(key, tar_gz_data)
        file_path = os.path.join(self._backup_dir, f"{backup_id}.tar.gz.enc")
        with open(file_path, "wb") as f:
            f.write(encrypted_blob)
        return file_path

    def _do_backup(self, backup_id: str, backup_type: str, components: list[str],
                   paths: list[str], notes: str = "") -> dict:
        self._catalog.register(backup_id, backup_type, components,
                               os.path.join(self._backup_dir, f"{backup_id}.tar.gz.enc"))
        try:
            tar_gz_data = self._create_tar_gz(paths)
            compressed_size = len(tar_gz_data)
            file_path = self._save_encrypted_backup(backup_id, tar_gz_data)
            total_size = os.path.getsize(file_path)
            verification_hash = sha256_hex(tar_gz_data)
            result = self._catalog.complete(backup_id, total_size, compressed_size, verification_hash)
            if notes:
                self._catalog._get_conn().execute(
                    "UPDATE backup_record SET notes=? WHERE backup_id=?", (notes, backup_id)
                )
                self._catalog._get_conn().commit()
            return {**result, "status": "complete", "backup_id": backup_id,
                    "file_path": file_path, "components": components}
        except Exception as e:
            self._catalog.fail(backup_id, str(e))
            raise

    def create_full(self, components: list = None, notes: str = "") -> dict:
        if components is None:
            components = ["all"]
        resolved = _resolve_components(components)
        paths = []
        for comp in resolved:
            paths.extend(COMPONENT_PATHS[comp])
        backup_id = f"full_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        return self._do_backup(backup_id, "full", resolved, paths, notes)

    def create_incremental(self, since_timestamp: str, components: list = None) -> dict:
        if components is None:
            components = ["all"]
        resolved = _resolve_components(components)
        # Collect only files modified after since_timestamp
        since_dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
        changed_paths = []
        for comp in resolved:
            for path in COMPONENT_PATHS[comp]:
                if os.path.isfile(path):
                    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                    if mtime > since_dt:
                        changed_paths.append(path)
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for fname in files:
                            fpath = os.path.join(root, fname)
                            mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
                            if mtime > since_dt:
                                changed_paths.append(fpath)
        backup_id = f"incr_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        return self._do_backup(backup_id, "incremental", resolved, changed_paths)

    def create_selective(self, component_list: list[str]) -> dict:
        resolved = _resolve_components(component_list)
        paths = []
        for comp in resolved:
            paths.extend(COMPONENT_PATHS[comp])
        backup_id = f"sel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        return self._do_backup(backup_id, "selective", resolved, paths)

    def verify(self, backup_id: str) -> dict:
        key = self._require_key()
        record = self._catalog.get(backup_id)
        file_path = record["file_path"]
        if not os.path.exists(file_path):
            self._catalog.mark_verified(backup_id, ok=False)
            return {"backup_id": backup_id, "valid": False, "error": "Backup file not found"}
        try:
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
            tar_gz_data = decrypt(key, encrypted_data)
            computed_hash = sha256_hex(tar_gz_data)
            hash_ok = computed_hash == record.get("verification_hash")
            # Verify it's a valid tar.gz
            buf = io.BytesIO(tar_gz_data)
            with tarfile.open(fileobj=buf, mode="r:gz") as tar:
                members = tar.getmembers()
            self._catalog.mark_verified(backup_id, ok=hash_ok)
            return {
                "backup_id": backup_id,
                "valid": hash_ok,
                "hash_matches": hash_ok,
                "file_count": len(members),
                "compressed_size": len(tar_gz_data),
            }
        except Exception as e:
            self._catalog.mark_verified(backup_id, ok=False)
            return {"backup_id": backup_id, "valid": False, "error": str(e)}

    def list_backups(self) -> list[dict]:
        return self._catalog.list()

    def cleanup_old(self, retention_days: int = 30) -> int:
        return self._catalog.delete_expired()


_engine: Optional[BackupEngine] = None

def get_backup_engine(key: Optional[bytes] = None) -> BackupEngine:
    global _engine
    if _engine is None:
        _engine = BackupEngine(key=key)
    elif key is not None:
        _engine.set_key(key)
    return _engine
