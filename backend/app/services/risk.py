"""Portfolio & return risk analytics — pure Python (standard library only)."""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Optional

from . import technicals

TRADING_DAYS = 252


def sharpe(returns: list[float], risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    """Annualized Sharpe ratio from a per-period return series."""
    if len(returns) < 2:
        return None
    rf_per = risk_free / periods_per_year
    excess = [r - rf_per for r in returns]
    sd = pstdev(excess)
    if sd == 0:
        return None
    return round((mean(excess) / sd) * (periods_per_year ** 0.5), 4)


def sortino(returns: list[float], risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    """Annualized Sortino ratio (downside-deviation denominator)."""
    if len(returns) < 2:
        return None
    rf_per = risk_free / periods_per_year
    excess = [r - rf_per for r in returns]
    downside = [min(e, 0.0) ** 2 for e in excess]
    dd = (sum(downside) / len(downside)) ** 0.5
    if dd == 0:
        return None
    return round((mean(excess) / dd) * (periods_per_year ** 0.5), 4)


def correlation(a: list[float], b: list[float]) -> Optional[float]:
    """Pearson correlation of two equal-length series."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = mean(a), mean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    if da == 0 or db == 0:
        return None
    return round(cov / (da * db), 4)


def beta(asset_returns: list[float], market_returns: list[float]) -> Optional[float]:
    """Beta of an asset vs. the market (cov / market variance)."""
    n = min(len(asset_returns), len(market_returns))
    if n < 2:
        return None
    a, m = asset_returns[-n:], market_returns[-n:]
    ma, mm = mean(a), mean(m)
    cov = sum((x - ma) * (y - mm) for x, y in zip(a, m)) / n
    var_m = sum((y - mm) ** 2 for y in m) / n
    if var_m == 0:
        return None
    return round(cov / var_m, 4)


def value_at_risk(returns: list[float], level: float = 0.95) -> Optional[float]:
    """Historical Value-at-Risk as a positive loss fraction at ``level``."""
    if len(returns) < 2:
        return None
    ordered = sorted(returns)
    idx = max(0, min(len(ordered) - 1, int((1 - level) * len(ordered))))
    return round(-ordered[idx], 6)


def summarize_returns(prices: list[float], benchmark_prices: Optional[list[float]] = None,
                      risk_free: float = 0.0) -> dict:
    """Risk summary for one price series, optionally relative to a benchmark."""
    rets = technicals.daily_returns(prices)
    out = {
        "points": len(prices),
        "annualized_volatility": round(technicals.volatility(prices), 6),
        "sharpe": sharpe(rets, risk_free),
        "sortino": sortino(rets, risk_free),
        "max_drawdown": technicals.max_drawdown(prices)["max_drawdown"],
        "value_at_risk_95": value_at_risk(rets, 0.95),
    }
    if benchmark_prices and len(benchmark_prices) >= 2:
        bench = technicals.daily_returns(benchmark_prices)
        out["beta_vs_benchmark"] = beta(rets, bench)
        out["correlation_vs_benchmark"] = correlation(rets, bench)
    return out


def portfolio_report(holdings: list[dict], benchmark_prices: Optional[list[float]] = None) -> dict:
    """Aggregate a portfolio.

    Each holding: ``{symbol, weight|value, prices[]}``. Computes weighted exposure,
    concentration (Herfindahl), sector exposure (if ``sector`` given), and a
    blended risk profile from each holding's return series.
    """
    if not holdings:
        raise ValueError("no holdings provided")
    # Normalize weights from explicit weight or market value.
    raw = [float(h.get("weight", h.get("value", 0)) or 0) for h in holdings]
    total = sum(raw)
    weights = [w / total if total else 1 / len(holdings) for w in raw]

    hhi = round(sum(w * w for w in weights), 4)  # 1.0 = single name, →0 diversified
    sectors: dict[str, float] = {}
    positions = []
    for h, w in zip(holdings, weights):
        sec = h.get("sector", "Unclassified")
        sectors[sec] = round(sectors.get(sec, 0.0) + w, 4)
        prices = h.get("prices") or []
        risk = summarize_returns(prices, benchmark_prices) if len(prices) >= 2 else None
        positions.append({
            "symbol": str(h.get("symbol", "?")).upper(),
            "weight": round(w, 4),
            "sector": sec,
            "risk": risk,
        })

    top = max(positions, key=lambda p: p["weight"])
    return {
        "n_positions": len(holdings),
        "concentration_hhi": hhi,
        "effective_positions": round(1 / hhi, 1) if hhi else None,
        "largest_position": {"symbol": top["symbol"], "weight": top["weight"]},
        "sector_exposure": dict(sorted(sectors.items(), key=lambda kv: -kv[1])),
        "positions": positions,
        "note": "Concentration HHI: 1.0 = single position; lower is more diversified.",
    }
