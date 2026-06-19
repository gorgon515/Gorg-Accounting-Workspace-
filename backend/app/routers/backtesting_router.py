"""Backtesting Engine API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/backtesting", tags=["backtesting"])


class BacktestRun(BaseModel):
    name: str
    signals: list[float]
    asset_returns: list[float]
    strategy_id: str = ""
    symbol: str = ""
    commission_bps: float = 1.0
    slippage_bps: float = 5.0
    benchmark_returns: Optional[list[float]] = None
    initial_capital: float = 100000.0


class WalkForward(BaseModel):
    signals: list[float]
    asset_returns: list[float]
    n_splits: int = 4


class MonteCarlo(BaseModel):
    strategy_returns: list[float]
    n_sims: int = 1000
    horizon: Optional[int] = None


class Sensitivity(BaseModel):
    signals: list[float]
    asset_returns: list[float]
    param_grid: Optional[dict] = None


@router.post("/run")
def run_backtest(body: BacktestRun):
    from backtesting.engine import get_backtester
    return get_backtester().run(
        body.name, body.signals, body.asset_returns, body.strategy_id, body.symbol,
        body.commission_bps, body.slippage_bps, body.benchmark_returns, body.initial_capital)


@router.post("/walk-forward")
def walk_forward(body: WalkForward):
    from backtesting.engine import walk_forward
    return walk_forward(body.signals, body.asset_returns, body.n_splits)


@router.post("/rolling")
def rolling_validation(body: WalkForward):
    from backtesting.engine import rolling_validation
    return rolling_validation(body.signals, body.asset_returns)


@router.post("/monte-carlo")
def monte_carlo(body: MonteCarlo):
    from backtesting.engine import monte_carlo
    return monte_carlo(body.strategy_returns, body.n_sims, body.horizon)


@router.post("/sensitivity")
def sensitivity(body: Sensitivity):
    from backtesting.engine import sensitivity_analysis
    return sensitivity_analysis(body.signals, body.asset_returns, body.param_grid)


@router.post("/metrics")
def compute_metrics(returns: list[float], benchmark: Optional[list[float]] = None):
    from backtesting.metrics import full_report
    return full_report(returns, benchmark)


@router.get("/runs")
def list_runs(strategy_id: Optional[str] = None, limit: int = 50):
    from backtesting.engine import get_backtester
    return get_backtester().list_runs(strategy_id=strategy_id, limit=limit)


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    from backtesting.engine import get_backtester
    r = get_backtester().get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return r


@router.get("/stats")
def stats():
    from backtesting.engine import get_backtester
    return get_backtester().stats()
