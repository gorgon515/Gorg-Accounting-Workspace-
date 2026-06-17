"""Market-data connector layer: ingestion, caching, normalization, storage.

A small provider abstraction so the rest of the engine never knows where prices
came from. Ships with a Yahoo provider (no key) and is structured so Alpha
Vantage / Polygon / Financial Modeling Prep slot in as additional providers
behind the same ``Provider`` interface and the same normalized shapes.

Network is treated as optional: failures raise ``DataUnavailable`` (the API maps
that to 503), and every quant endpoint also accepts an explicit price series so
the engine is fully usable offline.
"""
from __future__ import annotations

import time
from typing import Optional

try:
    import requests
except Exception:  # pragma: no cover - requests is a declared dependency
    requests = None  # type: ignore


class DataUnavailable(RuntimeError):
    """Raised when a provider cannot return data (network, rate limit, unknown symbol)."""


# ---- normalized shapes --------------------------------------------------------
# Quote:   {symbol, price, change, change_percent, currency, source}
# History: {symbol, dates: [iso...], prices: [close...], source}


class _TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        hit = self._store.get(key)
        if not hit:
            return None
        ts, value = hit
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: object):
        self._store[key] = (time.time(), value)


class YahooProvider:
    """Yahoo Finance public endpoints (no API key)."""

    name = "yahoo"
    QUOTE = "https://query1.finance.yahoo.com/v7/finance/quote"
    CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    _UA = {"User-Agent": "Mozilla/5.0 (HELIOS sidecar)"}

    def _get(self, url: str, params: dict) -> dict:
        if requests is None:
            raise DataUnavailable("requests not installed")
        try:
            resp = requests.get(url, params=params, headers=self._UA, timeout=8)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - normalize all network errors
            raise DataUnavailable(f"yahoo request failed: {exc}") from exc

    def quote(self, symbol: str) -> dict:
        data = self._get(self.QUOTE, {"symbols": symbol})
        rows = (data.get("quoteResponse") or {}).get("result") or []
        if not rows:
            raise DataUnavailable(f"no quote for {symbol}")
        q = rows[0]
        return {
            "symbol": q.get("symbol", symbol).upper(),
            "price": q.get("regularMarketPrice"),
            "change": q.get("regularMarketChange"),
            "change_percent": q.get("regularMarketChangePercent"),
            "currency": q.get("currency"),
            "source": self.name,
        }

    def history(self, symbol: str, rng: str = "6mo", interval: str = "1d") -> dict:
        data = self._get(self.CHART.format(symbol=symbol), {"range": rng, "interval": interval})
        chart = (data.get("chart") or {}).get("result") or []
        if not chart:
            raise DataUnavailable(f"no history for {symbol}")
        res = chart[0]
        stamps = res.get("timestamp") or []
        closes = (((res.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
        dates, prices = [], []
        for ts, close in zip(stamps, closes):
            if close is None:
                continue
            dates.append(time.strftime("%Y-%m-%d", time.gmtime(ts)))
            prices.append(float(close))
        if len(prices) < 2:
            raise DataUnavailable(f"insufficient history for {symbol}")
        return {"symbol": symbol.upper(), "dates": dates, "prices": prices, "source": self.name}


class MarketData:
    """Facade over providers with TTL caching. Default provider: Yahoo."""

    def __init__(self, provider: Optional[object] = None, quote_ttl: float = 30, history_ttl: float = 900):
        self.provider = provider or YahooProvider()
        self._quotes = _TTLCache(quote_ttl)
        self._history = _TTLCache(history_ttl)
        self.quote_ttl = quote_ttl
        self.history_ttl = history_ttl
        self._refreshed: dict[str, float] = {}  # key → last successful fetch time

    def _mark(self, key: str) -> None:
        self._refreshed[key] = time.time()

    def quote(self, symbol: str) -> dict:
        symbol = symbol.upper().strip()
        cached = self._quotes.get(symbol)
        if cached:
            return {**cached, "cached": True, "age_seconds": round(time.time() - self._refreshed.get(f"q:{symbol}", time.time()), 1)}
        fresh = self.provider.quote(symbol)
        self._quotes.set(symbol, fresh)
        self._mark(f"q:{symbol}")
        return {**fresh, "cached": False, "age_seconds": 0}

    def history(self, symbol: str, rng: str = "6mo", interval: str = "1d") -> dict:
        symbol = symbol.upper().strip()
        key = f"{symbol}:{rng}:{interval}"
        cached = self._history.get(key)
        if cached:
            return {**cached, "cached": True}
        fresh = self.provider.history(symbol, rng, interval)
        self._history.set(key, fresh)
        self._mark(f"h:{key}")
        return {**fresh, "cached": False}

    def prices(self, symbol: str, rng: str = "6mo") -> list[float]:
        """Convenience: just the close series for the quant engine."""
        return self.history(symbol, rng)["prices"]

    def freshness(self) -> dict:
        """Per-key age and staleness — lets the UI show refresh times / stale data."""
        now = time.time()
        out = {}
        for key, ts in self._refreshed.items():
            ttl = self.quote_ttl if key.startswith("q:") else self.history_ttl
            age = now - ts
            out[key] = {"age_seconds": round(age, 1), "stale": age > ttl, "ttl": ttl}
        return out

    def is_stale(self, key: str) -> bool:
        ts = self._refreshed.get(key)
        if ts is None:
            return True
        ttl = self.quote_ttl if key.startswith("q:") else self.history_ttl
        return (time.time() - ts) > ttl


# Module-level singleton reused across requests so the cache is shared.
market = MarketData()
