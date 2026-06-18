"""HELIOS Backup & Recovery API."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupFullRequest(BaseModel):
    password: str
    notes: str = ""

class BackupIncrementalRequest(BaseModel):
    password: str
    since: Optional[str] = None

class BackupSelectiveRequest(BaseModel):
    password: str
    components: list[str]

class RestoreFullRequest(BaseModel):
    backup_id: str
    password: str
    dry_run: bool = False

class RestoreSelectiveRequest(BaseModel):
    backup_id: str
    password: str
    components: list[str]
    dry_run: bool = False

class RestorePitRequest(BaseModel):
    before_timestamp: str
    component: str
    password: str


def _key_from_password(password: str) -> bytes:
    """Derive an encryption key from a password for backup operations."""
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"helios-backup-salt", 600_000, dklen=32)


def _engine(password: str):
    from backup.engine import BackupEngine
    e = BackupEngine()
    e.set_key(_key_from_password(password))
    return e


def _restore(password: str):
    from backup.restore import RestoreEngine
    r = RestoreEngine()
    r.set_key(_key_from_password(password))
    return r


def _dr(password: str):
    from backup.disaster_recovery import DisasterRecovery
    from backup.engine import BackupEngine
    from backup.restore import RestoreEngine
    e = BackupEngine()
    k = _key_from_password(password)
    e.set_key(k)
    r = RestoreEngine()
    r.set_key(k)
    return DisasterRecovery(e, r)


def _catalog():
    from backup.catalog import BackupCatalog
    return BackupCatalog()


@router.get("/status")
def backup_status() -> dict:
    try:
        cat = _catalog()
        backups = cat.list(limit=10)
        total = len(cat.list(limit=9999))
        return {"total_backups": total, "recent": backups}
    except Exception as e:
        return {"error": str(e)}


@router.post("/full")
def backup_full(req: BackupFullRequest) -> dict:
    try:
        return _engine(req.password).create_full(notes=req.notes)
    except Exception as e:
        return {"error": str(e)}


@router.post("/incremental")
def backup_incremental(req: BackupIncrementalRequest) -> dict:
    try:
        return _engine(req.password).create_incremental(since_timestamp=req.since or "")
    except Exception as e:
        return {"error": str(e)}


@router.post("/selective")
def backup_selective(req: BackupSelectiveRequest) -> dict:
    try:
        return _engine(req.password).create_selective(req.components)
    except Exception as e:
        return {"error": str(e)}


@router.get("/list")
def backup_list() -> dict:
    try:
        return {"backups": _catalog().list()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/verify/{backup_id}")
def backup_verify(backup_id: str, password: str = "") -> dict:
    try:
        if not password:
            return {"error": "password required for verification"}
        return _engine(password).verify(backup_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/restore/points")
def restore_points(component: Optional[str] = None) -> dict:
    try:
        # Return catalog entries as restore points (no key needed for listing)
        cat = _catalog()
        backups = cat.list()
        if component:
            backups = [b for b in backups if component in (b.get("components") or [])]
        return {"points": backups}
    except Exception as e:
        return {"error": str(e)}


@router.post("/restore/full")
def restore_full(req: RestoreFullRequest) -> dict:
    try:
        return _restore(req.password).restore_full(req.backup_id, dry_run=req.dry_run)
    except Exception as e:
        return {"error": str(e)}


@router.post("/restore/selective")
def restore_selective(req: RestoreSelectiveRequest) -> dict:
    try:
        return _restore(req.password).restore_selective(req.backup_id, req.components, dry_run=req.dry_run)
    except Exception as e:
        return {"error": str(e)}


@router.post("/restore/pit")
def restore_pit(req: RestorePitRequest) -> dict:
    try:
        return _restore(req.password).restore_point_in_time(req.before_timestamp, req.component)
    except Exception as e:
        return {"error": str(e)}


@router.get("/dr/status")
def dr_status() -> dict:
    try:
        from backup.disaster_recovery import DisasterRecovery
        from backup.engine import BackupEngine
        from backup.restore import RestoreEngine
        dr = DisasterRecovery(BackupEngine(), RestoreEngine())
        return dr.check_backup_health()
    except Exception as e:
        return {"error": str(e)}


@router.post("/dr/integrity")
def dr_integrity(password: str = "") -> dict:
    try:
        from backup.disaster_recovery import DisasterRecovery
        from backup.engine import BackupEngine
        from backup.restore import RestoreEngine
        key = _key_from_password(password) if password else None
        e = BackupEngine()
        r = RestoreEngine()
        if key:
            e.set_key(key); r.set_key(key)
        dr = DisasterRecovery(e, r)
        return dr.check_system_integrity()
    except Exception as e:
        return {"error": str(e)}


@router.post("/dr/simulate/{backup_id}")
def dr_simulate(backup_id: str, password: str = "") -> dict:
    try:
        return _dr(password).run_recovery_simulation(backup_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/dr/plan")
def dr_plan() -> dict:
    try:
        from backup.disaster_recovery import DisasterRecovery
        from backup.engine import BackupEngine
        from backup.restore import RestoreEngine
        dr = DisasterRecovery(BackupEngine(), RestoreEngine())
        return dr.generate_recovery_plan()
    except Exception as e:
        return {"error": str(e)}


@router.get("/dr/report")
def dr_report() -> dict:
    try:
        from backup.disaster_recovery import DisasterRecovery
        from backup.engine import BackupEngine
        from backup.restore import RestoreEngine
        dr = DisasterRecovery(BackupEngine(), RestoreEngine())
        return dr.generate_report()
    except Exception as e:
        return {"error": str(e)}
