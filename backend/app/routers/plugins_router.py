"""HELIOS Plugin Architecture API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/plugins", tags=["plugins"])


class InstallRequest(BaseModel):
    manifest: dict
    actor: Optional[str] = None


class ExecuteRequest(BaseModel):
    function_name: str
    args: Optional[dict] = None
    permissions: list[str] = []


@router.post("/install")
def install(req: InstallRequest):
    try:
        from plugins.loader import get_loader
        return get_loader().install(req.manifest, actor=req.actor)
    except Exception as e:
        return {"error": str(e)}


@router.get("/")
def list_plugins(status: Optional[str] = None):
    try:
        from plugins.registry import get_registry
        return {"plugins": get_registry().list(status)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/sandbox/audit")
def sandbox_audit(limit: int = 100):
    try:
        from plugins.sandbox import get_sandbox
        return {"audit": get_sandbox().get_audit_log(limit=limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{plugin_id}")
def get_plugin(plugin_id: str):
    try:
        from plugins.loader import get_loader
        info = get_loader().get_plugin_info(plugin_id)
        return info or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{plugin_id}/enable")
def enable(plugin_id: str):
    try:
        from plugins.loader import get_loader
        return get_loader().enable(plugin_id)
    except Exception as e:
        return {"error": str(e)}


@router.post("/{plugin_id}/disable")
def disable(plugin_id: str):
    try:
        from plugins.loader import get_loader
        return get_loader().disable(plugin_id)
    except Exception as e:
        return {"error": str(e)}


@router.delete("/{plugin_id}")
def uninstall(plugin_id: str):
    try:
        from plugins.loader import get_loader
        return get_loader().uninstall(plugin_id)
    except Exception as e:
        return {"error": str(e)}


@router.post("/{plugin_id}/execute")
def execute(plugin_id: str, req: ExecuteRequest):
    try:
        from plugins.sandbox import get_sandbox
        return get_sandbox().execute(plugin_id, req.function_name, req.args, req.permissions)
    except Exception as e:
        return {"error": str(e)}


@router.get("/{plugin_id}/audit")
def plugin_audit(plugin_id: str, limit: int = 50):
    try:
        from plugins.registry import get_registry
        return {"audit": get_registry().get_audit(plugin_id, limit)}
    except Exception as e:
        return {"error": str(e)}
