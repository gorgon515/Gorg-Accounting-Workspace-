"""Market-data endpoints (quotes + history) via the connector layer."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.market_data import market

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/quote/{symbol}")
def quote(symbol: str) -> dict:
    return market.quote(symbol)


@router.get("/history/{symbol}")
def history(symbol: str, range: str = Query("6mo"), interval: str = Query("1d")) -> dict:
    return market.history(symbol, range, interval)
