"""
Market Signal Detection: identifies actionable signals from market and macro data.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_DB = Path(".data/market_intel.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS market_signal (
            id TEXT PRIMARY KEY,
            signal_type TEXT NOT NULL,
            symbol TEXT DEFAULT '',
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            strength REAL DEFAULT 0.5,
            direction TEXT DEFAULT 'neutral',
            timeframe TEXT DEFAULT 'short',
            supporting_data TEXT DEFAULT '{}',
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


SIGNAL_TYPES = {
    "momentum": "Price momentum above/below moving average",
    "volume_spike": "Unusual trading volume detected",
    "earnings_surprise": "Earnings beat or miss vs expectations",
    "macro_shift": "Significant macro indicator change",
    "sector_rotation": "Capital flows rotating between sectors",
    "yield_curve": "Yield curve shape change",
    "volatility": "VIX spike or compression",
}


class SignalDetector:
    def __init__(self):
        _conn().close()

    def detect_signals(self) -> list[dict]:
        """Run all signal detectors and return newly triggered signals."""
        signals = []
        signals.extend(self._detect_macro_signals())
        signals.extend(self._detect_watchlist_signals())
        return signals

    def _detect_macro_signals(self) -> list[dict]:
        signals = []
        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            fedfunds = hub.get_economic("FEDFUNDS", limit=3)
            if len(fedfunds) >= 2:
                current = fedfunds[0].get("value", 0) or 0
                prev = fedfunds[1].get("value", 0) or 0
                if abs(current - prev) >= 0.25:
                    direction = "up" if current > prev else "down"
                    signals.append(self.create_signal(
                        signal_type="macro_shift",
                        title=f"Fed Funds Rate Changed: {prev:.2f}% → {current:.2f}%",
                        description=f"Federal Reserve rate {'increased' if direction == 'up' else 'decreased'} by {abs(current - prev):.2f}%",
                        strength=0.8,
                        direction=direction,
                        timeframe="medium",
                        supporting_data={"series": "FEDFUNDS", "current": current, "previous": prev},
                    ))
            cpi = hub.get_economic("CPIAUCSL", limit=3)
            if len(cpi) >= 2:
                current = cpi[0].get("value", 0) or 0
                prev = cpi[1].get("value", 0) or 0
                change = current - prev
                if abs(change) > 0.5:
                    direction = "up" if change > 0 else "down"
                    signals.append(self.create_signal(
                        signal_type="macro_shift",
                        title=f"CPI Shift: {prev:.1f} → {current:.1f}",
                        description=f"Consumer Price Index {'rose' if direction == 'up' else 'fell'} by {abs(change):.1f} points",
                        strength=0.7,
                        direction=direction,
                        timeframe="medium",
                        supporting_data={"series": "CPIAUCSL", "current": current, "previous": prev},
                    ))
        except Exception:
            pass
        return signals

    def _detect_watchlist_signals(self) -> list[dict]:
        signals = []
        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            watchlist = hub.get_watchlist()
            for item in watchlist[:20]:
                symbol = item["symbol"]
                prices = hub.get_prices(symbol, limit=5)
                if len(prices) < 2:
                    continue
                current = prices[0].get("close", 0) or 0
                prev = prices[1].get("close", 0) or 1
                if prev == 0:
                    continue
                change_pct = (current - prev) / prev * 100
                if abs(change_pct) >= 5.0:
                    direction = "up" if change_pct > 0 else "down"
                    strength = min(abs(change_pct) / 20, 0.95)
                    signals.append(self.create_signal(
                        signal_type="momentum",
                        symbol=symbol,
                        title=f"{symbol}: {change_pct:+.1f}% price move",
                        description=f"{item.get('name', symbol)} moved {change_pct:+.1f}% to ${current:.2f}",
                        strength=strength,
                        direction=direction,
                        timeframe="short",
                        supporting_data={"current": current, "previous": prev, "change_pct": change_pct},
                    ))
        except Exception:
            pass
        return signals

    def create_signal(self, signal_type: str, title: str, description: str = "",
                      symbol: str = "", strength: float = 0.5, direction: str = "neutral",
                      timeframe: str = "short", supporting_data: dict | None = None,
                      status: str = "active") -> dict:
        sig_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO market_signal
               (id, signal_type, symbol, title, description, strength, direction, timeframe,
                supporting_data, status) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (sig_id, signal_type, symbol, title, description, strength, direction,
             timeframe, json.dumps(supporting_data or {}), status),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM market_signal WHERE id=?", (sig_id,)).fetchone()
        conn.close()
        return self._fmt(row)

    def list_signals(self, signal_type: str | None = None, status: str = "active",
                     symbol: str | None = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses = ["status=?"]; params: list = [status]
        if signal_type:
            clauses.append("signal_type=?"); params.append(signal_type)
        if symbol:
            clauses.append("symbol=?"); params.append(symbol)
        rows = conn.execute(
            f"SELECT * FROM market_signal WHERE {' AND '.join(clauses)} ORDER BY strength DESC, created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def dismiss_signal(self, signal_id: str) -> Optional[dict]:
        conn = _conn()
        conn.execute("UPDATE market_signal SET status='dismissed' WHERE id=?", (signal_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM market_signal WHERE id=?", (signal_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def _fmt(self, row) -> dict:
        d = dict(row)
        try:
            d["supporting_data"] = json.loads(d["supporting_data"])
        except Exception:
            d["supporting_data"] = {}
        return d

    def stats(self) -> dict:
        conn = _conn()
        active = conn.execute(
            "SELECT COUNT(*) FROM market_signal WHERE status='active'"
        ).fetchone()[0]
        by_type = {}
        rows = conn.execute(
            "SELECT signal_type, COUNT(*) as cnt FROM market_signal WHERE status='active' GROUP BY signal_type"
        ).fetchall()
        for row in rows:
            by_type[row["signal_type"]] = row["cnt"]
        conn.close()
        return {"active_signals": active, "by_type": by_type}


_instance: Optional[SignalDetector] = None


def get_signal_detector() -> SignalDetector:
    global _instance
    if _instance is None:
        _instance = SignalDetector()
    return _instance
