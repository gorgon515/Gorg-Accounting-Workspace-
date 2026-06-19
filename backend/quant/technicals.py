"""Advanced technical analysis — builds on the Phase-2 primitives.

Re-exports the core indicators (SMA/EMA/RSI/MACD/Bollinger/momentum/volatility/
drawdown) from app.services.technicals and adds ATR, relative strength, and
0–100 momentum/trend/volume scores with plain-language explanations. Pure Python.
"""
from __future__ import annotations

from statistics import mean
from typing import Optional

from app.services.technicals import (  # noqa: F401  (re-exported on purpose)
    sma, ema, ema_series, rsi, macd, bollinger, momentum, volatility,
    max_drawdown, daily_returns, analyze as base_analyze,
)


def _need(seq, n):
    if not seq or len(seq) < n:
        raise ValueError(f"need at least {n} data points")


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    """Average True Range — requires OHLC high/low/close arrays."""
    _need(closes, period + 1)
    if len(highs) != len(closes) or len(lows) != len(closes):
        raise ValueError("highs/lows/closes must be equal length")
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    # Wilder smoothing.
    a = mean(trs[:period])
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return round(a, 6)


def relative_strength(prices: list[float], benchmark: list[float], window: int = 63) -> dict:
    """Performance of the asset vs. a benchmark over the trailing window."""
    _need(prices, 2)
    _need(benchmark, 2)
    w = min(window, len(prices) - 1, len(benchmark) - 1)
    a = (prices[-1] - prices[-1 - w]) / prices[-1 - w]
    b = (benchmark[-1] - benchmark[-1 - w]) / benchmark[-1 - w]
    return {
        "asset_return": round(a, 6),
        "benchmark_return": round(b, 6),
        "excess": round(a - b, 6),
        "outperforming": a > b,
        "window": w,
    }


def momentum_score(prices: list[float]) -> float:
    """Blend 1/3/6-month momentum into a 0–100 score."""
    _need(prices, 22)
    parts = []
    for period, scale in ((21, 0.10), (63, 0.20), (126, 0.30)):
        if len(prices) > period:
            m = momentum(prices, period)
            parts.append(max(0.0, min(100.0, 50 + (m / scale) * 50)))
    return round(mean(parts), 1) if parts else 50.0


def trend_score(prices: list[float]) -> float:
    """0–100 trend strength from price vs moving averages and their order."""
    _need(prices, 20)
    last = prices[-1]
    score = 50.0
    if len(prices) >= 20:
        score += 12 if last > sma(prices, 20) else -12
    if len(prices) >= 50:
        s20, s50 = sma(prices, 20), sma(prices, 50)
        score += 12 if last > s50 else -12
        score += 14 if s20 > s50 else -14
    if len(prices) >= 200:
        score += 12 if last > sma(prices, 200) else -12
    return round(max(0.0, min(100.0, score)), 1)


def volume_analysis(volumes: list[float], period: int = 20) -> dict:
    """Relative-volume read: last vs. average, and a simple up/down trend."""
    _need(volumes, period)
    avg = mean(volumes[-period:])
    last = volumes[-1]
    first_half = mean(volumes[-period:-period // 2]) if period >= 4 else avg
    second_half = mean(volumes[-period // 2:]) if period >= 4 else avg
    return {
        "last": round(last, 2),
        "avg": round(avg, 2),
        "relative_volume": round(last / avg, 3) if avg else None,
        "trend": "rising" if second_half > first_half else "falling",
    }


def analyze_extended(prices: list[float], benchmark: Optional[list[float]] = None,
                     volumes: Optional[list[float]] = None) -> dict:
    """Full technical read: base indicators + scores + explanations."""
    out = base_analyze(prices)
    out["momentum_score"] = momentum_score(prices) if len(prices) >= 22 else None
    out["trend_score"] = trend_score(prices) if len(prices) >= 20 else None
    if benchmark and len(benchmark) >= 2:
        out["relative_strength"] = relative_strength(prices, benchmark)
    if volumes and len(volumes) >= 20:
        out["volume"] = volume_analysis(volumes)
    out["explanations"] = _explain(out)
    return out


def _explain(a: dict) -> list[str]:
    notes = []
    if a.get("trend_score") is not None:
        ts = a["trend_score"]
        notes.append(f"Trend score {ts}/100 — {'strong uptrend' if ts >= 65 else 'downtrend' if ts <= 35 else 'mixed'}.")
    if a.get("momentum_score") is not None:
        notes.append(f"Momentum score {a['momentum_score']}/100.")
    if a.get("relative_strength"):
        rs = a["relative_strength"]
        notes.append(f"{'Outperforming' if rs['outperforming'] else 'Lagging'} benchmark by "
                     f"{rs['excess'] * 100:.1f}% over {rs['window']} periods.")
    return notes
