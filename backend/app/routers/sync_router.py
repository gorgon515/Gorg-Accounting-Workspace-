"""HELIOS Multi-Device Sync API."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/sync", tags=["sync"])


class RegisterDeviceRequest(BaseModel):
    device_name: str
    device_type: str = "desktop"
    platform: Optional[str] = None
    public_key: Optional[str] = None

class StartSessionRequest(BaseModel):
    device_id: str

class CompleteSessionRequest(BaseModel):
    records_synced: int = 0
    conflicts_resolved: int = 0

class PushRequest(BaseModel):
    device_id: str
    component: str
    records: list[dict]

class ResolveConflictRequest(BaseModel):
    resolution: str  # last_write_wins | manual | merge
    winning_data: Optional[dict] = None


def _registry():
    from sync.device_registry import DeviceRegistry
    return DeviceRegistry()


def _engine():
    from sync.engine import SyncEngine
    from sync.device_registry import DeviceRegistry
    return SyncEngine(DeviceRegistry())


@router.get("/status")
def sync_status() -> dict:
    try:
        reg = _registry()
        devices = reg.list_devices()
        active = [d for d in devices if d.get("status") == "active"]
        return {
            "device_count": len(devices),
            "active_devices": len(active),
            "devices": devices[:10],
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/devices/register")
def register_device(req: RegisterDeviceRequest) -> dict:
    try:
        return _registry().register(req.device_name, req.device_type, req.platform, req.public_key)
    except Exception as e:
        return {"error": str(e)}


@router.get("/devices")
def list_devices() -> dict:
    try:
        return {"devices": _registry().list_devices()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/devices/{device_id}/heartbeat")
def heartbeat(device_id: str) -> dict:
    try:
        ok = _registry().heartbeat(device_id)
        return {"ok": ok}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/devices/{device_id}")
def deregister_device(device_id: str) -> dict:
    try:
        ok = _registry().deregister(device_id)
        return {"deregistered": ok}
    except Exception as e:
        return {"error": str(e)}


@router.post("/session/start")
def start_session(req: StartSessionRequest) -> dict:
    try:
        return _registry().start_session(req.device_id)
    except Exception as e:
        return {"error": str(e)}


@router.post("/session/{session_id}/complete")
def complete_session(session_id: str, req: CompleteSessionRequest) -> dict:
    try:
        return _registry().complete_session(session_id, req.records_synced, req.conflicts_resolved)
    except Exception as e:
        return {"error": str(e)}


@router.get("/delta")
def get_delta(device_id: str, component: str, since_version: int = 0) -> dict:
    try:
        records = _engine().get_delta(device_id, component, since_version)
        return {"records": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/push")
def push(req: PushRequest) -> dict:
    try:
        return _engine().push(req.device_id, req.component, req.records)
    except Exception as e:
        return {"error": str(e)}


@router.get("/conflicts")
def list_conflicts(resolved: bool = False) -> dict:
    try:
        return {"conflicts": _engine().list_conflicts(resolved=resolved)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: int, req: ResolveConflictRequest) -> dict:
    try:
        return _engine().resolve_conflict(conflict_id, req.resolution, req.winning_data)
    except Exception as e:
        return {"error": str(e)}


@router.get("/audit")
def sync_audit(device_id: Optional[str] = None, limit: int = 50) -> dict:
    try:
        return {"entries": _engine().sync_audit_log(device_id=device_id, limit=limit)}
    except Exception as e:
        return {"error": str(e)}
