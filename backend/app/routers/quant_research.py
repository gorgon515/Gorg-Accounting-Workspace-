"""Extended Quant Research endpoints: fundamentals, signals, market briefing."""
from __future__ import annotations

from fastapi import APIRouter

from ..models import FundamentalsRequest, MarketBriefingRequest, SignalRequest
from ..services.market_data import market
from quant import fundamentals as fa
from quant import signals as sig
from quant.market_briefing import generate_market_briefing

router = APIRouter(tags=["quant-research"])


@router.post("/quant/fundamentals")
def fundamentals(req: FundamentalsRequest) -> dict:
    return fa.analyze(req.symbol, req.fundamentals, req.history)


@router.post("/quant/signal")
def signal(req: SignalRequest) -> dict:
    prices = req.prices or market.prices(req.symbol, req.range)
    bench = req.benchmark_prices
    if not bench and req.benchmark_symbol:
        try:
            bench = market.prices(req.benchmark_symbol, req.range)
        except Exception:
            bench = None
    return sig.generate_signal(req.symbol, prices, fundamentals=req.fundamentals,
                               benchmark=bench, sector=req.sector)


@router.post("/market/briefing")
def market_briefing(req: MarketBriefingRequest) -> dict:
    quotes = req.quotes
    if not quotes and req.symbols:
        # Fetch live quotes for the supplied symbols (network-guarded per symbol).
        quotes = []
        for s in req.symbols:
            try:
                quotes.append(market.quote(s))
            except Exception:
                continue
    return generate_market_briefing(quotes or [], portfolio=req.portfolio,
                                    watchlist_changes=req.watchlist_changes,
                                    earnings=req.earnings, macro=req.macro)
