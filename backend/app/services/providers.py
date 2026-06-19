"""Additional market-data provider adapters.

Financial Modeling Prep, Alpha Vantage, and SEC company-filings adapters that
conform to the same normalized shapes as the Yahoo provider. Each separates
``normalize_*`` (pure, unit-tested with fixtures) from the live ``fetch``
(network + API key), so normalization is verifiable offline and the live path
works on a machine with network + keys.
"""
from __future__ import annotations

import os
from typing import Optional

from .market_data import DataUnavailable, YahooProvider

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


def _get(url: str, params: dict, headers: Optional[dict] = None, timeout: int = 10) -> dict:
    if requests is None:
        raise DataUnavailable("requests not installed")
    try:
        r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise DataUnavailable(f"{url}: {exc}") from exc


class FMPProvider:
    """Financial Modeling Prep (needs FMP_API_KEY)."""

    name = "fmp"
    BASE = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FMP_API_KEY", "")

    @staticmethod
    def normalize_quote(raw: list | dict) -> dict:
        row = raw[0] if isinstance(raw, list) and raw else (raw if isinstance(raw, dict) else {})
        if not row:
            raise DataUnavailable("empty FMP quote")
        return {
            "symbol": str(row.get("symbol", "")).upper(),
            "price": row.get("price"),
            "change": row.get("change"),
            "change_percent": row.get("changesPercentage"),
            "currency": "USD",
            "source": "fmp",
        }

    @staticmethod
    def normalize_fundamentals(profile: dict, ratios: dict) -> dict:
        return {
            "symbol": str(profile.get("symbol", "")).upper(),
            "price": profile.get("price"),
            "market_cap": profile.get("mktCap"),
            "pe": ratios.get("peRatioTTM"),
            "pb": ratios.get("priceToBookRatioTTM"),
            "roe": ratios.get("returnOnEquityTTM"),
            "net_margin": ratios.get("netProfitMarginTTM"),
            "debt_to_equity": ratios.get("debtEquityRatioTTM"),
            "current_ratio": ratios.get("currentRatioTTM"),
            "dividend_yield": ratios.get("dividendYieldTTM"),
        }

    def quote(self, symbol: str) -> dict:
        if not self.api_key:
            raise DataUnavailable("FMP_API_KEY not set")
        return self.normalize_quote(_get(f"{self.BASE}/quote/{symbol}", {"apikey": self.api_key}))


class AlphaVantageProvider:
    """Alpha Vantage (needs ALPHA_VANTAGE_KEY)."""

    name = "alphavantage"
    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ALPHA_VANTAGE_KEY", "")

    @staticmethod
    def normalize_quote(raw: dict) -> dict:
        q = raw.get("Global Quote", raw) or {}
        if not q.get("01. symbol") and not q.get("symbol"):
            raise DataUnavailable("empty Alpha Vantage quote")
        pct = q.get("10. change percent", "0%")
        return {
            "symbol": (q.get("01. symbol") or q.get("symbol", "")).upper(),
            "price": _f(q.get("05. price")),
            "change": _f(q.get("09. change")),
            "change_percent": _f(str(pct).rstrip("%")),
            "currency": "USD",
            "source": "alphavantage",
        }

    @staticmethod
    def normalize_history(raw: dict) -> dict:
        series = raw.get("Time Series (Daily)") or {}
        if not series:
            raise DataUnavailable("empty Alpha Vantage history")
        dates = sorted(series.keys())
        prices = [_f(series[d].get("4. close")) for d in dates]
        return {"symbol": (raw.get("Meta Data", {}).get("2. Symbol", "")).upper(),
                "dates": dates, "prices": [p for p in prices if p is not None], "source": "alphavantage"}

    def quote(self, symbol: str) -> dict:
        if not self.api_key:
            raise DataUnavailable("ALPHA_VANTAGE_KEY not set")
        return self.normalize_quote(_get(self.BASE, {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key}))


class SECFilingsProvider:
    """SEC company filings via data.sec.gov submissions JSON (no key; UA required)."""

    name = "sec_filings"
    BASE = "https://data.sec.gov/submissions/CIK{cik}.json"
    UA = {"User-Agent": os.environ.get("HELIOS_HTTP_UA", "HELIOS Accounting Intelligence (contact: helios@example.com)")}

    @staticmethod
    def normalize_filings(raw: dict, limit: int = 20) -> dict:
        recent = (raw.get("filings", {}) or {}).get("recent", {}) or {}
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accession = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        out = []
        for i in range(min(limit, len(forms))):
            out.append({"form": forms[i], "filed": dates[i] if i < len(dates) else None,
                        "accession": accession[i] if i < len(accession) else None,
                        "document": docs[i] if i < len(docs) else None})
        return {"entity": raw.get("name"), "cik": raw.get("cik"), "filings": out, "source": "sec_filings"}

    def filings(self, cik: str, limit: int = 20) -> dict:
        cik10 = str(cik).zfill(10)
        return self.normalize_filings(_get(self.BASE.format(cik=cik10), {}, headers=self.UA), limit)


def _f(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# Provider selection by env, default Yahoo.
def select_provider(name: Optional[str] = None):
    name = (name or os.environ.get("HELIOS_MARKET_PROVIDER", "yahoo")).lower()
    return {"yahoo": YahooProvider, "fmp": FMPProvider, "alphavantage": AlphaVantageProvider}.get(name, YahooProvider)()
