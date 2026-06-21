from __future__ import annotations

import os
import requests
from typing import Optional

BASE_URL = "https://tradingview-data1.p.rapidapi.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt(symbol: str) -> str:
    """Auto-prefix with NASDAQ: if no exchange colon present."""
    return symbol if ":" in symbol else f"NASDAQ:{symbol}"


def _key() -> str:
    """Return the RapidAPI key from the environment."""
    return os.getenv("TRADINGVIEW_RAPIDAPI_KEY", "")


def _headers() -> dict:
    """Return request headers for TradingView RapidAPI."""
    return {
        "x-rapidapi-host": "tradingview-data1.p.rapidapi.com",
        "x-rapidapi-key": _key(),
    }


def _get(path: str, params: Optional[dict] = None) -> dict | list:
    """Perform a GET request. Returns parsed JSON or an error dict."""
    if not _key():
        return {"error": "TRADINGVIEW_RAPIDAPI_KEY not configured", "configured": False}
    response = requests.get(
        f"{BASE_URL}{path}",
        headers=_headers(),
        params=params,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _post(path: str, body: Optional[dict] = None) -> dict | list:
    """Perform a POST request. Returns parsed JSON or an error dict."""
    if not _key():
        return {"error": "TRADINGVIEW_RAPIDAPI_KEY not configured", "configured": False}
    response = requests.post(
        f"{BASE_URL}{path}",
        headers=_headers(),
        json=body,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------

def quote(symbol: str, session: str = "regular") -> dict | list:
    """GET /quote — single symbol quote."""
    return _get("/quote", params={"symbol": _fmt(symbol), "session": session})


def quotes_batch(symbols: list[str]) -> dict | list:
    """GET /quote/batch — multiple symbol quotes."""
    formatted = ",".join(_fmt(s) for s in symbols)
    return _get("/quote/batch", params={"symbols": formatted})


def price(symbol: str) -> dict | list:
    """GET /price — single symbol price."""
    return _get("/price", params={"symbol": _fmt(symbol)})


def prices_batch(symbols: list[str]) -> dict | list:
    """GET /price/batch — multiple symbol prices."""
    formatted = ",".join(_fmt(s) for s in symbols)
    return _get("/price/batch", params={"symbols": formatted})


def ta(symbol: str, interval: str = "1D", include_indicators: bool = True) -> dict | list:
    """GET /ta — technical analysis for a symbol."""
    return _get("/ta", params={
        "symbol": _fmt(symbol),
        "interval": interval,
        "include_indicators": include_indicators,
    })


def news(
    symbol: Optional[str] = None,
    market: str = "stock",
    limit: int = 20,
    offset: int = 0,
) -> dict | list:
    """GET /news — news feed, optionally filtered by symbol."""
    params: dict = {"market": market, "limit": limit, "offset": offset}
    if symbol is not None:
        params["symbol"] = _fmt(symbol)
    return _get("/news", params=params)


def news_detail(news_id: str) -> dict | list:
    """GET /news — fetch a specific news item by ID."""
    return _get("/news", params={"news_id": news_id})


def ideas_by_symbol(symbol: str) -> dict | list:
    """GET /ideas/by-symbol — trading ideas for a specific symbol."""
    return _get("/ideas/by-symbol", params={"symbol": _fmt(symbol)})


def ideas_hot() -> dict | list:
    """GET /ideas/hot — currently hot trading ideas."""
    return _get("/ideas/hot")


def ideas_editors_picks() -> dict | list:
    """GET /ideas/editors-picks — editor-curated trading ideas."""
    return _get("/ideas/editors-picks")


def calendar(country: str = "US") -> dict | list:
    """GET /calendar — economic/earnings calendar."""
    return _get("/calendar", params={"country": country})


def search(query: str, market: str = "stock") -> dict | list:
    """GET /search — search for symbols/instruments."""
    return _get("/search", params={"q": query, "market": market})


def screen(
    asset_type: str = "stock",
    market: str = "america",
    filters: Optional[dict] = None,
    sort_by: str = "market_cap_basic",
    sort_order: str = "desc",
    limit: int = 50,
) -> dict | list:
    """POST /screener — screen assets with optional filters."""
    body = {
        "asset_type": asset_type,
        "market": market,
        "filters": filters or {},
        "sort": {"sortBy": sort_by, "sortOrder": sort_order},
        "range": [0, limit],
    }
    return _post("/screener", body=body)


def market_data(market: str = "crypto", data_type: str = "overview") -> dict | list:
    """GET /market-data — market overview data."""
    return _get("/market-data", params={"market": market, "type": data_type})


def economy_indicators() -> dict | list:
    """GET /economy/indicators — global economy indicators."""
    return _get("/economy/indicators")


def screener_presets() -> dict | list:
    """GET /screener/presets — available screener preset configurations."""
    return _get("/screener/presets")


def screener_filter_options() -> dict | list:
    """GET /screener/filter-options — available screener filter fields."""
    return _get("/screener/filter-options")


def enrich_symbol(symbol: str) -> dict:
    """Aggregate quote, technical analysis, and recent news for a symbol."""
    fmt_symbol = _fmt(symbol)
    return {
        "symbol": fmt_symbol,
        "quote": quote(fmt_symbol),
        "ta": ta(fmt_symbol),
        "news": news(fmt_symbol, limit=5),
    }
