"""Portfolio Construction Engine API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/portfolio-lab", tags=["portfolio-lab"])


class PortfolioConstruct(BaseModel):
    name: str
    symbols: list[str]
    method: str = "equal_weight"
    description: str = ""
    lookback: int = 252
    constraints: Optional[dict] = None
    risk_free: float = 0.0
    market_weights: Optional[list[float]] = None
    views: Optional[dict] = None


@router.get("/methods")
def methods():
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().methods()


@router.get("/portfolios")
def list_portfolios(status: str = "active", limit: int = 50):
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().list(status=status, limit=limit)


@router.post("/portfolios")
def construct(body: PortfolioConstruct):
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().construct(
        body.name, body.symbols, body.method, body.description, body.lookback,
        body.constraints, body.risk_free, body.market_weights, body.views)


@router.get("/portfolios/{pid}")
def get_portfolio(pid: str):
    from portfolio.engine import get_portfolio_engine
    pf = get_portfolio_engine().get(pid)
    if not pf:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return pf


@router.post("/portfolios/{pid}/rebalance")
def propose_rebalance(pid: str):
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().propose_rebalance(pid)


@router.get("/rebalances")
def list_rebalances(portfolio_id: Optional[str] = None, status: str = "pending"):
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().list_rebalances(portfolio_id=portfolio_id, status=status)


@router.get("/stats")
def stats():
    from portfolio.engine import get_portfolio_engine
    return get_portfolio_engine().stats()
