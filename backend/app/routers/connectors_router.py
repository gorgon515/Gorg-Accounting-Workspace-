"""Connector management API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


class ConnectorConfigUpdate(BaseModel):
    config: dict = {}


class CredentialStore(BaseModel):
    vault_key: str
    masked_preview: str = ""


@router.get("")
def list_connectors(category: Optional[str] = None, kind: Optional[str] = None):
    from connectors.registry import get_registry
    return get_registry().list(category=category, kind=kind)


@router.get("/stats")
def connector_stats():
    from connectors.registry import get_registry
    return get_registry().stats()


@router.get("/{connector_id}")
def get_connector(connector_id: str):
    from connectors.registry import get_registry
    c = get_registry().get(connector_id)
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")
    return c


@router.post("/{connector_id}/enable")
def enable_connector(connector_id: str):
    from connectors.registry import get_registry
    return get_registry().set_status(connector_id, "active")


@router.post("/{connector_id}/disable")
def disable_connector(connector_id: str):
    from connectors.registry import get_registry
    return get_registry().set_status(connector_id, "disabled")


@router.put("/{connector_id}/config")
def update_config(connector_id: str, body: ConnectorConfigUpdate):
    from connectors.registry import get_registry
    return get_registry().update_config(connector_id, body.config)


@router.post("/{connector_id}/credential")
def store_credential(connector_id: str, body: CredentialStore):
    from connectors.registry import get_registry
    get_registry().store_credential(connector_id, body.vault_key, body.masked_preview)
    return {"status": "stored", "connector_id": connector_id}


@router.get("/{connector_id}/health")
def health_check(connector_id: str):
    from connectors.registry import get_registry
    return get_registry().health_check(connector_id)


@router.post("/{connector_id}/fetch")
def fetch_connector(connector_id: str, body: dict = {}):
    from connectors.registry import get_registry
    result = get_registry().fetch(connector_id, **body)
    return result


@router.get("/{connector_id}/logs")
def poll_logs(connector_id: str, limit: int = 20):
    from connectors.registry import get_registry
    return get_registry().poll_logs(connector_id, limit=limit)
