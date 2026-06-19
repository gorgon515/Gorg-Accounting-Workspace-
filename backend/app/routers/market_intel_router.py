"""Market Intelligence Center API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/market-intel", tags=["market-intelligence"])


class MacroSnapshot(BaseModel):
    gdp_growth: Optional[float] = None
    inflation_rate: Optional[float] = None
    unemployment_rate: Optional[float] = None
    fed_funds_rate: Optional[float] = None
    yield_10y: Optional[float] = None
    vix: Optional[float] = None
    outlook: str = "neutral"


@router.post("/brief/generate")
def generate_brief():
    from market_intel.brief import get_market_briefing
    return get_market_briefing().generate_daily_brief()


@router.get("/brief/latest")
def latest_brief():
    from market_intel.brief import get_market_briefing
    brief = get_market_briefing().get_latest_brief()
    if not brief:
        return {"message": "No brief yet — POST /brief/generate to create one"}
    return brief


@router.get("/briefs")
def list_briefs(limit: int = 10):
    from market_intel.brief import get_market_briefing
    return get_market_briefing().list_briefs(limit=limit)


@router.get("/signals")
def list_signals(signal_type: Optional[str] = None, symbol: Optional[str] = None,
                 status: str = "active", limit: int = 50):
    from market_intel.signals import get_signal_detector
    return get_signal_detector().list_signals(
        signal_type=signal_type, status=status, symbol=symbol, limit=limit
    )


@router.post("/signals/detect")
def detect_signals():
    from market_intel.signals import get_signal_detector
    return get_signal_detector().detect_signals()


@router.post("/signals/{signal_id}/dismiss")
def dismiss_signal(signal_id: str):
    from market_intel.signals import get_signal_detector
    result = get_signal_detector().dismiss_signal(signal_id)
    if not result:
        raise HTTPException(status_code=404, detail="Signal not found")
    return result


@router.get("/watchlist-alerts")
def list_watchlist_alerts(symbol: Optional[str] = None, limit: int = 50):
    from market_intel.brief import get_market_briefing
    return get_market_briefing().list_watchlist_alerts(symbol=symbol, limit=limit)


@router.post("/macro/snapshot")
def snapshot_macro(body: MacroSnapshot):
    from market_intel.brief import get_market_briefing
    return get_market_briefing().snapshot_macro(
        gdp_growth=body.gdp_growth, inflation_rate=body.inflation_rate,
        unemployment_rate=body.unemployment_rate, fed_funds_rate=body.fed_funds_rate,
        yield_10y=body.yield_10y, vix=body.vix, outlook=body.outlook,
    )


@router.get("/macro/latest")
def get_macro():
    from market_intel.brief import get_market_briefing
    snap = get_market_briefing().get_macro_snapshot()
    if not snap:
        return {"message": "No macro snapshot yet"}
    return snap


@router.get("/stats")
def market_intel_stats():
    from market_intel.brief import get_market_briefing
    from market_intel.signals import get_signal_detector
    return {
        "briefing": get_market_briefing().stats(),
        "signals": get_signal_detector().stats(),
    }
