"""Security, Vault, Backup, Recovery & Sync API.

Surfaces the HELIOS security tier: the encrypted vault, encrypted memory/document
storage, immutable compliance log, agent permission matrix, data-integrity scans,
encrypted backups + restore + disaster recovery, multi-device sync, and system
health. The vault is the root of trust — encrypted-data and sync endpoints require
it to be unlocked.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Body, Query

from security import compliance as compliance_mod
from security import health, integrity, permissions
from security.service import SecurityService
from security.vault import VaultLocked
from backup.engine import BackupEngine
from backup.restore import RestoreEngine
from backup.recovery import RecoveryManager
from sync.engine import SyncEngine
from .accounting_platform_router import _conn as ACCT

router = APIRouter(tags=["security"])

_svc = SecurityService()
_backup = BackupEngine()
_restore = RestoreEngine(_backup)
_recovery = RecoveryManager(_backup, _restore)
_sync: dict = {"engine": None}


def _data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".data")


def _resolve(env_key: str, default_name: str) -> str:
    return os.environ.get(env_key) or os.path.join(_data_dir(), default_name)


def _register_backup_sources():
    """Register the live HELIOS stores as backup sources (idempotent)."""
    try:
        acct_path = ACCT.execute("PRAGMA database_list").fetchone()[2]
        if acct_path:
            _backup.add_db_source("accounting", acct_path)
    except Exception:  # pragma: no cover - defensive
        pass
    for name, env_key, default in (
        ("vault", "HELIOS_VAULT_DB", "vault.db"),
        ("compliance", "HELIOS_COMPLIANCE_DB", "compliance.db"),
        ("encrypted_store", "HELIOS_ENCSTORE_DB", "encrypted_store.db"),
        ("sync", "HELIOS_SYNC_DB", "sync.db"),
    ):
        _backup.add_db_source(name, _resolve(env_key, default))


_register_backup_sources()


def _sync_engine() -> SyncEngine:
    """Build (and cache) the sync engine using the vault's data key. Requires unlock."""
    if _sync["engine"] is None:
        _sync["engine"] = SyncEngine(_svc.data_key)  # raises VaultLocked if locked
    return _sync["engine"]


# ----------------------------- security / vault lifecycle -----------------------------
@router.get("/security/status")
def security_status():
    return _svc.status()


@router.post("/security/initialize")
def security_initialize(body: dict = Body(...)):
    return _svc.initialize(body["master_password"])


@router.post("/security/unlock")
def security_unlock(body: dict = Body(...)):
    out = _svc.unlock(body["master_password"])
    if not out.get("unlocked"):
        _sync["engine"] = None
    return out


@router.post("/security/lock")
def security_lock():
    _sync["engine"] = None
    return _svc.lock()


# ----------------------------- vault secrets -----------------------------
@router.get("/vault/secrets")
def vault_secrets():
    return {"secrets": _svc.vault.list_refs()}


@router.post("/vault/secret")
def vault_set_secret(body: dict = Body(...)):
    return _svc.vault.set_secret(body["ref"], body["value"],
                                 category=body.get("category", "general"),
                                 actor=body.get("actor", "user"))


@router.get("/vault/secret/{ref:path}")
def vault_get_secret(ref: str):
    value = _svc.vault.get_secret(ref)
    return {"ref": ref, "value": value, "found": value is not None}


@router.post("/vault/secret/{ref:path}/rotate")
def vault_rotate_secret(ref: str, body: dict = Body(...)):
    return _svc.vault.rotate_secret(ref, body["value"])


@router.delete("/vault/secret/{ref:path}")
def vault_delete_secret(ref: str):
    return _svc.vault.delete_secret(ref)


@router.post("/vault/rotate-master")
def vault_rotate_master(body: dict = Body(...)):
    return _svc.vault.rotate_master(body["old_password"], body["new_password"])


@router.get("/vault/access-log")
def vault_access_log(limit: int = 100):
    return {"access": _svc.vault.access_log(limit)}


# ----------------------------- encrypted memory / documents -----------------------------
@router.post("/security/memory")
def put_memory(body: dict = Body(...)):
    return _svc.put_memory(body["key"], body["value"], actor=body.get("actor", "user"))


@router.get("/security/memory/{key:path}")
def get_memory(key: str):
    return {"key": key, "value": _svc.get_memory(key)}


@router.post("/security/document")
def put_document(body: dict = Body(...)):
    return _svc.put_document(body["doc_id"], body["payload"], meta=body.get("meta", ""),
                             actor=body.get("actor", "user"))


@router.get("/security/document/{doc_id:path}")
def get_document(doc_id: str):
    return {"doc_id": doc_id, "value": _svc.get_document(doc_id)}


# ----------------------------- compliance -----------------------------
@router.get("/compliance/events")
def compliance_events(category: Optional[str] = None, limit: int = 100):
    return {"events": _svc.compliance.query(category, limit)}


@router.post("/compliance/record")
def compliance_record(body: dict = Body(...)):
    return _svc.compliance.record(body["category"], body["action"],
                                  actor=body.get("actor", "system"), detail=body.get("detail"))


@router.get("/compliance/verify")
def compliance_verify():
    return _svc.compliance.verify()


@router.get("/compliance/stats")
def compliance_stats():
    return _svc.compliance.stats()


# ----------------------------- permissions -----------------------------
@router.get("/security/permissions")
def permission_matrix():
    return {"matrix": permissions.MATRIX,
            "invariant": "no agent may approve or execute money/filing actions"}


@router.get("/security/permissions/{agent}")
def permission_for_agent(agent: str):
    return {"agent": agent, "permissions": permissions.perms(agent),
            "can_approve": permissions.can_approve(agent),
            "can_propose": permissions.can_propose(agent)}


# ----------------------------- data integrity -----------------------------
@router.get("/security/integrity/ledger")
def integrity_ledger():
    return integrity.ledger_integrity(ACCT)


@router.get("/security/integrity/audit")
def integrity_audit():
    return integrity.audit_verification(ACCT)


# ----------------------------- health -----------------------------
@router.get("/security/health")
def security_health():
    return health.system_health()


# ----------------------------- backup -----------------------------
@router.post("/backup/create")
def backup_create(body: dict = Body(...)):
    _register_backup_sources()
    return _backup.create_backup(body["password"], kind=body.get("kind", "full"),
                                 note=body.get("note", ""))


@router.get("/backup/list")
def backup_list(limit: int = 100):
    return {"backups": _backup.list_backups(limit)}


@router.get("/backup/stats")
def backup_stats():
    return _backup.stats()


@router.get("/backup/{backup_id}/verify")
def backup_verify(backup_id: str):
    return _backup.verify(backup_id)


@router.post("/backup/retention")
def backup_retention(body: dict = Body(...)):
    return _backup.apply_retention(int(body["keep"]))


# ----------------------------- restore -----------------------------
@router.post("/restore/validate")
def restore_validate(body: dict = Body(...)):
    return _restore.validate(body["backup_id"], body["password"])


@router.post("/restore/inspect")
def restore_inspect(body: dict = Body(...)):
    return _restore.inspect(body["backup_id"], body["password"])


@router.post("/restore/run")
def restore_run(body: dict = Body(...)):
    return _restore.restore(body["backup_id"], body["password"], body.get("targets", {}),
                            members=body.get("members"))


# ----------------------------- disaster recovery -----------------------------
@router.get("/recovery/points")
def recovery_points():
    return {"points": _recovery.recovery_points()}


@router.get("/recovery/plan")
def recovery_plan():
    return _recovery.recovery_plan()


@router.post("/recovery/simulate")
def recovery_simulate(body: dict = Body(...)):
    return _recovery.simulate_recovery(body["password"])


@router.post("/recovery/report")
def recovery_report(body: dict = Body(default={})):
    return _recovery.report(body.get("password"))


# ----------------------------- multi-device sync -----------------------------
@router.post("/sync/device")
def sync_register(body: dict = Body(...)):
    return _sync_engine().register_device(body["name"])


@router.get("/sync/devices")
def sync_devices():
    return {"devices": _sync_engine().devices()}


@router.post("/sync/push")
def sync_push(body: dict = Body(...)):
    return _sync_engine().push(body["device_id"], body["changes"])


@router.post("/sync/pull")
def sync_pull(body: dict = Body(...)):
    return _sync_engine().pull(body["device_id"], since=body.get("since"))


@router.get("/sync/conflicts")
def sync_conflicts(limit: int = 100):
    return {"conflicts": _sync_engine().conflicts(limit)}


@router.get("/sync/audit")
def sync_audit(limit: int = 100):
    return {"audit": _sync_engine().audit_log(limit)}


@router.get("/sync/status")
def sync_status():
    return _sync_engine().status()
