"""
Factor Research Framework — factor library (value, quality, momentum, growth,
volatility, size, profitability, dividend, custom), cross-sectional ranking,
factor persistence/decay, attribution, and combinations.

Scores pull fundamentals/prices from the Financial Data Hub. Each factor returns
a 0-100 score (higher = more attractive exposure to that factor).
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, Sequence
import numpy as np

_DB = Path(".data/factors.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS custom_factor (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            definition TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS factor_snapshot (
            id TEXT PRIMARY KEY,
            factor TEXT NOT NULL,
            symbol TEXT NOT NULL,
            score REAL,
            recorded_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _scale(value: Optional[float], good: float, bad: float) -> Optional[float]:
    """Linear scale value→[0,100] where `good`→100 and `bad`→0."""
    if value is None:
        return None
    if good == bad:
        return 50.0
    return _clamp((value - bad) / (good - bad) * 100.0)


FACTOR_NAMES = ["value", "quality", "momentum", "growth", "volatility",
                "size", "profitability", "dividend"]


class FactorLibrary:
    def __init__(self):
        _conn().close()

    # ── individual factor scores ────────────────────────────────────────────

    def value(self, f: dict) -> Optional[float]:
        scores = [
            _scale(f.get("pe_ratio"), good=8, bad=40),
            _scale(f.get("pb_ratio"), good=1, bad=8),
            _scale(f.get("ev_ebitda"), good=5, bad=20),
            _scale(f.get("fcf_yield"), good=0.10, bad=0.0),
        ]
        return self._avg(scores)

    def quality(self, f: dict) -> Optional[float]:
        scores = [
            _scale(f.get("roe"), good=0.25, bad=0.0),
            _scale(f.get("roa"), good=0.15, bad=0.0),
            _scale(f.get("debt_to_equity"), good=0.0, bad=2.0),
            _scale(f.get("current_ratio"), good=2.5, bad=0.8),
        ]
        return self._avg(scores)

    def momentum(self, prices: Optional[Sequence[float]]) -> Optional[float]:
        if not prices or len(prices) < 20:
            return None
        p = np.asarray(prices, dtype=float)
        # 12-1 momentum proxy with available history
        ret = (p[-1] / p[0]) - 1.0
        return _scale(ret, good=0.5, bad=-0.3)

    def growth(self, f: dict) -> Optional[float]:
        scores = [
            _scale(f.get("revenue_growth"), good=0.30, bad=-0.05),
            _scale(f.get("earnings_growth"), good=0.30, bad=-0.10),
        ]
        return self._avg(scores)

    def volatility(self, prices: Optional[Sequence[float]]) -> Optional[float]:
        if not prices or len(prices) < 20:
            return None
        p = np.asarray(prices, dtype=float)
        rets = np.diff(p) / p[:-1]
        ann_vol = float(np.std(rets, ddof=1) * np.sqrt(252))
        # Low-volatility factor: lower vol → higher score
        return _scale(ann_vol, good=0.10, bad=0.60)

    def size(self, f: dict) -> Optional[float]:
        mcap = f.get("market_cap")
        if mcap is None or mcap <= 0:
            return None
        # Small-cap tilt: smaller → higher score (log scale, $100M→100, $1T→0)
        log_cap = np.log10(mcap)
        return _scale(log_cap, good=8.0, bad=12.0)

    def profitability(self, f: dict) -> Optional[float]:
        scores = [
            _scale(f.get("gross_margin"), good=0.60, bad=0.10),
            _scale(f.get("operating_margin"), good=0.30, bad=0.0),
            _scale(f.get("net_margin"), good=0.20, bad=0.0),
        ]
        return self._avg(scores)

    def dividend(self, f: dict) -> Optional[float]:
        scores = [
            _scale(f.get("dividend_yield"), good=0.05, bad=0.0),
            _scale(f.get("payout_ratio"), good=0.45, bad=0.90),
        ]
        return self._avg(scores)

    def _avg(self, scores: list[Optional[float]]) -> Optional[float]:
        valid = [s for s in scores if s is not None]
        if not valid:
            return None
        return round(float(np.mean(valid)), 2)

    # ── aggregation & data access ───────────────────────────────────────────

    def score_symbol(self, symbol: str, fundamentals: Optional[dict] = None,
                     prices: Optional[Sequence[float]] = None) -> dict:
        f = fundamentals or self._fetch_fundamentals(symbol)
        p = prices if prices is not None else self._fetch_prices(symbol)
        return {
            "value": self.value(f),
            "quality": self.quality(f),
            "momentum": self.momentum(p),
            "growth": self.growth(f),
            "volatility": self.volatility(p),
            "size": self.size(f),
            "profitability": self.profitability(f),
            "dividend": self.dividend(f),
        }

    def _fetch_fundamentals(self, symbol: str) -> dict:
        # Fundamentals connectors are credential-gated; return empty when absent.
        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            conn = hub_conn = None  # fundamentals stored per metric
            rows = []
            try:
                import sqlite3 as _sq
                c = _sq.connect(".data/financial_hub.db")
                c.row_factory = _sq.Row
                rows = c.execute(
                    "SELECT metric, value FROM fundamental WHERE symbol=? ORDER BY period DESC", (symbol,)
                ).fetchall()
                c.close()
            except Exception:
                rows = []
            return {r["metric"]: r["value"] for r in rows}
        except Exception:
            return {}

    def _fetch_prices(self, symbol: str) -> list[float]:
        try:
            from financial_hub.store import get_financial_hub
            bars = get_financial_hub().get_prices(symbol, limit=252)
            return [b["close"] for b in reversed(bars) if b.get("close") is not None]
        except Exception:
            return []

    def rank(self, symbols: Sequence[str], factor: str = "value") -> list[dict]:
        """Cross-sectional ranking of symbols by a factor."""
        scored = []
        for s in symbols:
            sc = self.score_symbol(s)
            val = sc.get(factor)
            if val is not None:
                scored.append({"symbol": s, "score": val, "all_factors": sc})
        scored.sort(key=lambda x: -x["score"])
        for i, item in enumerate(scored):
            item["rank"] = i + 1
            item["percentile"] = round((len(scored) - i) / len(scored) * 100, 1) if scored else 0
        return scored

    def combine(self, symbols: Sequence[str], weights: dict[str, float]) -> list[dict]:
        """Multi-factor composite score with custom factor weights."""
        total_w = sum(weights.values()) or 1.0
        out = []
        for s in symbols:
            sc = self.score_symbol(s)
            composite, used = 0.0, 0.0
            for fname, w in weights.items():
                v = sc.get(fname)
                if v is not None:
                    composite += w * v
                    used += w
            if used > 0:
                out.append({"symbol": s, "composite_score": round(composite / used, 2),
                            "factors": sc})
        out.sort(key=lambda x: -x["composite_score"])
        return out

    def persistence(self, symbol: str, factor: str) -> dict:
        """Measure factor-score persistence over recorded snapshots."""
        conn = _conn()
        rows = conn.execute(
            "SELECT score, recorded_at FROM factor_snapshot WHERE symbol=? AND factor=? ORDER BY recorded_at",
            (symbol, factor)).fetchall()
        conn.close()
        scores = [r["score"] for r in rows if r["score"] is not None]
        if len(scores) < 2:
            return {"symbol": symbol, "factor": factor, "persistence": None,
                    "n_observations": len(scores)}
        arr = np.asarray(scores)
        # autocorrelation lag-1 as a persistence proxy
        if arr.std() == 0:
            autocorr = 1.0
        else:
            autocorr = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
        decay = round(1.0 - abs(autocorr), 4)
        return {"symbol": symbol, "factor": factor,
                "persistence": round(autocorr, 4), "decay": decay,
                "n_observations": len(scores), "latest": scores[-1]}

    def snapshot(self, symbols: Sequence[str]) -> int:
        """Record current factor scores for later persistence/decay analysis."""
        conn = _conn()
        count = 0
        for s in symbols:
            sc = self.score_symbol(s)
            for fname, val in sc.items():
                conn.execute(
                    "INSERT INTO factor_snapshot(id, factor, symbol, score) VALUES(?,?,?,?)",
                    (str(uuid.uuid4()), fname, s, val))
                count += 1
        conn.commit()
        conn.close()
        return count

    def create_custom(self, name: str, description: str, definition: dict) -> dict:
        """Define a custom factor as a weighted blend of base factors."""
        fid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            "INSERT INTO custom_factor(id, name, description, definition) VALUES(?,?,?,?)",
            (fid, name, description, json.dumps(definition)))
        conn.commit()
        conn.close()
        return {"id": fid, "name": name, "description": description, "definition": definition}

    def list_custom(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM custom_factor ORDER BY created_at DESC").fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["definition"] = json.loads(d["definition"])
            except Exception:
                d["definition"] = {}
            out.append(d)
        return out

    def library(self) -> list[dict]:
        descriptions = {
            "value": "Cheapness: P/E, P/B, EV/EBITDA, FCF yield",
            "quality": "Profitability & balance-sheet strength: ROE, ROA, leverage",
            "momentum": "Trailing price momentum",
            "growth": "Revenue & earnings growth",
            "volatility": "Low-volatility anomaly (lower vol scores higher)",
            "size": "Small-cap tilt",
            "profitability": "Margin structure: gross/operating/net",
            "dividend": "Dividend yield & sustainability",
        }
        return [{"name": n, "description": descriptions[n]} for n in FACTOR_NAMES]

    def stats(self) -> dict:
        conn = _conn()
        custom = conn.execute("SELECT COUNT(*) FROM custom_factor").fetchone()[0]
        snaps = conn.execute("SELECT COUNT(*) FROM factor_snapshot").fetchone()[0]
        conn.close()
        return {"base_factors": len(FACTOR_NAMES), "custom_factors": custom, "snapshots": snaps}


_instance: Optional[FactorLibrary] = None


def get_factor_library() -> FactorLibrary:
    global _instance
    if _instance is None:
        _instance = FactorLibrary()
    return _instance
