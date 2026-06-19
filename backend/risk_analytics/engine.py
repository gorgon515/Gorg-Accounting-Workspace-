"""
Risk Analytics Platform — VaR, Expected Shortfall, stress testing, scenario
analysis, factor/sector exposure, concentration, correlation, tail-risk
detection, and a composite portfolio health score.

Real implementations over portfolio holdings and the Financial Data Hub's
price history. Outputs feed the Portfolio Command Center and Risk Officer agent.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, Sequence
import numpy as np

_DB = Path(".data/risk_analytics.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS risk_report (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT DEFAULT '',
            name TEXT DEFAULT '',
            report TEXT DEFAULT '{}',
            health_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS stress_scenario (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            shocks TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


# Built-in historical stress scenarios (market shock magnitudes, simplified).
BUILTIN_SCENARIOS = {
    "2008_financial_crisis": {"name": "2008 Financial Crisis", "equity_shock": -0.40, "vol_mult": 2.5, "corr_shift": 0.3},
    "2020_covid_crash": {"name": "2020 COVID Crash", "equity_shock": -0.34, "vol_mult": 3.0, "corr_shift": 0.4},
    "2022_rate_shock": {"name": "2022 Rate Shock", "equity_shock": -0.25, "vol_mult": 1.8, "corr_shift": 0.2},
    "dotcom_2000": {"name": "Dotcom Bust 2000", "equity_shock": -0.45, "vol_mult": 2.0, "corr_shift": 0.25},
    "flash_crash": {"name": "Flash Crash", "equity_shock": -0.10, "vol_mult": 4.0, "corr_shift": 0.5},
}


def _portfolio_returns(holdings: list[dict], lookback: int = 252) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (weights, returns_matrix n_assets x n_periods, symbols)."""
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    series, weights, symbols = {}, [], []
    for h in holdings:
        sym = h.get("symbol")
        bars = hub.get_prices(sym, limit=lookback)
        closes = [b.get("close") for b in reversed(bars) if b.get("close") is not None]
        if len(closes) >= 3:
            arr = np.asarray(closes, dtype=float)
            series[sym] = np.diff(arr) / arr[:-1]
    for h in holdings:
        if h.get("symbol") in series:
            symbols.append(h["symbol"])
            weights.append(h.get("weight", 0.0))
    if not symbols:
        return np.array([]), np.empty((0, 0)), []
    min_len = min(len(series[s]) for s in symbols)
    matrix = np.vstack([series[s][-min_len:] for s in symbols])
    w = np.asarray(weights, dtype=float)
    w = w / w.sum() if w.sum() > 0 else np.ones(len(symbols)) / len(symbols)
    return w, matrix, symbols


class RiskEngine:
    def __init__(self):
        conn = _conn()
        for sid, sc in BUILTIN_SCENARIOS.items():
            ex = conn.execute("SELECT id FROM stress_scenario WHERE id=?", (sid,)).fetchone()
            if not ex:
                conn.execute(
                    "INSERT INTO stress_scenario(id, name, description, shocks) VALUES(?,?,?,?)",
                    (sid, sc["name"], "", json.dumps(sc)))
        conn.commit()
        conn.close()

    def analyze(self, holdings: list[dict], name: str = "", portfolio_id: str = "",
                level: float = 0.95, persist: bool = True) -> dict:
        w, matrix, symbols = _portfolio_returns(holdings)
        if matrix.size == 0:
            return {"error": "no price history for holdings", "health_score": None}

        port_returns = w @ matrix
        report = {
            "symbols": symbols,
            "weights": {symbols[i]: round(float(w[i]), 4) for i in range(len(symbols))},
            "var": self._var(port_returns, level),
            "expected_shortfall": self._es(port_returns, level),
            "volatility_annual": round(float(np.std(port_returns, ddof=1) * np.sqrt(252)), 4),
            "concentration": self.concentration(w, symbols),
            "correlation": self.correlation_analysis(matrix, symbols),
            "tail_risk": self.tail_risk(port_returns),
            "drawdown": self._drawdown(port_returns),
        }
        health = self.health_score(report)
        report["health_score"] = health
        if persist:
            report["id"] = self._save(portfolio_id, name, report, health)
        return report

    def _var(self, returns: np.ndarray, level: float) -> dict:
        hist = float(np.percentile(returns, (1 - level) * 100))
        mu, sigma = float(np.mean(returns)), float(np.std(returns, ddof=1))
        from scipy.stats import norm
        param = float(mu + sigma * norm.ppf(1 - level))
        return {"level": level, "historical": round(hist, 5), "parametric": round(param, 5),
                "historical_pct": round(hist * 100, 3)}

    def _es(self, returns: np.ndarray, level: float) -> dict:
        var = np.percentile(returns, (1 - level) * 100)
        tail = returns[returns <= var]
        es = float(np.mean(tail)) if tail.size else float(var)
        return {"level": level, "value": round(es, 5), "value_pct": round(es * 100, 3)}

    def _drawdown(self, returns: np.ndarray) -> dict:
        equity = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / peak
        return {"max_drawdown": round(float(np.min(dd)), 4),
                "current_drawdown": round(float(dd[-1]), 4)}

    def concentration(self, w: np.ndarray, symbols: list[str]) -> dict:
        herfindahl = float(np.sum(w ** 2))
        top = sorted(zip(symbols, w), key=lambda x: -x[1])[:3]
        return {
            "herfindahl": round(herfindahl, 4),
            "effective_positions": round(float(1.0 / herfindahl), 2) if herfindahl > 0 else 0,
            "top3_weight": round(float(sum(t[1] for t in top)), 4),
            "max_position": {"symbol": top[0][0], "weight": round(float(top[0][1]), 4)} if top else None,
        }

    def correlation_analysis(self, matrix: np.ndarray, symbols: list[str]) -> dict:
        if matrix.shape[0] < 2:
            return {"avg_correlation": None, "max_pair": None}
        corr = np.corrcoef(matrix)
        n = corr.shape[0]
        off = corr[np.triu_indices(n, k=1)]
        max_idx = np.argmax(off)
        pairs = [(symbols[i], symbols[j]) for i in range(n) for j in range(i + 1, n)]
        return {
            "avg_correlation": round(float(np.mean(off)), 4),
            "max_correlation": round(float(np.max(off)), 4),
            "max_pair": list(pairs[max_idx]) if pairs else None,
            "diversification_ratio": round(float(1.0 - np.mean(off)), 4),
        }

    def tail_risk(self, returns: np.ndarray) -> dict:
        from scipy.stats import skew, kurtosis
        return {
            "skewness": round(float(skew(returns)), 4),
            "excess_kurtosis": round(float(kurtosis(returns)), 4),
            "worst_day": round(float(np.min(returns)), 5),
            "fat_tails": bool(kurtosis(returns) > 1.0),
        }

    def stress_test(self, holdings: list[dict], scenario_id: Optional[str] = None) -> dict:
        w, matrix, symbols = _portfolio_returns(holdings)
        if matrix.size == 0:
            return {"error": "no price history"}
        scenarios = ({scenario_id: BUILTIN_SCENARIOS[scenario_id]}
                     if scenario_id and scenario_id in BUILTIN_SCENARIOS else BUILTIN_SCENARIOS)
        results = []
        base_vol = float(np.std(w @ matrix, ddof=1) * np.sqrt(252))
        for sid, sc in scenarios.items():
            shock = sc["equity_shock"]
            # Portfolio P&L under an instantaneous equity shock (beta≈1 simplification).
            pnl = float(np.sum(w) * shock)
            stressed_vol = base_vol * sc["vol_mult"]
            results.append({
                "scenario_id": sid, "name": sc["name"],
                "portfolio_pnl": round(pnl, 4),
                "portfolio_pnl_pct": round(pnl * 100, 2),
                "stressed_volatility": round(stressed_vol, 4),
                "vol_multiplier": sc["vol_mult"],
            })
        return {"base_volatility": round(base_vol, 4), "scenarios": results}

    def scenario_analysis(self, holdings: list[dict], shocks: dict) -> dict:
        """Custom scenario: shocks = {symbol: pct_move} or {'market': pct}."""
        w, matrix, symbols = _portfolio_returns(holdings)
        if matrix.size == 0:
            return {"error": "no price history"}
        market_shock = shocks.get("market", 0.0)
        pnl = 0.0
        contributions = {}
        for i, sym in enumerate(symbols):
            move = shocks.get(sym, market_shock)
            contrib = float(w[i] * move)
            contributions[sym] = round(contrib, 5)
            pnl += contrib
        return {"portfolio_pnl": round(pnl, 5), "portfolio_pnl_pct": round(pnl * 100, 3),
                "contributions": contributions}

    def factor_exposure(self, holdings: list[dict]) -> dict:
        """Estimate portfolio exposure to common factors via the factor library."""
        try:
            from quant_lab.factors import get_factor_library
            lib = get_factor_library()
            exposures: dict[str, list[float]] = {}
            weights = []
            for h in holdings:
                scores = lib.score_symbol(h.get("symbol", ""))
                weights.append(h.get("weight", 0.0))
                for fname, val in scores.items():
                    if val is not None:
                        exposures.setdefault(fname, []).append((h.get("weight", 0.0), val))
            agg = {}
            for fname, pairs in exposures.items():
                tw = sum(p[0] for p in pairs)
                if tw > 0:
                    agg[fname] = round(sum(p[0] * p[1] for p in pairs) / tw, 2)
            return {"factor_exposures": agg}
        except Exception as e:
            return {"factor_exposures": {}, "note": str(e)}

    def health_score(self, report: dict) -> float:
        """Composite 0-100 portfolio health (higher = healthier)."""
        score = 100.0
        conc = report.get("concentration", {})
        herf = conc.get("herfindahl", 0.0)
        score -= min(herf * 100, 30)  # concentration penalty
        corr = report.get("correlation", {})
        avg_corr = corr.get("avg_correlation") or 0.0
        score -= max(0, avg_corr) * 25  # high correlation penalty
        tail = report.get("tail_risk", {})
        if tail.get("fat_tails"):
            score -= 10
        dd = report.get("drawdown", {})
        score -= min(abs(dd.get("max_drawdown", 0.0)) * 40, 25)
        return round(max(0.0, min(100.0, score)), 1)

    def _save(self, portfolio_id, name, report, health) -> str:
        rid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            "INSERT INTO risk_report(id, portfolio_id, name, report, health_score) VALUES(?,?,?,?,?)",
            (rid, portfolio_id, name, json.dumps(report), health))
        conn.commit()
        conn.close()
        return rid

    def list_reports(self, portfolio_id: Optional[str] = None, limit: int = 20) -> list[dict]:
        conn = _conn()
        if portfolio_id:
            rows = conn.execute(
                "SELECT * FROM risk_report WHERE portfolio_id=? ORDER BY created_at DESC LIMIT ?",
                (portfolio_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM risk_report ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["report"] = json.loads(d["report"])
            except Exception:
                d["report"] = {}
            out.append(d)
        return out

    def scenarios(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM stress_scenario ORDER BY name").fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["shocks"] = json.loads(d["shocks"])
            except Exception:
                d["shocks"] = {}
            out.append(d)
        return out

    def stats(self) -> dict:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM risk_report").fetchone()[0]
        scen = conn.execute("SELECT COUNT(*) FROM stress_scenario").fetchone()[0]
        conn.close()
        return {"total_reports": total, "stress_scenarios": scen}


_instance: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    global _instance
    if _instance is None:
        _instance = RiskEngine()
    return _instance
