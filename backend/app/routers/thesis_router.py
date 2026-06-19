"""Investment Thesis Engine API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


class ThesisCreate(BaseModel):
    title: str
    symbol: str = ""
    direction: str = "long"
    summary: str = ""
    evidence: list = []
    risks: list = []
    catalysts: list = []
    valuation: dict = {}
    expected_return: Optional[float] = None
    time_horizon: str = "12m"
    confidence: float = 0.5


class ThesisUpdate(BaseModel):
    fields: dict


class ThesisReview(BaseModel):
    note: str
    confidence: Optional[float] = None
    action: str = "review"


class ThesisOutcome(BaseModel):
    outcome: str
    realized_return: Optional[float] = None


@router.get("/theses")
def list_theses(status: Optional[str] = None, symbol: Optional[str] = None):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().list(status=status, symbol=symbol)


@router.post("/theses")
def create_thesis(body: ThesisCreate):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().create(
        body.title, body.symbol, body.direction, body.summary, body.evidence,
        body.risks, body.catalysts, body.valuation, body.expected_return,
        body.time_horizon, body.confidence)


@router.get("/theses/{tid}")
def get_thesis(tid: str):
    from thesis.engine import get_thesis_engine
    t = get_thesis_engine().get(tid)
    if not t:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return t


@router.put("/theses/{tid}")
def update_thesis(tid: str, body: ThesisUpdate):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().update(tid, body.fields)


@router.post("/theses/{tid}/review")
def add_review(tid: str, body: ThesisReview):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().add_review(tid, body.note, body.confidence, body.action)


@router.get("/theses/{tid}/reviews")
def reviews(tid: str):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().reviews(tid)


@router.post("/theses/{tid}/close")
def close_outcome(tid: str, body: ThesisOutcome):
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().close_outcome(tid, body.outcome, body.realized_return)


@router.get("/stats")
def stats():
    from thesis.engine import get_thesis_engine
    return get_thesis_engine().stats()
