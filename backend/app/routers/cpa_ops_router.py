"""CPA Operations Hub API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/cpa-ops", tags=["cpa-ops"])


class AdvisoryCreate(BaseModel):
    title: str
    body: str
    advisory_type: str = "general"
    trigger_update_id: Optional[str] = None
    priority: str = "normal"


class ComplianceCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "tax"
    due_date: str = ""
    client_id: str = ""
    priority: str = "normal"


@router.get("/updates")
def list_updates(category: Optional[str] = None, priority: Optional[str] = None, limit: int = 50):
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().list_updates(category=category, priority=priority, limit=limit)


@router.post("/ingest")
def ingest_updates():
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().ingest_regulatory_updates()


@router.post("/digest")
def run_digest():
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().run_digest()


@router.get("/advisories")
def list_advisories(status: Optional[str] = None, advisory_type: Optional[str] = None, limit: int = 50):
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().list_advisories(status=status, advisory_type=advisory_type, limit=limit)


@router.post("/advisories")
def create_advisory(body: AdvisoryCreate):
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().create_advisory(
        title=body.title, body=body.body, advisory_type=body.advisory_type,
        trigger_update_id=body.trigger_update_id, priority=body.priority,
    )


@router.get("/compliance")
def list_compliance(category: Optional[str] = None, status: str = "open", limit: int = 50):
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().list_compliance(category=category, status=status, limit=limit)


@router.post("/compliance")
def add_compliance_item(body: ComplianceCreate):
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().add_compliance_item(
        title=body.title, description=body.description, category=body.category,
        due_date=body.due_date, client_id=body.client_id, priority=body.priority,
    )


@router.get("/stats")
def cpa_stats():
    from cpa_ops.monitor import get_cpa_monitor
    return get_cpa_monitor().stats()
