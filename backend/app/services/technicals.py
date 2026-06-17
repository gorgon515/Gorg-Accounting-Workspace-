"""Technical-analysis engine — pure Python (standard library only).

Deterministic indicator math used by the Quant Research Engine. Kept dependency
free so it is unit-testable without numpy/pandas and can run in the sidecar with a
minimal install. All functions operate on a list of closing prices (floats),
oldest first, and raise ``ValueError`` on insufficient data so the API layer can
map that to a 400.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Optional


def _need(values: list[float], n: int) -> None:
    if values is None or len(values) < n:
        raise ValueError(f"need at least {n} data points, got {0 if values is None else len(values)}")


def daily_returns(prices: list[float]) -> list[float]:
    """Simple period-over-period returns."""
    _need(prices, 2)
    out = []
    for prev, cur in zip(prices, prices[1:]):
        out.append((cur - prev) / prev if prev else 0.0)
    return out


def sma(prices: list[float], period: int) -> float:
    """Latest simple moving average over ``period``."""
    _need(prices, period)
    return mean(prices[-period:])


def ema_series(prices: list[float], period: int) -> list[float]:
    """EMA aligned to ``prices`` (first ``period-1`` entries are None).

    Seeded with the SMA of the first ``period`` values, then the standard
    multiplier ``2/(period+1)``.
    """
    _need(prices, period)
    k = 2 / (period + 1)
    out: list[Optional[float]] = [None] * (period - 1)
    prev = mean(prices[:period])
    out.append(prev)
    for price in prices[period:]:
        prev = price * k + prev * (1 - k)
        out.append(prev)
    return out  # type: ignore[return-value]


def ema(prices: list[float], period: int) -> float:
    """Latest EMA value."""
    return ema_series(prices, period)[-1]


def rsi(prices: list[float], period: int = 14) -> float:
    """Wilder's Relative Strength Index (0–100), latest value."""
    _need(prices, period + 1)
    gains, losses = [], []
    for prev, cur in zip(prices, prices[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    # Wilder smoothing over the remaining periods.
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD line, signal line, and histogram (latest values)."""
    _need(prices, slow + signal)
    fast_e = ema_series(prices, fast)
    slow_e = ema_series(prices, slow)
    macd_line = [
        f - s for f, s in zip(fast_e, slow_e) if f is not None and s is not None
    ]
    signal_line = ema_series(macd_line, signal)
    return {
        "macd": round(macd_line[-1], 6),
        "signal": round(signal_line[-1], 6),
        "histogram": round(macd_line[-1] - signal_line[-1], 6),
    }


def bollinger(prices: list[float], period: int = 20, mult: float = 2.0) -> dict:
    """Bollinger Bands (latest): middle (SMA), upper, lower, and %B position."""
    _need(prices, period)
    window = prices[-period:]
    mid = mean(window)
    sd = pstdev(window)
    upper = mid + mult * sd
    lower = mid - mult * sd
    width = upper - lower
    pct_b = (prices[-1] - lower) / width if width else 0.5
    return {
        "middle": round(mid, 6),
        "upper": round(upper, 6),
        "lower": round(lower, 6),
        "percent_b": round(pct_b, 4),
    }


def momentum(prices: list[float], period: int) -> float:
    """Percent change over the trailing ``period``."""
    _need(prices, period + 1)
    past = prices[-(period + 1)]
    return (prices[-1] - past) / past if past else 0.0


def volatility(prices: list[float], periods_per_year: int = 252, annualized: bool = True) -> float:
    """Return-series standard deviation, optionally annualized."""
    rets = daily_returns(prices)
    vol = pstdev(rets) if len(rets) > 1 else 0.0
    return vol * (periods_per_year ** 0.5) if annualized else vol


def max_drawdown(prices: list[float]) -> dict:
    """Largest peak-to-trough decline as a positive fraction, with indices."""
    _need(prices, 2)
    peak = prices[0]
    peak_i = trough_i = 0
    mdd = 0.0
    cur_peak_i = 0
    for i, p in enumerate(prices):
        if p > peak:
            peak = p
            cur_peak_i = i
        dd = (peak - p) / peak if peak else 0.0
        if dd > mdd:
            mdd = dd
            peak_i = cur_peak_i
            trough_i = i
    return {"max_drawdown": round(mdd, 6), "peak_index": peak_i, "trough_index": trough_i}


def analyze(prices: list[float]) -> dict:
    """Full indicator summary plus plain-language signals.

    Gracefully includes only the indicators the series is long enough to support,
    so short histories still return useful output instead of erroring.
    """
    _need(prices, 2)
    last = prices[-1]
    out: dict = {"price": round(last, 6), "points": len(prices), "signals": []}
    sig = out["signals"]

    if len(prices) >= 50:
        s20, s50 = sma(prices, 20), sma(prices, 50)
        out["sma20"], out["sma50"] = round(s20, 6), round(s50, 6)
        out["trend"] = "up" if s20 > s50 else "down"
        sig.append(f"trend {out['trend']} (SMA20 {'>' if s20 > s50 else '<'} SMA50)")
    elif len(prices) >= 20:
        out["sma20"] = round(sma(prices, 20), 6)

    if len(prices) >= 15:
        r = rsi(prices, 14)
        out["rsi14"] = round(r, 2)
        if r >= 70:
            sig.append(f"overbought (RSI {r:.0f})")
        elif r <= 30:
            sig.append(f"oversold (RSI {r:.0f})")
        else:
            sig.append(f"neutral momentum (RSI {r:.0f})")

    if len(prices) >= 35:
        m = macd(prices)
        out["macd"] = m
        sig.append("MACD bullish" if m["histogram"] > 0 else "MACD bearish")

    if len(prices) >= 20:
        b = bollinger(prices)
        out["bollinger"] = b
        if b["percent_b"] > 1:
            sig.append("above upper band")
        elif b["percent_b"] < 0:
            sig.append("below lower band")

    if len(prices) >= 21:
        out["momentum_20"] = round(momentum(prices, 20), 6)
    out["volatility_annualized"] = round(volatility(prices), 6)
    out["max_drawdown"] = max_drawdown(prices)["max_drawdown"]
    return out
