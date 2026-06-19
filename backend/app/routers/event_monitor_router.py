"""Event Monitoring Engine API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/event-monitor", tags=["event-monitor"])


class EventCreate(BaseModel):
    category: str
    event_type: str
    title: str
    description: str = ""
    severity: str = "medium"
    source: str = ""
    metadata: dict = {}
    due_date: Optional[str] = None


class DeadlineCreate(BaseModel):
    title: str
    deadline_date: str
    description: str = ""
    category: str = "tax"
    client_id: str = ""
    reminder_days: int = 7


@router.post("/scan")
def scan_intelligence():
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().scan_intelligence()


@router.post("/check-deadlines")
def check_deadlines():
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().check_deadlines()


@router.get("/events")
def list_events(category: Optional[str] = None, severity: Optional[str] = None,
                status: str = "active", limit: int = 50):
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().list_events(category=category, severity=severity,
                                           status=status, limit=limit)


@router.post("/events")
def create_event(body: EventCreate):
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().create_event(
        category=body.category, event_type=body.event_type, title=body.title,
        description=body.description, severity=body.severity, source=body.source,
        metadata=body.metadata, due_date=body.due_date,
    )


@router.post("/events/{event_id}/acknowledge")
def acknowledge_event(event_id: str):
    from event_monitor.engine import get_event_monitor
    result = get_event_monitor().acknowledge_event(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.post("/events/{event_id}/resolve")
def resolve_event(event_id: str):
    from event_monitor.engine import get_event_monitor
    result = get_event_monitor().resolve_event(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("/deadlines")
def list_deadlines(category: Optional[str] = None, status: str = "pending", limit: int = 50):
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().list_deadlines(category=category, status=status, limit=limit)


@router.post("/deadlines")
def add_deadline(body: DeadlineCreate):
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().add_deadline(
        title=body.title, deadline_date=body.deadline_date, description=body.description,
        category=body.category, client_id=body.client_id, reminder_days=body.reminder_days,
    )


@router.get("/rules")
def list_rules():
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().list_rules()


@router.get("/stats")
def event_monitor_stats():
    from event_monitor.engine import get_event_monitor
    return get_event_monitor().stats()
