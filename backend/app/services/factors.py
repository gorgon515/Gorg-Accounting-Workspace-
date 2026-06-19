"""Factor scoring — transparent, rules-based (no ML, no opaque weights).

Each fundamental/price input is mapped to a 0–100 sub-score via a documented,
monotonic, clamped transform, then grouped into the classic style factors
(value, quality, growth, momentum) and combined into a composite. The point is
explainability: every score traces back to a stated threshold, never a black box.

Inputs are optional — missing metrics are simply dropped from their factor's
average so partial data still yields a usable score (with lower ``coverage``).
"""
from __future__ import annotations

from typing import Optional

from . import technicals


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _lin(value: Optional[float], good: float, bad: float) -> Optional[float]:
    """Map ``value`` to 0–100 where ``good``→100 and ``bad``→0 (either direction)."""
    if value is None:
        return None
    if good == bad:
        return 50.0
    return _clamp((value - bad) / (good - bad) * 100)


def _avg(scores: list[Optional[float]]) -> tuple[Optional[float], int]:
    present = [s for s in scores if s is not None]
    if not present:
        return None, 0
    return round(sum(present) / len(present), 1), len(present)


def value_score(f: dict) -> tuple[Optional[float], int]:
    """Cheaper is better. PE, PEG, P/B, P/S, FCF yield."""
    return _avg([
        _lin(f.get("pe"), good=8, bad=40),
        _lin(f.get("peg"), good=0.8, bad=3.0),
        _lin(f.get("pb"), good=1.0, bad=8.0),
        _lin(f.get("ps"), good=1.0, bad=12.0),
        _lin(f.get("fcf_yield"), good=0.08, bad=0.0),
    ])


def quality_score(f: dict) -> tuple[Optional[float], int]:
    """High returns/margins, low leverage."""
    return _avg([
        _lin(f.get("roe"), good=0.25, bad=0.0),
        _lin(f.get("roic"), good=0.20, bad=0.0),
        _lin(f.get("gross_margin"), good=0.60, bad=0.10),
        _lin(f.get("net_margin"), good=0.25, bad=0.0),
        _lin(f.get("debt_to_equity"), good=0.2, bad=2.5),
        _lin(f.get("current_ratio"), good=2.5, bad=0.8),
    ])


def growth_score(f: dict) -> tuple[Optional[float], int]:
    """Revenue and earnings growth."""
    return _avg([
        _lin(f.get("revenue_growth"), good=0.30, bad=-0.05),
        _lin(f.get("earnings_growth"), good=0.30, bad=-0.10),
        _lin(f.get("fcf_growth"), good=0.25, bad=-0.10),
    ])


def momentum_score(prices: Optional[list[float]]) -> tuple[Optional[float], int]:
    """Trailing price momentum (3m/6m/12m) plus trend confirmation."""
    if not prices or len(prices) < 30:
        return None, 0
    parts: list[Optional[float]] = []
    for period, good, bad in ((63, 0.15, -0.15), (126, 0.25, -0.25), (252, 0.40, -0.40)):
        if len(prices) > period:
            parts.append(_lin(technicals.momentum(prices, period), good=good, bad=bad))
    if len(prices) >= 50:
        trend_up = technicals.sma(prices, 20) > technicals.sma(prices, 50)
        parts.append(75.0 if trend_up else 25.0)
    return _avg(parts)


_RATINGS = ((80, "strong"), (65, "favorable"), (45, "neutral"), (30, "weak"), (0, "poor"))


def rate(score: Optional[float]) -> str:
    if score is None:
        return "n/a"
    for threshold, label in _RATINGS:
        if score >= threshold:
            return label
    return "poor"


def score(symbol: str, fundamentals: dict | None = None, prices: list[float] | None = None) -> dict:
    """Composite factor score with per-factor breakdown and coverage.

    ``weights`` are equal across the factors that have data; coverage reports how
    many underlying metrics were available so the caller can gauge confidence.
    """
    fundamentals = fundamentals or {}
    factors = {
        "value": value_score(fundamentals),
        "quality": quality_score(fundamentals),
        "growth": growth_score(fundamentals),
        "momentum": momentum_score(prices),
    }
    breakdown = {k: {"score": v[0], "metrics_used": v[1], "rating": rate(v[0])} for k, v in factors.items()}
    present = [v[0] for v in factors.values() if v[0] is not None]
    composite = round(sum(present) / len(present), 1) if present else None
    total_metrics = sum(v[1] for v in factors.values())
    return {
        "symbol": symbol.upper(),
        "composite": composite,
        "rating": rate(composite),
        "factors": breakdown,
        "coverage": {"factors_scored": len(present), "metrics_used": total_metrics},
        "note": "Rules-based factor scores from the supplied metrics — transparent thresholds, not a forecast.",
    }
