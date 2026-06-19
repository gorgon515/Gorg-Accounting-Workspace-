"""
Risk-adjusted performance metrics — real implementations over return series.

All functions accept a list/array of periodic (e.g. daily) simple returns unless
noted. They return None when the input is too short to be meaningful rather than
raising, so callers can degrade gracefully.
"""
from __future__ import annotations
import math
from typing import Optional, Sequence
import numpy as np

TRADING_DAYS = 252


def _arr(returns: Sequence[float]) -> np.ndarray:
    a = np.asarray([r for r in returns if r is not None], dtype=float)
    return a


def cagr(returns: Sequence[float], periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    growth = float(np.prod(1.0 + a))
    if growth <= 0:
        return -1.0
    years = a.size / periods_per_year
    if years <= 0:
        return None
    return growth ** (1.0 / years) - 1.0


def total_return(returns: Sequence[float]) -> Optional[float]:
    a = _arr(returns)
    if a.size == 0:
        return None
    return float(np.prod(1.0 + a) - 1.0)


def volatility(returns: Sequence[float], periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    return float(np.std(a, ddof=1) * math.sqrt(periods_per_year))


def sharpe(returns: Sequence[float], risk_free: float = 0.0,
           periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    rf_per = risk_free / periods_per_year
    excess = a - rf_per
    sd = np.std(excess, ddof=1)
    if sd == 0:
        return None
    return float(np.mean(excess) / sd * math.sqrt(periods_per_year))


def sortino(returns: Sequence[float], risk_free: float = 0.0,
            periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    rf_per = risk_free / periods_per_year
    excess = a - rf_per
    downside = excess[excess < 0]
    if downside.size == 0:
        return None
    dd = math.sqrt(float(np.mean(downside ** 2)))
    if dd == 0:
        return None
    return float(np.mean(excess) / dd * math.sqrt(periods_per_year))


def max_drawdown(returns: Sequence[float]) -> Optional[float]:
    a = _arr(returns)
    if a.size < 1:
        return None
    equity = np.cumprod(1.0 + a)
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    return float(np.min(drawdowns))  # negative number, e.g. -0.23


def calmar(returns: Sequence[float], periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    c = cagr(returns, periods_per_year)
    mdd = max_drawdown(returns)
    if c is None or mdd is None or mdd == 0:
        return None
    return float(c / abs(mdd))


def beta(asset_returns: Sequence[float], market_returns: Sequence[float]) -> Optional[float]:
    a = _arr(asset_returns)
    m = _arr(market_returns)
    n = min(a.size, m.size)
    if n < 2:
        return None
    a, m = a[-n:], m[-n:]
    var_m = np.var(m, ddof=1)
    if var_m == 0:
        return None
    cov = np.cov(a, m, ddof=1)[0, 1]
    return float(cov / var_m)


def alpha(asset_returns: Sequence[float], market_returns: Sequence[float],
          risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    b = beta(asset_returns, market_returns)
    if b is None:
        return None
    a = _arr(asset_returns)
    m = _arr(market_returns)
    n = min(a.size, m.size)
    a, m = a[-n:], m[-n:]
    rf_per = risk_free / periods_per_year
    asset_ann = float(np.mean(a)) * periods_per_year
    market_ann = float(np.mean(m)) * periods_per_year
    # Jensen's alpha (annualized)
    return float(asset_ann - (risk_free + b * (market_ann - risk_free)))


def information_ratio(returns: Sequence[float], benchmark_returns: Sequence[float],
                      periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    a = _arr(returns)
    b = _arr(benchmark_returns)
    n = min(a.size, b.size)
    if n < 2:
        return None
    active = a[-n:] - b[-n:]
    te = np.std(active, ddof=1)
    if te == 0:
        return None
    return float(np.mean(active) / te * math.sqrt(periods_per_year))


def treynor(returns: Sequence[float], market_returns: Sequence[float],
            risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    b = beta(returns, market_returns)
    if b is None or b == 0:
        return None
    a = _arr(returns)
    ann = float(np.mean(a)) * periods_per_year
    return float((ann - risk_free) / b)


def hit_rate(returns: Sequence[float]) -> Optional[float]:
    a = _arr(returns)
    if a.size == 0:
        return None
    return float(np.mean(a > 0))


def profit_factor(returns: Sequence[float]) -> Optional[float]:
    a = _arr(returns)
    if a.size == 0:
        return None
    gains = a[a > 0].sum()
    losses = -a[a < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else None
    return float(gains / losses)


def expectancy(returns: Sequence[float]) -> Optional[float]:
    """Average return per period (per-trade expectancy)."""
    a = _arr(returns)
    if a.size == 0:
        return None
    return float(np.mean(a))


def value_at_risk(returns: Sequence[float], level: float = 0.95) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    return float(np.percentile(a, (1.0 - level) * 100.0))


def expected_shortfall(returns: Sequence[float], level: float = 0.95) -> Optional[float]:
    a = _arr(returns)
    if a.size < 2:
        return None
    var = np.percentile(a, (1.0 - level) * 100.0)
    tail = a[a <= var]
    if tail.size == 0:
        return float(var)
    return float(np.mean(tail))


def prices_to_returns(prices: Sequence[float]) -> list[float]:
    p = np.asarray([x for x in prices if x is not None], dtype=float)
    if p.size < 2:
        return []
    return list(np.diff(p) / p[:-1])


def full_report(returns: Sequence[float], benchmark_returns: Optional[Sequence[float]] = None,
                risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> dict:
    """Compute the full institutional metric set over a return series."""
    def r(x, nd=4):
        return round(x, nd) if isinstance(x, (int, float)) and not math.isinf(x) else x

    report = {
        "periods": int(_arr(returns).size),
        "total_return": r(total_return(returns)),
        "cagr": r(cagr(returns, periods_per_year)),
        "volatility": r(volatility(returns, periods_per_year)),
        "sharpe": r(sharpe(returns, risk_free, periods_per_year)),
        "sortino": r(sortino(returns, risk_free, periods_per_year)),
        "calmar": r(calmar(returns, periods_per_year)),
        "max_drawdown": r(max_drawdown(returns)),
        "hit_rate": r(hit_rate(returns)),
        "profit_factor": r(profit_factor(returns)),
        "expectancy": r(expectancy(returns), 6),
        "var_95": r(value_at_risk(returns, 0.95)),
        "expected_shortfall_95": r(expected_shortfall(returns, 0.95)),
    }
    if benchmark_returns is not None:
        report.update({
            "alpha": r(alpha(returns, benchmark_returns, risk_free, periods_per_year)),
            "beta": r(beta(returns, benchmark_returns)),
            "information_ratio": r(information_ratio(returns, benchmark_returns, periods_per_year)),
            "treynor": r(treynor(returns, benchmark_returns, risk_free, periods_per_year)),
        })
    return report
