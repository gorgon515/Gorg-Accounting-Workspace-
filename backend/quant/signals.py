"""Signal generation engine.

Produces a research signal — bull case, bear case, risk factors, catalysts,
valuation/technical views, portfolio fit, and a confidence score — by combining
the technical and factor engines. It deliberately separates Facts, Calculations,
Interpretations, and Forecasts, and never emits a trade recommendation without
the supporting analysis attached.
"""
from __future__ import annotations

from statistics import mean
from typing import Optional

from app.services import factors, risk
from . import technicals as ta


def _bias(score: float) -> str:
    return "bullish" if score >= 55 else "bearish" if score <= 45 else "neutral"


def generate_signal(symbol: str, prices: list[float], *,
                    fundamentals: Optional[dict] = None,
                    benchmark: Optional[list[float]] = None,
                    sector: Optional[str] = None) -> dict:
    if not prices or len(prices) < 20:
        raise ValueError("need at least 20 price points for a signal")

    tech = ta.analyze_extended(prices, benchmark=benchmark)
    factor = factors.score(symbol, fundamentals or {}, prices)
    rets = ta.daily_returns(prices)

    # ---- Calculations (numbers the analysis rests on) ----
    trend = tech.get("trend_score")
    mom = tech.get("momentum_score")
    comp = factor.get("composite")
    vol = tech.get("volatility_annualized")
    mdd = tech.get("max_drawdown")
    sharpe = risk.sharpe(rets)
    rs = tech.get("relative_strength")

    directional = [s for s in (trend, mom, comp) if s is not None]
    dir_score = round(mean(directional), 1) if directional else 50.0
    bias = _bias(dir_score)

    # ---- Interpretations ----
    bull, bear = [], []
    if trend is not None and trend >= 60:
        bull.append(f"Uptrend intact (trend score {trend}/100).")
    if trend is not None and trend <= 40:
        bear.append(f"Downtrend pressure (trend score {trend}/100).")
    if mom is not None and mom >= 60:
        bull.append(f"Positive momentum ({mom}/100).")
    if mom is not None and mom <= 40:
        bear.append(f"Weak momentum ({mom}/100).")
    if comp is not None and comp >= 65:
        bull.append(f"Favorable fundamentals (factor composite {comp}, {factor['rating']}).")
    if comp is not None and comp <= 45:
        bear.append(f"Weak fundamentals (factor composite {comp}, {factor['rating']}).")
    if rs and rs.get("outperforming"):
        bull.append(f"Outperforming benchmark by {rs['excess'] * 100:.1f}%.")
    if rs and not rs.get("outperforming"):
        bear.append(f"Lagging benchmark by {abs(rs['excess']) * 100:.1f}%.")
    if tech.get("rsi14") is not None and tech["rsi14"] >= 70:
        bear.append(f"Overbought (RSI {tech['rsi14']}).")
    if tech.get("rsi14") is not None and tech["rsi14"] <= 30:
        bull.append(f"Oversold (RSI {tech['rsi14']}).")

    risk_factors = []
    if vol is not None and vol > 0.4:
        risk_factors.append(f"Elevated volatility ({vol * 100:.0f}% annualized).")
    if mdd is not None and mdd > 0.3:
        risk_factors.append(f"Large historical drawdown ({mdd * 100:.0f}%).")
    if factor["coverage"]["metrics_used"] < 4:
        risk_factors.append("Thin fundamental coverage — fundamental view is low-confidence.")

    # ---- Confidence: alignment of available signals × data coverage ----
    spread = max(directional) - min(directional) if len(directional) > 1 else 0
    alignment = max(0.0, 1 - spread / 100)  # 1 = all signals agree
    coverage = min(1.0, (len(directional) / 3) * 0.6 + (1 if comp is not None else 0) * 0.4)
    confidence = round(40 + alignment * 40 + coverage * 20)  # 40–100
    conf_label = "high" if confidence >= 75 else "medium" if confidence >= 60 else "low"

    return {
        "symbol": symbol.upper(),
        "bias": bias,
        "directional_score": dir_score,
        "confidence": {"score": confidence, "label": conf_label,
                       "basis": f"signal alignment {alignment:.2f}, data coverage {coverage:.2f}"},
        "bull_case": bull or ["No clear bullish signals."],
        "bear_case": bear or ["No clear bearish signals."],
        "risk_factors": risk_factors or ["No elevated risk flags from available data."],
        "catalysts_to_watch": ["Next earnings report", "Guidance revisions", "Sector rotation",
                               "Macro data affecting the sector" + (f" ({sector})" if sector else "")],
        "valuation_view": _valuation_view(comp, factor),
        "technical_view": tech.get("explanations", []),
        "portfolio_fit": _portfolio_fit(vol, sharpe, sector),
        "evidence": {
            "facts": {"price": tech.get("price"), "points": tech.get("points"), "sector": sector},
            "calculations": {"trend_score": trend, "momentum_score": mom, "factor_composite": comp,
                             "rsi14": tech.get("rsi14"), "volatility_annualized": vol,
                             "max_drawdown": mdd, "sharpe": sharpe,
                             "relative_strength": rs},
            "interpretations": {"bias": bias, "bull": bull, "bear": bear, "risks": risk_factors},
            "forecasts": [
                "Forecast (not certainty): if the current trend and momentum persist, the bias above "
                "is more likely to play out; a break of the trend invalidates it.",
            ],
        },
        "disclaimer": "Research signal, not a trade recommendation or guarantee. Facts/calculations are "
                      "measured; interpretations and forecasts are judgments and may be wrong.",
    }


def _valuation_view(comp: Optional[float], factor: dict) -> str:
    if comp is None:
        return "Insufficient fundamental data for a valuation view."
    v = factor["factors"].get("value", {}).get("score")
    if v is None:
        return f"Composite {comp} ({factor['rating']}); valuation inputs not supplied."
    if v >= 65:
        return f"Screens inexpensive on supplied multiples (value score {v})."
    if v <= 40:
        return f"Screens expensive on supplied multiples (value score {v})."
    return f"Fairly valued on supplied multiples (value score {v})."


def _portfolio_fit(vol: Optional[float], sharpe: Optional[float], sector: Optional[str]) -> str:
    bits = []
    if vol is not None:
        bits.append("higher-risk sleeve" if vol > 0.35 else "core/lower-volatility sleeve")
    if sharpe is not None:
        bits.append(f"historical Sharpe {sharpe}")
    if sector:
        bits.append(f"adds {sector} exposure — check concentration")
    return "; ".join(bits) or "Insufficient data for portfolio-fit assessment."
