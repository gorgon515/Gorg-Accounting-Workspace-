"""
Backtesting Engine — historical simulation, walk-forward, Monte Carlo,
sensitivity analysis, with slippage and transaction-cost modeling.

Strategies are expressed as signal series (target weight in [-1, 1] per period,
or a list of {date, weight}). The engine simulates an equity curve net of costs
and reports the full institutional metric set. Persists runs to SQLite so the
Quant Lab and Knowledge Engine can reference them.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, Sequence
import numpy as np

from . import metrics as M

_DB = Path(".data/backtesting.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS backtest_run (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            strategy_id TEXT DEFAULT '',
            symbol TEXT DEFAULT '',
            kind TEXT DEFAULT 'historical',
            params TEXT DEFAULT '{}',
            metrics TEXT DEFAULT '{}',
            equity_curve TEXT DEFAULT '[]',
            n_periods INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class CostModel:
    """Transaction cost + slippage model applied on weight changes (turnover)."""

    def __init__(self, commission_bps: float = 1.0, slippage_bps: float = 5.0):
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps

    def cost(self, turnover: float) -> float:
        # turnover is |Δweight|; cost in return terms.
        return turnover * (self.commission_bps + self.slippage_bps) / 10000.0


def _align(signals: Sequence[float], returns: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    s = np.asarray(signals, dtype=float)
    r = np.asarray(returns, dtype=float)
    n = min(s.size, r.size)
    return s[-n:], r[-n:]


def simulate(signals: Sequence[float], asset_returns: Sequence[float],
             cost_model: Optional[CostModel] = None,
             initial_capital: float = 100000.0) -> dict:
    """
    Core historical simulation. `signals[t]` is the target weight applied to the
    asset return `asset_returns[t]` (signal is acted on at the same period —
    callers should pre-shift signals to avoid look-ahead). Returns equity curve,
    strategy returns and the full metric report.
    """
    cost_model = cost_model or CostModel()
    s, r = _align(signals, asset_returns)
    if s.size == 0:
        return {"error": "no data", "metrics": {}, "equity_curve": [], "strategy_returns": []}

    prev_w = 0.0
    strat_returns = np.zeros(s.size)
    for t in range(s.size):
        w = float(s[t])
        turnover = abs(w - prev_w)
        gross = w * float(r[t])
        net = gross - cost_model.cost(turnover)
        strat_returns[t] = net
        prev_w = w

    equity = initial_capital * np.cumprod(1.0 + strat_returns)
    report = M.full_report(list(strat_returns))
    return {
        "metrics": report,
        "equity_curve": [round(float(x), 2) for x in equity],
        "strategy_returns": [round(float(x), 6) for x in strat_returns],
        "final_equity": round(float(equity[-1]), 2),
        "initial_capital": initial_capital,
    }


def benchmark_compare(strategy_returns: Sequence[float],
                      benchmark_returns: Sequence[float]) -> dict:
    """Compare a strategy return series against a benchmark (e.g. buy & hold)."""
    return {
        "strategy": M.full_report(list(strategy_returns), benchmark_returns),
        "benchmark": M.full_report(list(benchmark_returns)),
        "excess_return": (M.total_return(strategy_returns) or 0) - (M.total_return(benchmark_returns) or 0),
    }


def walk_forward(signals: Sequence[float], asset_returns: Sequence[float],
                 n_splits: int = 4, cost_model: Optional[CostModel] = None) -> dict:
    """
    Walk-forward validation: split the series into sequential folds and report
    out-of-sample metrics per fold. Detects performance decay across time.
    """
    s, r = _align(signals, asset_returns)
    if s.size < n_splits * 5:
        return {"error": "insufficient data for walk-forward", "folds": []}
    fold_size = s.size // n_splits
    folds = []
    for i in range(n_splits):
        start = i * fold_size
        end = s.size if i == n_splits - 1 else (i + 1) * fold_size
        sim = simulate(s[start:end], r[start:end], cost_model)
        folds.append({
            "fold": i + 1,
            "periods": int(end - start),
            "sharpe": sim["metrics"].get("sharpe"),
            "total_return": sim["metrics"].get("total_return"),
            "max_drawdown": sim["metrics"].get("max_drawdown"),
        })
    sharpes = [f["sharpe"] for f in folds if f["sharpe"] is not None]
    consistency = float(np.std(sharpes)) if len(sharpes) > 1 else None
    return {
        "n_splits": n_splits,
        "folds": folds,
        "mean_oos_sharpe": round(float(np.mean(sharpes)), 4) if sharpes else None,
        "sharpe_dispersion": round(consistency, 4) if consistency is not None else None,
    }


def rolling_validation(signals: Sequence[float], asset_returns: Sequence[float],
                       window: int = 63, cost_model: Optional[CostModel] = None) -> dict:
    """Rolling-window Sharpe to visualize stability through time."""
    s, r = _align(signals, asset_returns)
    if s.size < window + 1:
        return {"error": "insufficient data", "rolling_sharpe": []}
    sim = simulate(s, r, cost_model)
    rets = np.asarray(sim["strategy_returns"], dtype=float)
    rolling = []
    for t in range(window, rets.size + 1):
        win = rets[t - window:t]
        sh = M.sharpe(list(win))
        rolling.append(round(sh, 3) if sh is not None else None)
    return {"window": window, "rolling_sharpe": rolling}


def monte_carlo(strategy_returns: Sequence[float], n_sims: int = 1000,
                horizon: Optional[int] = None, seed: int = 42) -> dict:
    """
    Monte Carlo via bootstrap resampling of historical strategy returns.
    Produces a distribution of terminal returns and drawdowns.
    """
    a = np.asarray([x for x in strategy_returns if x is not None], dtype=float)
    if a.size < 5:
        return {"error": "insufficient data for Monte Carlo"}
    horizon = horizon or a.size
    rng = np.random.default_rng(seed)
    terminal = np.empty(n_sims)
    drawdowns = np.empty(n_sims)
    for i in range(n_sims):
        sample = rng.choice(a, size=horizon, replace=True)
        equity = np.cumprod(1.0 + sample)
        terminal[i] = equity[-1] - 1.0
        peak = np.maximum.accumulate(equity)
        drawdowns[i] = float(np.min((equity - peak) / peak))
    return {
        "n_sims": n_sims,
        "horizon": horizon,
        "terminal_return": {
            "mean": round(float(np.mean(terminal)), 4),
            "median": round(float(np.median(terminal)), 4),
            "p05": round(float(np.percentile(terminal, 5)), 4),
            "p25": round(float(np.percentile(terminal, 25)), 4),
            "p75": round(float(np.percentile(terminal, 75)), 4),
            "p95": round(float(np.percentile(terminal, 95)), 4),
            "prob_loss": round(float(np.mean(terminal < 0)), 4),
        },
        "max_drawdown": {
            "mean": round(float(np.mean(drawdowns)), 4),
            "worst": round(float(np.min(drawdowns)), 4),
            "p05": round(float(np.percentile(drawdowns, 5)), 4),
        },
    }


def sensitivity_analysis(signals: Sequence[float], asset_returns: Sequence[float],
                         param_grid: Optional[dict] = None) -> dict:
    """
    Sensitivity of risk-adjusted performance to cost assumptions. Varies
    slippage across a grid and reports the Sharpe surface.
    """
    grid = param_grid or {"slippage_bps": [0, 5, 10, 20, 50]}
    results = []
    for slip in grid.get("slippage_bps", [5]):
        sim = simulate(signals, asset_returns, CostModel(slippage_bps=slip))
        results.append({
            "slippage_bps": slip,
            "sharpe": sim["metrics"].get("sharpe"),
            "total_return": sim["metrics"].get("total_return"),
        })
    return {"parameter": "slippage_bps", "results": results}


def position_sizing(signal_strength: Sequence[float], target_vol: float = 0.15,
                    asset_vol: Optional[float] = None,
                    asset_returns: Optional[Sequence[float]] = None) -> list[float]:
    """
    Volatility-targeted position sizing: scale raw signal to hit a target
    annualized volatility. Returns position weights aligned with signals.
    """
    s = np.asarray(signal_strength, dtype=float)
    if asset_vol is None and asset_returns is not None:
        asset_vol = M.volatility(asset_returns) or 0.0
    if not asset_vol or asset_vol == 0:
        return list(np.clip(s, -1.0, 1.0))
    scale = target_vol / asset_vol
    return list(np.clip(s * scale, -1.0, 1.0))


class Backtester:
    def __init__(self):
        _conn().close()

    def run(self, name: str, signals: Sequence[float], asset_returns: Sequence[float],
            strategy_id: str = "", symbol: str = "",
            commission_bps: float = 1.0, slippage_bps: float = 5.0,
            benchmark_returns: Optional[Sequence[float]] = None,
            initial_capital: float = 100000.0, persist: bool = True) -> dict:
        cost = CostModel(commission_bps, slippage_bps)
        sim = simulate(signals, asset_returns, cost, initial_capital)
        result = {
            "name": name, "strategy_id": strategy_id, "symbol": symbol,
            "metrics": sim["metrics"], "equity_curve": sim["equity_curve"],
            "final_equity": sim.get("final_equity"),
            "n_periods": sim["metrics"].get("periods", 0),
        }
        if benchmark_returns is not None:
            result["benchmark"] = benchmark_compare(sim["strategy_returns"], benchmark_returns)
        if persist:
            result["id"] = self._save(name, strategy_id, symbol, "historical",
                                      {"commission_bps": commission_bps, "slippage_bps": slippage_bps},
                                      sim["metrics"], sim["equity_curve"])
        return result

    def _save(self, name, strategy_id, symbol, kind, params, metrics_d, equity) -> str:
        run_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO backtest_run(id, name, strategy_id, symbol, kind, params,
               metrics, equity_curve, n_periods) VALUES(?,?,?,?,?,?,?,?,?)""",
            (run_id, name, strategy_id, symbol, kind, json.dumps(params),
             json.dumps(metrics_d), json.dumps(equity), metrics_d.get("periods", 0)),
        )
        conn.commit()
        conn.close()
        return run_id

    def list_runs(self, strategy_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        if strategy_id:
            rows = conn.execute(
                "SELECT * FROM backtest_run WHERE strategy_id=? ORDER BY created_at DESC LIMIT ?",
                (strategy_id, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM backtest_run ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def get_run(self, run_id: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM backtest_run WHERE id=?", (run_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def _fmt(self, row) -> dict:
        d = dict(row)
        for f in ("params", "metrics", "equity_curve"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = {} if f != "equity_curve" else []
        return d

    def stats(self) -> dict:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM backtest_run").fetchone()[0]
        conn.close()
        return {"total_backtests": total}


_instance: Optional[Backtester] = None


def get_backtester() -> Backtester:
    global _instance
    if _instance is None:
        _instance = Backtester()
    return _instance
