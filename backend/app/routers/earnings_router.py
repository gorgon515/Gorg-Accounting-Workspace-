"""Earnings Intelligence System API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


class EarningsEvent(BaseModel):
    symbol: str
    period: str = ""
    earnings_date: str = ""
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    guidance: str = ""
    transcript: str = ""


class Revision(BaseModel):
    symbol: str
    metric: str = "eps"
    old_value: float
    new_value: float
    analyst: str = ""


class SentimentReq(BaseModel):
    text: str


@router.get("/events")
def list_events(symbol: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().list_events(symbol=symbol, status=status, limit=limit)


@router.post("/events")
def add_event(body: EarningsEvent):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().add_event(**body.model_dump())


@router.get("/events/{eid}/surprise")
def surprise(eid: str):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().surprise(eid)


@router.post("/events/{eid}/scorecard")
def scorecard(eid: str):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().scorecard(eid)


@router.post("/revisions")
def add_revision(body: Revision):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().add_revision(body.symbol, body.metric, body.old_value,
                                              body.new_value, body.analyst)


@router.get("/revisions/{symbol}")
def revision_trend(symbol: str, metric: str = "eps"):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().revision_trend(symbol.upper(), metric)


@router.post("/sentiment")
def sentiment(body: SentimentReq):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().analyze_sentiment(body.text)


@router.get("/drift/{symbol}")
def drift(symbol: str, earnings_date: str, window: int = 10):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().post_earnings_drift(symbol.upper(), earnings_date, window)


@router.get("/scorecards")
def list_scorecards(symbol: Optional[str] = None, limit: int = 30):
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().list_scorecards(symbol=symbol, limit=limit)


@router.get("/stats")
def stats():
    from earnings.engine import get_earnings_engine
    return get_earnings_engine().stats()
