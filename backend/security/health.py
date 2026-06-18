"""System health monitoring — lightweight, dependency-free checks.

Reports the reachability and size of each HELIOS data store, process/runtime
facts, and a rolled-up status. Used by the Security Center and the /health
surface so the HUD can show live system health.
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone

_START = time.time()


def _db_check(path: str) -> dict:
    if not path or path == ":memory:":
        return {"path": path or None, "exists": False, "ok": True, "size_bytes": 0, "tables": 0}
    if not os.path.exists(path):
        return {"path": path, "exists": False, "ok": True, "size_bytes": 0, "tables": 0}
    try:
        size = os.path.getsize(path)
        conn = sqlite3.connect(path)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        finally:
            conn.close()
        return {"path": path, "exists": True, "ok": integrity == "ok",
                "integrity": integrity, "size_bytes": size, "tables": tables}
    except sqlite3.Error as exc:
        return {"path": path, "exists": True, "ok": False, "error": str(exc), "size_bytes": 0, "tables": 0}


_STORES = {
    "accounting": "HELIOS_ACCT_DB",
    "vault": "HELIOS_VAULT_DB",
    "compliance": "HELIOS_COMPLIANCE_DB",
    "encrypted_store": "HELIOS_ENCSTORE_DB",
    "sync": "HELIOS_SYNC_DB",
    "backup_catalog": "HELIOS_BACKUP_DB",
    "execution": "HELIOS_EXEC_DB",
    "intel": "HELIOS_INTEL_DB",
}


def _default_path(env_key: str) -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
    name = {"HELIOS_ACCT_DB": "accounting.db", "HELIOS_VAULT_DB": "vault.db",
            "HELIOS_COMPLIANCE_DB": "compliance.db", "HELIOS_ENCSTORE_DB": "encrypted_store.db",
            "HELIOS_SYNC_DB": "sync.db", "HELIOS_BACKUP_DB": "backup_catalog.db",
            "HELIOS_EXEC_DB": "execution.db", "HELIOS_INTEL_DB": "intel.db"}.get(env_key, env_key.lower())
    return os.path.join(base, name)


def store_health() -> dict:
    out = {}
    for name, env_key in _STORES.items():
        path = os.environ.get(env_key) or _default_path(env_key)
        out[name] = _db_check(path)
    return out


def system_health() -> dict:
    stores = store_health()
    all_ok = all(s["ok"] for s in stores.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "uptime_seconds": round(time.time() - _START, 1),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "stores": stores,
        "total_data_bytes": sum(s["size_bytes"] for s in stores.values()),
    }
