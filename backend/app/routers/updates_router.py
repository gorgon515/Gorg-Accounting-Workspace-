"""HELIOS Auto-Update & Installer API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/updates", tags=["updates"])


class DownloadRequest(BaseModel):
    version: str
    channel: str = "stable"


class InstallRequest(BaseModel):
    version: str
    restart: bool = False


class RollbackRequest(BaseModel):
    target_version: Optional[str] = None


class SettingsRequest(BaseModel):
    channel: Optional[str] = None
    auto_download: Optional[bool] = None
    auto_install: Optional[bool] = None


@router.get("/check")
def check(channel: str = "stable"):
    try:
        from updates.updater import get_updater
        return get_updater().check_for_updates(channel)
    except Exception as e:
        return {"error": str(e)}


@router.post("/download")
def download(req: DownloadRequest):
    try:
        from updates.updater import get_updater
        return get_updater().download_update(req.version, req.channel)
    except Exception as e:
        return {"error": str(e)}


@router.post("/install")
def install(req: InstallRequest):
    try:
        from updates.updater import get_updater
        return get_updater().install_update(req.version, req.restart)
    except Exception as e:
        return {"error": str(e)}


@router.post("/rollback")
def rollback(req: RollbackRequest):
    try:
        from updates.updater import get_updater
        return get_updater().rollback(req.target_version)
    except Exception as e:
        return {"error": str(e)}


@router.get("/channels")
def channels():
    try:
        from updates.channels import list_channels
        return {"channels": list_channels()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/settings")
def get_settings():
    try:
        from updates.updater import get_updater
        return get_updater().get_settings()
    except Exception as e:
        return {"error": str(e)}


@router.put("/settings")
def update_settings(req: SettingsRequest):
    try:
        from updates.updater import get_updater
        return get_updater().update_settings(**req.model_dump(exclude_none=True))
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
def history():
    try:
        from updates.updater import get_updater
        return {"history": get_updater().history()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/validate-install")
def validate_install():
    try:
        from installer.validate import get_validator
        return get_validator().run_all()
    except Exception as e:
        return {"error": str(e)}


@router.post("/setup/data-dir")
def setup_data_dir():
    try:
        from installer.setup import get_setup_manager
        return get_setup_manager().initialize_data_directory()
    except Exception as e:
        return {"error": str(e)}


@router.post("/setup/migrate")
def setup_migrate():
    try:
        from installer.setup import get_setup_manager
        return get_setup_manager().run_database_migrations()
    except Exception as e:
        return {"error": str(e)}


@router.post("/setup/verify")
def setup_verify():
    try:
        from installer.setup import get_setup_manager
        return get_setup_manager().verify_installation()
    except Exception as e:
        return {"error": str(e)}


@router.get("/install-info")
def install_info():
    try:
        from installer.setup import get_setup_manager
        return get_setup_manager().get_installation_info()
    except Exception as e:
        return {"error": str(e)}
