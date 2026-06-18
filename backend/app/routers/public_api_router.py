"""HELIOS Public REST API — API key management and rate limiting."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/public-api", tags=["public-api"])


class CreateKeyRequest(BaseModel):
    name: str
    owner_id: Optional[str] = None
    scopes: list[str] = []
    rate_limit_rpm: int = 60
    expires_days: Optional[int] = None


class VerifyKeyRequest(BaseModel):
    api_key: str


class RateLimitCheckRequest(BaseModel):
    key_id: str
    rpm_limit: int = 60


@router.post("/keys")
def create_key(req: CreateKeyRequest):
    try:
        from public_api.api_keys import get_api_key_manager
        return get_api_key_manager().create(
            req.name, req.owner_id, req.scopes, req.rate_limit_rpm, req.expires_days
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/keys/stats")
def key_stats():
    try:
        from public_api.api_keys import get_api_key_manager
        return get_api_key_manager().stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/keys/verify")
def verify_key(req: VerifyKeyRequest):
    try:
        from public_api.api_keys import get_api_key_manager
        return get_api_key_manager().verify(req.api_key)
    except Exception as e:
        return {"error": str(e)}


@router.get("/keys")
def list_keys(owner_id: Optional[str] = None, status: Optional[str] = None):
    try:
        from public_api.api_keys import get_api_key_manager
        return {"keys": get_api_key_manager().list(owner_id, status)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/keys/{key_id}")
def get_key(key_id: str):
    try:
        from public_api.api_keys import get_api_key_manager
        k = get_api_key_manager().get(key_id)
        return k or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/keys/{key_id}/revoke")
def revoke_key(key_id: str):
    try:
        from public_api.api_keys import get_api_key_manager
        return {"revoked": get_api_key_manager().revoke(key_id)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/rate-limit/check")
def rate_limit_check(req: RateLimitCheckRequest):
    try:
        from public_api.rate_limit import get_rate_limiter
        return get_rate_limiter().check(req.key_id, req.rpm_limit)
    except Exception as e:
        return {"error": str(e)}


@router.get("/rate-limit/{key_id}")
def rate_limit_stats(key_id: str):
    try:
        from public_api.rate_limit import get_rate_limiter
        return get_rate_limiter().get_stats(key_id)
    except Exception as e:
        return {"error": str(e)}


@router.post("/rate-limit/{key_id}/reset")
def rate_limit_reset(key_id: str):
    try:
        from public_api.rate_limit import get_rate_limiter
        get_rate_limiter().reset(key_id)
        return {"reset": True}
    except Exception as e:
        return {"error": str(e)}
