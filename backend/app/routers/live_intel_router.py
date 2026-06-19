"""Live Intelligence Platform API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/live-intel", tags=["live-intelligence"])


class AlertAck(BaseModel):
    alert_id: str


class MonitorConfig(BaseModel):
    name: str
    domain: str
    keywords: list[str] = []
    connectors: list[str] = []
    check_interval_hours: int = 24


@router.get("/items")
def list_items(domain: Optional[str] = None, source: Optional[str] = None, limit: int = 50):
    from live_intelligence.monitor import get_monitor
    return get_monitor().list_items(domain=domain, source=source, limit=limit)


@router.get("/alerts")
def list_alerts(status: str = "new", limit: int = 50):
    from live_intelligence.monitor import get_monitor
    return get_monitor().list_alerts(status=status, limit=limit)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str):
    from live_intelligence.monitor import get_monitor
    result = get_monitor().acknowledge_alert(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


@router.get("/signals")
def list_signals(domain: Optional[str] = None, limit: int = 50):
    from live_intelligence.monitor import get_monitor
    return get_monitor().list_signals(domain=domain, limit=limit)


@router.post("/poll/{connector_id}")
def poll_connector(connector_id: str, domain: str = ""):
    from live_intelligence.monitor import get_monitor
    return get_monitor().poll_connector(connector_id, domain=domain)


@router.get("/sources")
def list_sources():
    from live_intelligence.monitor import get_monitor
    return get_monitor().sources()


@router.post("/monitors")
def add_monitor(body: MonitorConfig):
    from live_intelligence.monitor import get_monitor
    return get_monitor().add_monitor(
        name=body.name, domain=body.domain, keywords=body.keywords,
        connectors=body.connectors, check_interval_hours=body.check_interval_hours,
    )


@router.get("/monitors")
def list_monitors():
    from live_intelligence.monitor import get_monitor
    return get_monitor().list_monitors()


@router.get("/stats")
def stats():
    from live_intelligence.monitor import get_monitor
    return get_monitor().stats()
