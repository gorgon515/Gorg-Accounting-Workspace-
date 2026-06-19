"""Quant Research Engine endpoints: technicals, factor scoring, risk, portfolio."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from ..models import FactorRequest, PortfolioRequest, PriceInput, RiskRequest
from ..services import factors, risk, technicals
from ..services.market_data import market

router = APIRouter(prefix="/quant", tags=["quant"])


def _resolve_prices(symbol: Optional[str], prices: Optional[list[float]], rng: str) -> list[float]:
    """Use the supplied series, or fetch it for the symbol. Raises DataUnavailable."""
    if prices:
        return prices
    return market.prices(symbol, rng)  # type: ignore[arg-type]


@router.post("/analyze")
def analyze(req: PriceInput) -> dict:
    prices = _resolve_prices(req.symbol, req.prices, req.range)
    out = technicals.analyze(prices)
    if req.symbol:
        out["symbol"] = req.symbol.upper()
    return out


@router.post("/factors")
def factor_score(req: FactorRequest) -> dict:
    prices = req.prices
    if not prices and req.symbol:
        # Momentum needs prices, but factor scoring still works on fundamentals
        # alone if the fetch fails — so this is best-effort, not fatal.
        try:
            prices = market.prices(req.symbol, req.range)
        except Exception:
            prices = None
    return factors.score(req.symbol, req.fundamentals, prices)


@router.post("/risk")
def risk_summary(req: RiskRequest) -> dict:
    prices = _resolve_prices(req.symbol, req.prices, req.range)
    bench = req.benchmark_prices
    if not bench and req.benchmark_symbol:
        try:
            bench = market.prices(req.benchmark_symbol, req.range)
        except Exception:
            bench = None
    out = risk.summarize_returns(prices, bench, req.risk_free)
    if req.symbol:
        out["symbol"] = req.symbol.upper()
    return out


@router.post("/portfolio")
def portfolio(req: PortfolioRequest) -> dict:
    bench = req.benchmark_prices
    if not bench and req.benchmark_symbol:
        try:
            bench = market.prices(req.benchmark_symbol, "1y")
        except Exception:
            bench = None
    return risk.portfolio_report(req.holdings, bench)
