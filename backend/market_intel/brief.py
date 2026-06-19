"""
Market Intelligence Center: daily market briefs, sector analysis, macro monitoring.
Aggregates financial signals into actionable market intelligence.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

_DB = Path(".data/market_intel.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS market_brief (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            headline TEXT NOT NULL,
            executive_summary TEXT DEFAULT '',
            market_overview TEXT DEFAULT '{}',
            sector_performance TEXT DEFAULT '{}',
            macro_signals TEXT DEFAULT '{}',
            key_events TEXT DEFAULT '[]',
            watchlist_highlights TEXT DEFAULT '[]',
            risk_score REAL DEFAULT 0.5,
            sentiment TEXT DEFAULT 'neutral',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sector_analysis (
            id TEXT PRIMARY KEY,
            sector TEXT NOT NULL,
            date TEXT NOT NULL,
            performance REAL DEFAULT 0.0,
            trend TEXT DEFAULT 'neutral',
            key_drivers TEXT DEFAULT '[]',
            notable_movers TEXT DEFAULT '[]',
            risk_level TEXT DEFAULT 'medium',
            summary TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS macro_snapshot (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            gdp_growth REAL,
            inflation_rate REAL,
            unemployment_rate REAL,
            fed_funds_rate REAL,
            yield_10y REAL,
            vix REAL,
            signals TEXT DEFAULT '{}',
            outlook TEXT DEFAULT 'neutral',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist_alert (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL,
            change_pct REAL,
            severity TEXT DEFAULT 'medium',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


SECTORS = [
    "Technology", "Healthcare", "Financials", "Energy", "Consumer Discretionary",
    "Consumer Staples", "Industrials", "Materials", "Real Estate", "Utilities",
    "Communication Services",
]

SENTIMENT_KEYWORDS = {
    "bullish": ["rally", "surge", "record high", "outperform", "beat expectations", "strong growth"],
    "bearish": ["decline", "selloff", "miss", "downturn", "recession", "weak", "contraction"],
    "neutral": ["mixed", "stable", "unchanged", "flat", "in line"],
}


class MarketBriefing:
    def __init__(self):
        _conn().close()

    def generate_daily_brief(self) -> dict:
        """Generate daily market brief from available financial data and live intelligence."""
        date = datetime.utcnow().strftime("%Y-%m-%d")
        macro = self._gather_macro()
        watchlist_highlights = self._gather_watchlist_highlights()
        key_events = self._gather_key_events()
        risk_score, sentiment = self._compute_risk_sentiment(macro, key_events)
        headline = self._generate_headline(sentiment, macro, key_events)
        exec_summary = self._generate_summary(sentiment, macro, key_events, watchlist_highlights)
        brief_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT OR REPLACE INTO market_brief
               (id, date, headline, executive_summary, macro_signals, key_events,
                watchlist_highlights, risk_score, sentiment)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (brief_id, date, headline, exec_summary,
             json.dumps(macro), json.dumps(key_events),
             json.dumps(watchlist_highlights), risk_score, sentiment),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM market_brief WHERE id=?", (brief_id,)).fetchone()
        conn.close()
        return self._fmt_brief(row)

    def _gather_macro(self) -> dict:
        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            macro = {}
            for series_id in ("GDP", "CPIAUCSL", "UNRATE", "FEDFUNDS", "GS10"):
                rows = hub.get_economic(series_id, limit=1)
                if rows:
                    macro[series_id] = rows[0].get("value")
            return macro
        except Exception:
            return {}

    def _gather_watchlist_highlights(self) -> list[dict]:
        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            watchlist = hub.get_watchlist()
            highlights = []
            for item in watchlist[:10]:
                symbol = item["symbol"]
                prices = hub.get_prices(symbol, limit=2)
                if len(prices) >= 2:
                    current = prices[0].get("close", 0) or 0
                    prev = prices[1].get("close", 0) or 1
                    change_pct = ((current - prev) / prev * 100) if prev else 0
                    highlights.append({
                        "symbol": symbol,
                        "name": item.get("name", ""),
                        "price": current,
                        "change_pct": round(change_pct, 2),
                    })
            return highlights
        except Exception:
            return []

    def _gather_key_events(self) -> list[str]:
        try:
            from live_intelligence.monitor import get_monitor
            monitor = get_monitor()
            items = monitor.list_items(domain="markets", limit=5)
            items += monitor.list_items(domain="finance", limit=3)
            return [item.get("title", "")[:100] for item in items[:8] if item.get("title")]
        except Exception:
            return []

    def _compute_risk_sentiment(self, macro: dict, events: list[str]) -> tuple[float, str]:
        event_text = " ".join(events).lower()
        bullish_count = sum(1 for kw in SENTIMENT_KEYWORDS["bullish"] if kw in event_text)
        bearish_count = sum(1 for kw in SENTIMENT_KEYWORDS["bearish"] if kw in event_text)
        if bearish_count > bullish_count + 1:
            sentiment = "bearish"
            risk = 0.7
        elif bullish_count > bearish_count + 1:
            sentiment = "bullish"
            risk = 0.3
        else:
            sentiment = "neutral"
            risk = 0.5
        unrate = macro.get("UNRATE")
        if unrate and unrate > 5.0:
            risk = min(risk + 0.1, 0.95)
        return round(risk, 2), sentiment

    def _generate_headline(self, sentiment: str, macro: dict, events: list[str]) -> str:
        date = datetime.utcnow().strftime("%B %d, %Y")
        if events:
            return f"Market Intelligence Brief — {date}: {events[0][:80]}"
        return f"Market Intelligence Brief — {date}: {sentiment.title()} sentiment across markets"

    def _generate_summary(self, sentiment: str, macro: dict, events: list[str],
                          watchlist: list[dict]) -> str:
        parts = [f"Market sentiment is {sentiment}."]
        if macro.get("FEDFUNDS"):
            parts.append(f"Fed Funds Rate: {macro['FEDFUNDS']:.2f}%.")
        if macro.get("UNRATE"):
            parts.append(f"Unemployment: {macro['UNRATE']:.1f}%.")
        if macro.get("CPIAUCSL"):
            parts.append(f"CPI: {macro['CPIAUCSL']:.1f}.")
        if events:
            parts.append(f"Key events: {'; '.join(events[:3])}.")
        gainers = [w for w in watchlist if (w.get("change_pct") or 0) > 0]
        losers = [w for w in watchlist if (w.get("change_pct") or 0) < 0]
        if gainers:
            parts.append(f"Watchlist gainers: {', '.join(w['symbol'] for w in gainers[:3])}.")
        if losers:
            parts.append(f"Watchlist decliners: {', '.join(w['symbol'] for w in losers[:3])}.")
        return " ".join(parts)

    def _fmt_brief(self, row) -> dict:
        d = dict(row)
        for f in ("market_overview", "sector_performance", "macro_signals", "signals"):
            if f in d:
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = {}
        for f in ("key_events", "watchlist_highlights", "key_drivers", "notable_movers"):
            if f in d:
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = []
        return d

    def get_latest_brief(self) -> Optional[dict]:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM market_brief ORDER BY date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return self._fmt_brief(row) if row else None

    def list_briefs(self, limit: int = 10) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM market_brief ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [self._fmt_brief(r) for r in rows]

    def create_watchlist_alert(self, symbol: str, alert_type: str, title: str,
                                description: str = "", price: float = 0.0,
                                change_pct: float = 0.0, severity: str = "medium") -> dict:
        alert_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO watchlist_alert(id, symbol, alert_type, title, description,
               price, change_pct, severity) VALUES(?,?,?,?,?,?,?,?)""",
            (alert_id, symbol, alert_type, title, description, price, change_pct, severity),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM watchlist_alert WHERE id=?", (alert_id,)).fetchone()
        conn.close()
        return dict(row)

    def list_watchlist_alerts(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM watchlist_alert WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM watchlist_alert ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def snapshot_macro(self, gdp_growth: float | None = None, inflation_rate: float | None = None,
                       unemployment_rate: float | None = None, fed_funds_rate: float | None = None,
                       yield_10y: float | None = None, vix: float | None = None,
                       outlook: str = "neutral") -> dict:
        snap_id = str(uuid.uuid4())
        date = datetime.utcnow().strftime("%Y-%m-%d")
        conn = _conn()
        conn.execute(
            """INSERT INTO macro_snapshot(id, date, gdp_growth, inflation_rate, unemployment_rate,
               fed_funds_rate, yield_10y, vix, outlook) VALUES(?,?,?,?,?,?,?,?,?)""",
            (snap_id, date, gdp_growth, inflation_rate, unemployment_rate,
             fed_funds_rate, yield_10y, vix, outlook),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM macro_snapshot WHERE id=?", (snap_id,)).fetchone()
        conn.close()
        return dict(row)

    def get_macro_snapshot(self) -> Optional[dict]:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM macro_snapshot ORDER BY date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def stats(self) -> dict:
        conn = _conn()
        briefs = conn.execute("SELECT COUNT(*) FROM market_brief").fetchone()[0]
        alerts = conn.execute("SELECT COUNT(*) FROM watchlist_alert").fetchone()[0]
        snapshots = conn.execute("SELECT COUNT(*) FROM macro_snapshot").fetchone()[0]
        conn.close()
        return {"total_briefs": briefs, "watchlist_alerts": alerts, "macro_snapshots": snapshots}


_instance: Optional[MarketBriefing] = None


def get_market_briefing() -> MarketBriefing:
    global _instance
    if _instance is None:
        _instance = MarketBriefing()
    return _instance
