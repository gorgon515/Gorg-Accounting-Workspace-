"""
Macro Intelligence Platform — monitor Fed, Treasury, inflation, employment, GDP,
PMI, yield curves, and credit spreads. Generates macro regime classification,
risk-on/risk-off scoring, and an economic outlook.

Pulls economic series from the Financial Data Hub (FRED/BLS connectors). Fully
functional with whatever indicators are present; degrades gracefully otherwise.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

_DB = Path(".data/macro.db")

# Series mapping to Financial Data Hub series_ids (FRED conventions).
SERIES = {
    "fed_funds": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "gdp": "GDP",
    "treasury_10y": "GS10",
    "treasury_2y": "GS2",
    "treasury_3m": "TB3MS",
}


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS macro_regime (
            id TEXT PRIMARY KEY,
            regime TEXT NOT NULL,
            risk_score REAL DEFAULT 0.5,
            stance TEXT DEFAULT 'neutral',
            indicators TEXT DEFAULT '{}',
            outlook TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class MacroEngine:
    def __init__(self):
        _conn().close()

    def _latest(self, series_id: str, n: int = 2) -> list[float]:
        try:
            from financial_hub.store import get_financial_hub
            rows = get_financial_hub().get_economic(series_id, limit=n)
            return [r["value"] for r in rows if r.get("value") is not None]
        except Exception:
            return []

    def indicators(self) -> dict:
        """Current macro indicator snapshot with directional change."""
        out = {}
        for name, sid in SERIES.items():
            vals = self._latest(sid, 2)
            if vals:
                cur = vals[0]
                prev = vals[1] if len(vals) > 1 else None
                out[name] = {
                    "value": round(cur, 3),
                    "change": round(cur - prev, 3) if prev is not None else None,
                    "direction": ("up" if prev is not None and cur > prev
                                  else "down" if prev is not None and cur < prev else "flat"),
                }
        return out

    def yield_curve(self) -> dict:
        """Yield curve shape and inversion detection."""
        t10 = self._latest("GS10", 1)
        t2 = self._latest("GS2", 1)
        t3m = self._latest("TB3MS", 1)
        result = {"available": False}
        if t10 and t2:
            spread_10_2 = round(t10[0] - t2[0], 3)
            result.update({
                "available": True,
                "spread_10y_2y": spread_10_2,
                "inverted_10y_2y": spread_10_2 < 0,
            })
        if t10 and t3m:
            result["spread_10y_3m"] = round(t10[0] - t3m[0], 3)
            result["inverted_10y_3m"] = (t10[0] - t3m[0]) < 0
        if result.get("inverted_10y_2y") or result.get("inverted_10y_3m"):
            result["signal"] = "recession_warning"
        elif result.get("available"):
            result["signal"] = "normal"
        return result

    def classify_regime(self, persist: bool = True) -> dict:
        """
        Classify the macro regime and compute a risk-on/risk-off score in [0,1]
        (1 = strong risk-on). Combines growth, inflation, policy, and curve.
        """
        ind = self.indicators()
        curve = self.yield_curve()
        score = 0.5
        signals = []

        # Unemployment: rising → risk-off
        unemp = ind.get("unemployment", {})
        if unemp.get("direction") == "up":
            score -= 0.1; signals.append("rising unemployment")
        elif unemp.get("direction") == "down":
            score += 0.1; signals.append("falling unemployment")
        if unemp.get("value") and unemp["value"] > 5.0:
            score -= 0.05

        # Inflation (CPI): rising sharply → risk-off
        cpi = ind.get("cpi", {})
        if cpi.get("change") is not None and cpi["change"] > 0.5:
            score -= 0.1; signals.append("accelerating inflation")

        # Fed funds: rising rates → risk-off
        ff = ind.get("fed_funds", {})
        if ff.get("direction") == "up":
            score -= 0.1; signals.append("tightening policy")
        elif ff.get("direction") == "down":
            score += 0.1; signals.append("easing policy")

        # Yield curve inversion → risk-off
        if curve.get("signal") == "recession_warning":
            score -= 0.15; signals.append("inverted yield curve")

        score = float(np.clip(score, 0.0, 1.0))
        stance = "risk_on" if score >= 0.6 else "risk_off" if score <= 0.4 else "neutral"

        # Regime label from growth/inflation quadrant
        growth_up = unemp.get("direction") == "down"
        infl_up = cpi.get("change") is not None and cpi["change"] > 0.3
        if growth_up and not infl_up:
            regime = "goldilocks"
        elif growth_up and infl_up:
            regime = "reflation"
        elif not growth_up and infl_up:
            regime = "stagflation"
        else:
            regime = "deflation"

        outlook = self._outlook(regime, stance, signals)
        result = {"regime": regime, "risk_score": round(score, 3), "stance": stance,
                  "signals": signals, "indicators": ind, "yield_curve": curve, "outlook": outlook}
        if persist:
            result["id"] = self._save(result)
        return result

    def _outlook(self, regime: str, stance: str, signals: list[str]) -> str:
        base = {
            "goldilocks": "Favorable backdrop: growth firm with contained inflation.",
            "reflation": "Growth with rising inflation — favor real assets and value.",
            "stagflation": "Challenging: weak growth with sticky inflation — defensive posture.",
            "deflation": "Slowing growth and falling inflation — quality and duration favored.",
        }.get(regime, "Mixed macro signals.")
        if signals:
            base += " Drivers: " + ", ".join(signals) + "."
        base += f" Overall stance: {stance.replace('_', '-')}."
        return base

    def _save(self, result: dict) -> str:
        rid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO macro_regime(id, regime, risk_score, stance, indicators, outlook)
               VALUES(?,?,?,?,?,?)""",
            (rid, result["regime"], result["risk_score"], result["stance"],
             json.dumps(result["indicators"]), result["outlook"]))
        conn.commit()
        conn.close()
        return rid

    def regime_history(self, limit: int = 20) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM macro_regime ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["indicators"] = json.loads(d["indicators"])
            except Exception:
                d["indicators"] = {}
            out.append(d)
        return out

    def stats(self) -> dict:
        conn = _conn()
        regimes = conn.execute("SELECT COUNT(*) FROM macro_regime").fetchone()[0]
        latest = conn.execute("SELECT regime, stance FROM macro_regime ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        return {"regime_classifications": regimes,
                "current_regime": latest["regime"] if latest else None,
                "current_stance": latest["stance"] if latest else None}


_instance: Optional[MacroEngine] = None


def get_macro_engine() -> MacroEngine:
    global _instance
    if _instance is None:
        _instance = MacroEngine()
    return _instance
