"""Investment Discovery Engine API — Phase 15.75 Part 1.

Universe stats/browse/seed/ingest, opportunity scans, idea ranking with
anti-MAG7 diversification, investment memos, candidate portfolios, and the
daily discovery workflow. All advisory.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


class IngestBody(BaseModel):
    securities: list[dict] = []


class RankBody(BaseModel):
    limit: int = 100
    exclude_mega_cap: bool = False
    penalize_coverage: bool = True
    portfolio_overlap: list[str] = []


class BuildPortfolioBody(BaseModel):
    style: str
    size: int = 10


# ── universe ─────────────────────────────────────────────────────────────────
@router.get("/universe/stats")
def universe_stats():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().universe_stats()


@router.get("/universe")
def list_universe(sector: Optional[str] = None, cap_tier: Optional[str] = None,
                  exchange: Optional[str] = None, limit: int = 200):
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().list_universe(
        sector=sector, cap_tier=cap_tier, exchange=exchange, limit=limit)


@router.get("/universe/{symbol}")
def get_security(symbol: str):
    from investing.discovery.engine import get_discovery_engine
    sec = get_discovery_engine().get_security(symbol)
    if not sec:
        raise HTTPException(status_code=404, detail=f"Security not found: {symbol}")
    return sec


@router.post("/universe/seed")
def seed():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().seed()


@router.post("/universe/ingest")
def ingest(body: IngestBody):
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().ingest_securities(body.securities)


# ── scanning ─────────────────────────────────────────────────────────────────
@router.get("/scan/strategies")
def scan_strategies():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().scan_strategies()


@router.get("/scan")
def scan(strategy: str, limit: int = 25):
    from investing.discovery.engine import get_discovery_engine
    try:
        return get_discovery_engine().scan(strategy, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── ranking ──────────────────────────────────────────────────────────────────
@router.post("/rank")
def rank(body: RankBody):
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().rank(
        limit=body.limit, exclude_mega_cap=body.exclude_mega_cap,
        penalize_coverage=body.penalize_coverage,
        portfolio_overlap=body.portfolio_overlap)


@router.get("/ideas")
def ideas(tier: str = "top25"):
    from investing.discovery.engine import get_discovery_engine
    try:
        return get_discovery_engine().ideas(tier)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── memo ─────────────────────────────────────────────────────────────────────
@router.get("/memo/{symbol}")
def memo(symbol: str):
    from investing.discovery.engine import get_discovery_engine
    try:
        return get_discovery_engine().memo_for(symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── candidate portfolios ─────────────────────────────────────────────────────
@router.get("/portfolios")
def portfolio_styles():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().portfolio_styles()


@router.post("/portfolios/build")
def build_portfolio(body: BuildPortfolioBody):
    from investing.discovery.engine import get_discovery_engine
    try:
        return get_discovery_engine().build_portfolio(body.style, size=body.size)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── daily workflow ───────────────────────────────────────────────────────────
@router.post("/daily")
def run_daily():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().run_daily()


@router.get("/daily/latest")
def latest_daily():
    from investing.discovery.engine import get_discovery_engine
    latest = get_discovery_engine().latest_daily()
    if latest is None:
        raise HTTPException(status_code=404, detail="No daily run found")
    return latest


# ── stats ────────────────────────────────────────────────────────────────────
@router.get("/stats")
def stats():
    from investing.discovery.engine import get_discovery_engine
    return get_discovery_engine().stats()
