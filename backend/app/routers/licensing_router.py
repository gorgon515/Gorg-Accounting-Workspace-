"""HELIOS Licensing API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/licensing", tags=["licensing"])


class GenerateRequest(BaseModel):
    org_id: str
    org_name: str
    edition: str
    seats: int
    valid_days: int = 365


class VerifyRequest(BaseModel):
    license_key: str


class ActivateRequest(BaseModel):
    license_key: str
    machine_id: Optional[str] = None


class RevokeRequest(BaseModel):
    license_id: str


@router.get("/editions")
def list_editions():
    try:
        from licensing.editions import list_editions as _le
        return {"editions": _le()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/generate")
def generate(req: GenerateRequest):
    try:
        from licensing.license_manager import get_license_manager
        key = get_license_manager().generate(
            req.org_id, req.org_name, req.edition, req.seats, req.valid_days
        )
        return {"license_key": key}
    except Exception as e:
        return {"error": str(e)}


@router.post("/verify")
def verify(req: VerifyRequest):
    try:
        from licensing.license_manager import get_license_manager
        return get_license_manager().verify(req.license_key)
    except Exception as e:
        return {"error": str(e)}


@router.post("/activate")
def activate(req: ActivateRequest):
    try:
        from licensing.license_manager import get_license_manager
        return get_license_manager().activate(req.license_key, req.machine_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/active")
def active():
    try:
        from licensing.license_manager import get_license_manager
        lic = get_license_manager().get_active()
        return lic or {"active": False}
    except Exception as e:
        return {"error": str(e)}


@router.get("/activations")
def activations():
    try:
        from licensing.license_manager import get_license_manager
        return {"activations": get_license_manager().list_activations()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/revoke")
def revoke(req: RevokeRequest):
    try:
        from licensing.license_manager import get_license_manager
        return {"revoked": get_license_manager().revoke(req.license_id)}
    except Exception as e:
        return {"error": str(e)}
