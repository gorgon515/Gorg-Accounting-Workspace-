"""HELIOS Cross-Domain Intelligence API — graph, opportunities, risks."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class StatusRequest(BaseModel):
    status: str


# ---- Graph ----

@router.post("/graph/build")
def build_graph():
    try:
        from intelligence.graph import get_graph
        return get_graph().build_from_domains()
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph")
def graph(domain: Optional[str] = None):
    try:
        from intelligence.graph import get_graph
        g = get_graph()
        return {"nodes": g.nodes(domain), "edges": g.edges()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/insights")
def graph_insights():
    try:
        from intelligence.graph import get_graph
        return {"insights": get_graph().discover_relationships()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/stats")
def graph_stats():
    try:
        from intelligence.graph import get_graph
        return get_graph().stats()
    except Exception as e:
        return {"error": str(e)}


# ---- Opportunities ----

@router.post("/opportunities/scan")
def scan_opportunities():
    try:
        from intelligence.opportunities import get_opportunity_engine
        return {"opportunities": get_opportunity_engine().scan()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/opportunities")
def list_opportunities(status: Optional[str] = None, min_score: float = 0.0):
    try:
        from intelligence.opportunities import get_opportunity_engine
        return {"opportunities": get_opportunity_engine().list(status, min_score)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/opportunities/{opp_id}")
def get_opportunity(opp_id: str):
    try:
        from intelligence.opportunities import get_opportunity_engine
        o = get_opportunity_engine().get(opp_id)
        return o or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/opportunities/{opp_id}/status")
def set_opportunity_status(opp_id: str, req: StatusRequest):
    try:
        from intelligence.opportunities import get_opportunity_engine
        return {"updated": get_opportunity_engine().set_status(opp_id, req.status)}
    except Exception as e:
        return {"error": str(e)}


# ---- Risks ----

@router.post("/risks/scan")
def scan_risks():
    try:
        from intelligence.risks import get_risk_engine
        return {"risks": get_risk_engine().scan()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/risks")
def list_risks(status: Optional[str] = None, severity: Optional[str] = None):
    try:
        from intelligence.risks import get_risk_engine
        return {"risks": get_risk_engine().list(status, severity)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/risks/summary")
def risk_summary():
    try:
        from intelligence.risks import get_risk_engine
        return get_risk_engine().summary()
    except Exception as e:
        return {"error": str(e)}


@router.get("/risks/{risk_id}")
def get_risk(risk_id: str):
    try:
        from intelligence.risks import get_risk_engine
        r = get_risk_engine().get(risk_id)
        return r or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/risks/{risk_id}/status")
def set_risk_status(risk_id: str, req: StatusRequest):
    try:
        from intelligence.risks import get_risk_engine
        return {"updated": get_risk_engine().set_status(risk_id, req.status)}
    except Exception as e:
        return {"error": str(e)}
