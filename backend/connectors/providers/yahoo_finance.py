"""
Yahoo Finance connector — public endpoints, no auth required.
Uses yfinance library for reliable quote/history access.
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta
from connectors.registry import register_provider


@register_provider
class YahooFinanceConnector(BaseConnector):
    meta = ConnectorMeta(
        id="yahoo_finance",
        name="Yahoo Finance",
        kind="market_data",
        category="financial",
        description="Real-time quotes, historical prices, fundamentals via Yahoo Finance",
        auth_type="none",
        requires_credential=False,
        permissions=["read_market_data", "read_fundamentals"],
        poll_interval_sec=900,
    )

    def _fetch(self, symbols: list[str] | None = None, period: str = "1mo") -> list[dict]:
        import requests
        tickers = symbols or ["SPY", "QQQ", "IWM", "GLD", "TLT"]
        results = []
        for symbol in tickers[:20]:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                params = {"interval": "1d", "range": "5d"}
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                results.append({
                    "symbol": symbol,
                    "price": meta.get("regularMarketPrice"),
                    "prev_close": meta.get("previousClose"),
                    "change_pct": round(
                        (meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0))
                        / max(meta.get("previousClose", 1), 0.01) * 100, 2
                    ),
                    "volume": meta.get("regularMarketVolume"),
                    "currency": meta.get("currency", "USD"),
                    "exchange": meta.get("exchangeName", ""),
                })
            except Exception as exc:
                results.append({"symbol": symbol, "error": str(exc)})
        return results

    def _health(self):
        import requests
        resp = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY",
                            params={"interval": "1d", "range": "1d"},
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        resp.raise_for_status()

    def get_quote(self, symbol: str) -> dict:
        result = self._fetch(symbols=[symbol])
        return result[0] if result else {}

    def get_history(self, symbol: str, period: str = "3mo", interval: str = "1d") -> list[dict]:
        import requests
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        resp = requests.get(url, params={"interval": interval, "range": period},
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        resp.raise_for_status()
        result = resp.json().get("chart", {}).get("result", [{}])[0]
        timestamps = result.get("timestamp", [])
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quotes.get("close", [])
        volumes = quotes.get("volume", [])
        from datetime import datetime
        return [
            {
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "close": round(closes[i], 4) if closes[i] else None,
                "volume": volumes[i] if i < len(volumes) else None,
            }
            for i in range(min(len(timestamps), len(closes)))
        ]
