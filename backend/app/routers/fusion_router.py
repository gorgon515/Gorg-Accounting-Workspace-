"""Intelligence Fusion Layer API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/fusion", tags=["fusion"])


class FusionEventCreate(BaseModel):
    title: str
    description: str
    pattern: str
    severity: str = "medium"
    confidence: float = 0.5
    domains: list[str] = []
    source_signals: list[str] = []
    action_type: str = "alert"
    draft_action: Optional[str] = None


@router.post("/run")
def run_fusion():
    from fusion.engine import get_fusion_engine
    return get_fusion_engine().run_fusion()


@router.get("/events")
def list_events(status: str = "new", severity: Optional[str] = None, limit: int = 50):
    from fusion.engine import get_fusion_engine
    return get_fusion_engine().list_events(status=status, severity=severity, limit=limit)


@router.post("/events")
def create_event(body: FusionEventCreate):
    from fusion.engine import get_fusion_engine
    return get_fusion_engine().create_event(
        title=body.title, description=body.description, pattern=body.pattern,
        severity=body.severity, confidence=body.confidence, domains=body.domains,
        source_signals=body.source_signals, action_type=body.action_type,
        draft_action=body.draft_action,
    )


@router.post("/events/{event_id}/acknowledge")
def acknowledge_event(event_id: str):
    from fusion.engine import get_fusion_engine
    result = get_fusion_engine().acknowledge_event(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("/rules")
def list_rules():
    from fusion.engine import get_fusion_engine
    return get_fusion_engine().list_rules()


@router.get("/stats")
def fusion_stats():
    from fusion.engine import get_fusion_engine
    return get_fusion_engine().stats()
