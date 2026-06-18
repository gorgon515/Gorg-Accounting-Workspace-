"""HELIOS Production Monitoring API — errors, performance, incidents."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class RecordErrorRequest(BaseModel):
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    component: Optional[str] = None
    severity: str = "error"
    context: Optional[dict] = None


class ResolveErrorRequest(BaseModel):
    resolved_by: Optional[str] = None


class SampleRequest(BaseModel):
    metric_name: str
    value: float
    unit: str = "ms"
    component: Optional[str] = None
    tags: Optional[dict] = None


class CreateIncidentRequest(BaseModel):
    title: str
    description: str = ""
    severity: str = "medium"
    component: Optional[str] = None
    detected_by: Optional[str] = None


class IncidentStatusRequest(BaseModel):
    status: str
    note: Optional[str] = None
    updated_by: Optional[str] = None


class TimelineRequest(BaseModel):
    event_type: str
    description: str
    actor: Optional[str] = None


class ResolveIncidentRequest(BaseModel):
    resolution: str
    resolved_by: Optional[str] = None


# ---- Errors ----

@router.post("/errors")
def record_error(req: RecordErrorRequest):
    try:
        from monitoring.error_tracker import get_error_tracker
        eid = get_error_tracker().record(
            req.error_type, req.message, req.stack_trace, req.component, req.severity, req.context
        )
        return {"error_id": eid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/errors/stats")
def error_stats():
    try:
        from monitoring.error_tracker import get_error_tracker
        return get_error_tracker().stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/errors")
def list_errors(severity: Optional[str] = None, component: Optional[str] = None,
                resolved: Optional[bool] = None, limit: int = 100):
    try:
        from monitoring.error_tracker import get_error_tracker
        return {"errors": get_error_tracker().list(severity, component, resolved, limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/errors/{error_id}")
def get_error(error_id: int):
    try:
        from monitoring.error_tracker import get_error_tracker
        err = get_error_tracker().get(error_id)
        return err or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/errors/{error_id}/resolve")
def resolve_error(error_id: int, req: ResolveErrorRequest):
    try:
        from monitoring.error_tracker import get_error_tracker
        return {"resolved": get_error_tracker().resolve(error_id, req.resolved_by)}
    except Exception as e:
        return {"error": str(e)}


# ---- Performance ----

@router.post("/performance/sample")
def record_sample(req: SampleRequest):
    try:
        from monitoring.performance import get_performance_sampler
        sid = get_performance_sampler().record_sample(
            req.metric_name, req.value, req.unit, req.component, req.tags
        )
        return {"sample_id": sid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/performance")
def performance_dashboard():
    try:
        from monitoring.performance import get_performance_sampler
        return get_performance_sampler().dashboard()
    except Exception as e:
        return {"error": str(e)}


@router.get("/performance/{metric_name}")
def get_percentiles(metric_name: str, period_hours: int = 24):
    try:
        from monitoring.performance import get_performance_sampler
        return get_performance_sampler().get_percentiles(metric_name, period_hours)
    except Exception as e:
        return {"error": str(e)}


# ---- Incidents ----

@router.post("/incidents")
def create_incident(req: CreateIncidentRequest):
    try:
        from monitoring.incidents import get_incident_manager
        return get_incident_manager().create(
            req.title, req.description, req.severity, req.component, req.detected_by
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/incidents/stats/mttr")
def mttr_stats():
    try:
        from monitoring.incidents import get_incident_manager
        return get_incident_manager().mttr_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/incidents")
def list_incidents(status: Optional[str] = None, severity: Optional[str] = None, limit: int = 50):
    try:
        from monitoring.incidents import get_incident_manager
        return {"incidents": get_incident_manager().list(status, severity, limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    try:
        from monitoring.incidents import get_incident_manager
        inc = get_incident_manager().get(incident_id)
        return inc or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/incidents/{incident_id}/status")
def update_incident_status(incident_id: str, req: IncidentStatusRequest):
    try:
        from monitoring.incidents import get_incident_manager
        return get_incident_manager().update_status(incident_id, req.status, req.note, req.updated_by)
    except Exception as e:
        return {"error": str(e)}


@router.post("/incidents/{incident_id}/timeline")
def add_timeline(incident_id: str, req: TimelineRequest):
    try:
        from monitoring.incidents import get_incident_manager
        return get_incident_manager().add_timeline_event(
            incident_id, req.event_type, req.description, req.actor
        )
    except Exception as e:
        return {"error": str(e)}


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, req: ResolveIncidentRequest):
    try:
        from monitoring.incidents import get_incident_manager
        return {"resolved": get_incident_manager().resolve(incident_id, req.resolution, req.resolved_by)}
    except Exception as e:
        return {"error": str(e)}
