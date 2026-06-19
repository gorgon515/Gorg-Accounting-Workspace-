"""Financial Data Hub API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/financial-hub", tags=["financial-hub"])


class WatchlistAdd(BaseModel):
    symbol: str
    name: str = ""
    sector: str = ""


class PriceStore(BaseModel):
    symbol: str
    bars: list[dict]
    source: str = "manual"


@router.get("/prices/{symbol}")
def get_prices(symbol: str, limit: int = 252, source: Optional[str] = None):
    from financial_hub.store import get_financial_hub
    return get_financial_hub().get_prices(symbol.upper(), limit=limit, source=source)


@router.post("/prices")
def store_prices(body: PriceStore):
    from financial_hub.store import get_financial_hub
    stored = get_financial_hub().store_prices(body.symbol.upper(), body.bars, source=body.source)
    return {"stored": stored, "symbol": body.symbol.upper()}


@router.get("/economic/{series_id}")
def get_economic(series_id: str, limit: int = 60):
    from financial_hub.store import get_financial_hub
    return get_financial_hub().get_economic(series_id.upper(), limit=limit)


@router.get("/filings")
def list_filings(form: Optional[str] = None, limit: int = 50):
    from financial_hub.store import get_financial_hub
    return get_financial_hub().list_filings(form=form, limit=limit)


@router.get("/watchlist")
def get_watchlist():
    from financial_hub.store import get_financial_hub
    return get_financial_hub().get_watchlist()


@router.post("/watchlist")
def add_watchlist(body: WatchlistAdd):
    from financial_hub.store import get_financial_hub
    return get_financial_hub().add_watchlist(body.symbol.upper(), body.name, body.sector)


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str):
    from financial_hub.store import get_financial_hub
    get_financial_hub().remove_watchlist(symbol.upper())
    return {"removed": symbol.upper()}


@router.get("/stats")
def financial_hub_stats():
    from financial_hub.store import get_financial_hub
    return get_financial_hub().stats()
