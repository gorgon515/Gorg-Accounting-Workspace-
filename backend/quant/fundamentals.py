"""Fundamental analysis engine — ratios, growth, quality, trends, peers.

Computes the standard fundamental metrics from supplied statement line items or
pre-computed inputs. Every output traces to its inputs; missing inputs are simply
omitted (reported via ``available``) rather than fabricated.
"""
from __future__ import annotations

from statistics import mean
from typing import Optional


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _round(d: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def ratios(f: dict) -> dict:
    """Compute valuation, profitability, leverage, and dividend ratios.

    Accepts any of: price, eps, book_value_per_share, sales_per_share, revenue,
    net_income, gross_profit, operating_income, equity, invested_capital,
    total_debt, current_assets, current_liabilities, fcf, market_cap,
    dividends_per_share, ebit, interest_expense, ebitda, enterprise_value.
    """
    out: dict[str, Optional[float]] = {}
    # Valuation
    out["pe"] = _safe_div(f.get("price"), f.get("eps"))
    out["pb"] = _safe_div(f.get("price"), f.get("book_value_per_share"))
    out["ps"] = _safe_div(f.get("price"), f.get("sales_per_share")) or _safe_div(f.get("market_cap"), f.get("revenue"))
    out["ev_ebitda"] = _safe_div(f.get("enterprise_value"), f.get("ebitda"))
    # Profitability / margins
    out["gross_margin"] = _safe_div(f.get("gross_profit"), f.get("revenue"))
    out["operating_margin"] = _safe_div(f.get("operating_income"), f.get("revenue"))
    out["net_margin"] = _safe_div(f.get("net_income"), f.get("revenue"))
    out["roe"] = _safe_div(f.get("net_income"), f.get("equity"))
    out["roic"] = _safe_div(f.get("operating_income"), f.get("invested_capital"))
    out["fcf_yield"] = _safe_div(f.get("fcf"), f.get("market_cap"))
    # Leverage / liquidity
    out["debt_to_equity"] = _safe_div(f.get("total_debt"), f.get("equity"))
    out["current_ratio"] = _safe_div(f.get("current_assets"), f.get("current_liabilities"))
    out["interest_coverage"] = _safe_div(f.get("ebit"), f.get("interest_expense"))
    # Dividend
    out["dividend_yield"] = _safe_div(f.get("dividends_per_share"), f.get("price"))
    out["payout_ratio"] = _safe_div(f.get("dividends_per_share"), f.get("eps"))
    available = [k for k, v in out.items() if v is not None]
    return {"ratios": _round({k: v for k, v in out.items() if v is not None}), "available": available}


def growth(series: dict[str, list[float]]) -> dict:
    """Year-over-year and CAGR growth from historical annual series (oldest first).

    series e.g. {"revenue": [...], "eps": [...], "fcf": [...]} .
    """
    out: dict[str, dict] = {}
    for key, values in series.items():
        vals = [v for v in values if v is not None]
        if len(vals) < 2:
            continue
        yoy = (vals[-1] - vals[-2]) / abs(vals[-2]) if vals[-2] else None
        periods = len(vals) - 1
        cagr = None
        if vals[0] > 0 and vals[-1] > 0:
            cagr = (vals[-1] / vals[0]) ** (1 / periods) - 1
        out[key] = {"yoy": round(yoy, 4) if yoy is not None else None,
                    "cagr": round(cagr, 4) if cagr is not None else None,
                    "periods": periods}
    return out


def quality_metrics(f: dict) -> dict:
    """Quality read: a 0–100 composite from margins, returns, and leverage."""
    r = ratios(f)["ratios"]
    parts = []
    def clamp(x, good, bad):
        if x is None:
            return None
        return max(0.0, min(100.0, (x - bad) / (good - bad) * 100)) if good != bad else 50.0
    for metric, good, bad in [("roe", 0.25, 0), ("roic", 0.20, 0), ("gross_margin", 0.6, 0.1),
                              ("net_margin", 0.25, 0), ("current_ratio", 2.5, 0.8)]:
        s = clamp(r.get(metric), good, bad)
        if s is not None:
            parts.append(s)
    de = r.get("debt_to_equity")
    if de is not None:
        parts.append(max(0.0, min(100.0, (2.5 - de) / (2.5 - 0.2) * 100)))
    composite = round(mean(parts), 1) if parts else None
    return {"quality_score": composite, "metrics_used": len(parts)}


def peer_comparison(target: dict, peers: list[dict], metrics: Optional[list[str]] = None) -> dict:
    """Percentile rank of the target vs. peers on the chosen metrics."""
    metrics = metrics or ["pe", "roe", "net_margin", "revenue_growth", "debt_to_equity"]
    result = {}
    pool = [target] + peers
    for m in metrics:
        vals = [p.get(m) for p in pool if isinstance(p.get(m), (int, float))]
        tv = target.get(m)
        if tv is None or len(vals) < 2:
            continue
        below = sum(1 for v in vals if v < tv)
        result[m] = {"value": round(tv, 4), "percentile": round(below / (len(vals) - 1) * 100, 1),
                     "peer_median": round(sorted(vals)[len(vals) // 2], 4)}
    return {"target": target.get("symbol"), "metrics": result, "peers": len(peers)}


def analyze(symbol: str, fundamentals: dict, history: Optional[dict] = None) -> dict:
    """Full fundamental read for one company."""
    r = ratios(fundamentals)
    out = {
        "symbol": symbol.upper(),
        **r,
        "quality": quality_metrics(fundamentals),
    }
    if history:
        out["growth"] = growth(history)
    return out
