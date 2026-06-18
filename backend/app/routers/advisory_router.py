"""HELIOS Advisory API — personal and business advisory."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/advisory", tags=["advisory"])


class CapacityRequest(BaseModel):
    billable_hours_available: float = 160.0
    avg_engagement_hours: float = 20.0


@router.get("/personal/dashboard")
def personal_dashboard():
    try:
        from advisory.personal import get_personal_advisory
        return get_personal_advisory().life_dashboard()
    except Exception as e:
        return {"error": str(e)}


@router.get("/personal/recommendations")
def personal_recommendations(horizon: str = "weekly"):
    try:
        from advisory.personal import get_personal_advisory
        return get_personal_advisory().recommendations(horizon)
    except Exception as e:
        return {"error": str(e)}


@router.get("/business/analysis")
def business_analysis():
    try:
        from advisory.business import get_business_advisory
        return get_business_advisory().firm_analysis()
    except Exception as e:
        return {"error": str(e)}


@router.get("/business/executive-report")
def executive_report():
    try:
        from advisory.business import get_business_advisory
        return get_business_advisory().executive_report()
    except Exception as e:
        return {"error": str(e)}


@router.post("/business/capacity")
def capacity(req: CapacityRequest):
    try:
        from advisory.business import get_business_advisory
        return get_business_advisory().capacity_planning(
            req.billable_hours_available, req.avg_engagement_hours
        )
    except Exception as e:
        return {"error": str(e)}
