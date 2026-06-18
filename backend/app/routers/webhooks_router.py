"""HELIOS Webhooks API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    events: list[str] = []
    secret: Optional[str] = None
    owner_id: Optional[str] = None


class UpdateWebhookRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    status: Optional[str] = None
    secret: Optional[str] = None


class DeliverRequest(BaseModel):
    event_type: str
    payload: dict = {}


@router.post("/")
def create_webhook(req: CreateWebhookRequest):
    try:
        from public_api.webhooks import get_webhook_manager
        return get_webhook_manager().create(req.name, req.url, req.events, req.secret, req.owner_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/")
def list_webhooks(owner_id: Optional[str] = None, status: Optional[str] = None):
    try:
        from public_api.webhooks import get_webhook_manager
        return {"webhooks": get_webhook_manager().list(owner_id, status)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{webhook_id}")
def get_webhook(webhook_id: str):
    try:
        from public_api.webhooks import get_webhook_manager
        wh = get_webhook_manager().get(webhook_id)
        return wh or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.put("/{webhook_id}")
def update_webhook(webhook_id: str, req: UpdateWebhookRequest):
    try:
        from public_api.webhooks import get_webhook_manager
        return get_webhook_manager().update(webhook_id, **req.model_dump(exclude_none=True))
    except Exception as e:
        return {"error": str(e)}


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str):
    try:
        from public_api.webhooks import get_webhook_manager
        return {"deleted": get_webhook_manager().delete(webhook_id)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{webhook_id}/deliver")
def deliver(webhook_id: str, req: DeliverRequest):
    try:
        from public_api.webhooks import get_webhook_manager
        return get_webhook_manager().deliver(webhook_id, req.event_type, req.payload)
    except Exception as e:
        return {"error": str(e)}


@router.get("/{webhook_id}/deliveries")
def deliveries(webhook_id: str, limit: int = 50):
    try:
        from public_api.webhooks import get_webhook_manager
        return {"deliveries": get_webhook_manager().deliveries(webhook_id, limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{webhook_id}/stats")
def stats(webhook_id: str):
    try:
        from public_api.webhooks import get_webhook_manager
        return get_webhook_manager().stats(webhook_id)
    except Exception as e:
        return {"error": str(e)}
