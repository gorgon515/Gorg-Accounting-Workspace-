from __future__ import annotations

from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/tradingview", tags=["tradingview"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BatchSymbolsBody(BaseModel):
    symbols: list[str]


class ScreenBody(BaseModel):
    asset_type: str = "stock"
    market: str = "america"
    filters: Optional[dict] = None
    sort_by: str = "market_cap_basic"
    sort_order: str = "desc"
    limit: int = 50


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _handle(fn, *args, **kwargs):
    """Execute a market_data function and convert errors to HTTP exceptions."""
    try:
        return fn(*args, **kwargs)
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Quote routes
# ---------------------------------------------------------------------------

@router.get("/quote/{symbol}")
def get_quote(symbol: str, session: str = Query(default="regular")):
    from market_data.tradingview import quote as tv_quote
    return _handle(tv_quote, symbol, session)


@router.post("/quote/batch")
def get_quotes_batch(body: BatchSymbolsBody):
    from market_data.tradingview import quotes_batch as tv_quotes_batch
    return _handle(tv_quotes_batch, body.symbols)


# ---------------------------------------------------------------------------
# Price routes
# ---------------------------------------------------------------------------

@router.get("/price/{symbol}")
def get_price(symbol: str):
    from market_data.tradingview import price as tv_price
    return _handle(tv_price, symbol)


@router.post("/price/batch")
def get_prices_batch(body: BatchSymbolsBody):
    from market_data.tradingview import prices_batch as tv_prices_batch
    return _handle(tv_prices_batch, body.symbols)


# ---------------------------------------------------------------------------
# Technical Analysis
# ---------------------------------------------------------------------------

@router.get("/ta/{symbol}")
def get_ta(
    symbol: str,
    interval: str = Query(default="1D"),
    include_indicators: bool = Query(default=True),
):
    from market_data.tradingview import ta as tv_ta
    return _handle(tv_ta, symbol, interval, include_indicators)


# ---------------------------------------------------------------------------
# News routes
# ---------------------------------------------------------------------------

@router.get("/news")
def get_news(
    symbol: Optional[str] = Query(default=None),
    market: str = Query(default="stock"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
):
    from market_data.tradingview import news as tv_news
    return _handle(tv_news, symbol, market, limit, offset)


@router.get("/news/{news_id:path}")
def get_news_detail(news_id: str):
    from market_data.tradingview import news_detail as tv_news_detail
    return _handle(tv_news_detail, news_id)


# ---------------------------------------------------------------------------
# Ideas routes
# ---------------------------------------------------------------------------

@router.get("/ideas/hot")
def get_ideas_hot():
    from market_data.tradingview import ideas_hot as tv_ideas_hot
    return _handle(tv_ideas_hot)


@router.get("/ideas/editors-picks")
def get_ideas_editors_picks():
    from market_data.tradingview import ideas_editors_picks as tv_ideas_editors_picks
    return _handle(tv_ideas_editors_picks)


@router.get("/ideas/{symbol}")
def get_ideas_by_symbol(symbol: str):
    from market_data.tradingview import ideas_by_symbol as tv_ideas_by_symbol
    return _handle(tv_ideas_by_symbol, symbol)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@router.get("/calendar")
def get_calendar(country: str = Query(default="US")):
    from market_data.tradingview import calendar as tv_calendar
    return _handle(tv_calendar, country)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search")
def get_search(
    q: str = Query(...),
    market: str = Query(default="stock"),
):
    from market_data.tradingview import search as tv_search
    return _handle(tv_search, q, market)


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------

@router.post("/screen")
def post_screen(body: ScreenBody):
    from market_data.tradingview import screen as tv_screen
    return _handle(
        tv_screen,
        body.asset_type,
        body.market,
        body.filters,
        body.sort_by,
        body.sort_order,
        body.limit,
    )


@router.get("/screener/presets")
def get_screener_presets():
    from market_data.tradingview import screener_presets as tv_screener_presets
    return _handle(tv_screener_presets)


@router.get("/screener/filters")
def get_screener_filter_options():
    from market_data.tradingview import screener_filter_options as tv_screener_filter_options
    return _handle(tv_screener_filter_options)


# ---------------------------------------------------------------------------
# Market data & Economy
# ---------------------------------------------------------------------------

@router.get("/market")
def get_market_data(
    market: str = Query(default="crypto"),
    type: str = Query(default="overview"),
):
    from market_data.tradingview import market_data as tv_market_data
    return _handle(tv_market_data, market, type)


@router.get("/economy/indicators")
def get_economy_indicators():
    from market_data.tradingview import economy_indicators as tv_economy_indicators
    return _handle(tv_economy_indicators)


# ---------------------------------------------------------------------------
# Enrich
# ---------------------------------------------------------------------------

@router.get("/enrich/{symbol}")
def get_enrich_symbol(symbol: str):
    from market_data.tradingview import enrich_symbol as tv_enrich_symbol
    return _handle(tv_enrich_symbol, symbol)
