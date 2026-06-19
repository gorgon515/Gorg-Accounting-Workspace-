"""HELIOS Strategic Reasoning API — strategy, autonomous proposals, learning."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class DecomposeRequest(BaseModel):
    goal: str
    target_value: float = 100.0
    horizon_months: int = 12


class PrioritizeRequest(BaseModel):
    items: list[dict]


class TradeoffRequest(BaseModel):
    options: list[dict]


class ConstraintRequest(BaseModel):
    plan: dict
    constraints: dict


class DecideRequest(BaseModel):
    decision: str


class OutcomeRequest(BaseModel):
    kind: str
    predicted: float
    actual: float
    subject_id: Optional[str] = None


@router.get("/recommend")
def recommend():
    try:
        from reasoning.engine import get_reasoning_engine
        return get_reasoning_engine().recommend()
    except Exception as e:
        return {"error": str(e)}


@router.post("/decompose")
def decompose(req: DecomposeRequest):
    try:
        from reasoning.engine import get_reasoning_engine
        return get_reasoning_engine().decompose_goal(req.goal, req.target_value, req.horizon_months)
    except Exception as e:
        return {"error": str(e)}


@router.post("/prioritize")
def prioritize(req: PrioritizeRequest):
    try:
        from reasoning.engine import get_reasoning_engine
        return {"ranked": get_reasoning_engine().prioritize(req.items)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/tradeoffs")
def tradeoffs(req: TradeoffRequest):
    try:
        from reasoning.engine import get_reasoning_engine
        return get_reasoning_engine().analyze_tradeoffs(req.options)
    except Exception as e:
        return {"error": str(e)}


@router.post("/constraints")
def constraints(req: ConstraintRequest):
    try:
        from reasoning.engine import get_reasoning_engine
        return get_reasoning_engine().check_constraints(req.plan, req.constraints)
    except Exception as e:
        return {"error": str(e)}


# ---- Autonomous proposal loop ----

@router.post("/proposals/run")
def run_proposals():
    try:
        from reasoning.proposals import get_proposal_loop
        return get_proposal_loop().run_daily()
    except Exception as e:
        return {"error": str(e)}


@router.get("/proposals")
def list_proposals(status: Optional[str] = None, limit: int = 100):
    try:
        from reasoning.proposals import get_proposal_loop
        return {"proposals": get_proposal_loop().list_proposals(status, limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/proposals/stats")
def proposal_stats():
    try:
        from reasoning.proposals import get_proposal_loop
        return get_proposal_loop().stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/proposals/{proposal_id}/decide")
def decide_proposal(proposal_id: str, req: DecideRequest):
    try:
        from reasoning.proposals import get_proposal_loop
        return get_proposal_loop().decide(proposal_id, req.decision)
    except Exception as e:
        return {"error": str(e)}


# ---- Learning engine ----

@router.post("/learning/outcome")
def record_outcome(req: OutcomeRequest):
    try:
        from reasoning.learning import get_learning_engine
        return get_learning_engine().record_outcome(req.kind, req.predicted, req.actual, req.subject_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/learning/accuracy")
def learning_accuracy(kind: Optional[str] = None):
    try:
        from reasoning.learning import get_learning_engine
        return get_learning_engine().accuracy_by_kind(kind)
    except Exception as e:
        return {"error": str(e)}


@router.get("/learning/trend/{kind}")
def learning_trend(kind: str, window: int = 10):
    try:
        from reasoning.learning import get_learning_engine
        return get_learning_engine().trend(kind, window)
    except Exception as e:
        return {"error": str(e)}
