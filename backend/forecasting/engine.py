"""ForecastEngine — projects financial metrics with conservative/expected/aggressive
scenario ranges and confidence scoring.

Projections use compound growth over a base value. Confidence reflects the spread
between scenarios and the availability/quality of source data.
"""
from __future__ import annotations

import statistics
from typing import Optional

# Default monthly growth assumptions per scenario band.
SCENARIO_GROWTH = {
    "conservative": -0.01,
    "expected": 0.02,
    "aggressive": 0.05,
}


def _project(base: float, monthly_growth: float, months: int) -> list[float]:
    series, value = [], base
    for _ in range(months):
        value = value * (1.0 + monthly_growth)
        series.append(round(value, 2))
    return series


class ForecastEngine:
    def __init__(self):
        pass

    def _base_values(self) -> dict:
        from intelligence.sources import accounting_snapshot
        acct = accounting_snapshot()
        # Treat ledger figures as a monthly run-rate baseline; fall back to sane defaults.
        revenue = acct["revenue"] if acct["revenue"] > 0 else 10000.0
        expenses = acct["expenses"] if acct["expenses"] > 0 else 7000.0
        return {
            "available": acct["available"],
            "revenue": revenue,
            "expenses": expenses,
            "cash_flow": revenue - expenses,
            "savings": max((revenue - expenses) * 0.3, 0.0),
        }

    def forecast_metric(self, metric: str, months: int = 12,
                        base: Optional[float] = None) -> dict:
        if months < 1 or months > 120:
            raise ValueError("months must be between 1 and 120")
        bases = self._base_values()
        if base is None:
            base = bases.get(metric)
            if base is None:
                raise ValueError(f"Unknown metric: {metric}")
        scenarios = {}
        for name, growth in SCENARIO_GROWTH.items():
            series = _project(base, growth, months)
            scenarios[name] = {
                "monthly_growth": growth,
                "series": series,
                "ending_value": series[-1],
                "total": round(sum(series), 2),
            }
        # Confidence: tighter spread + available data → higher confidence.
        endings = [s["ending_value"] for s in scenarios.values()]
        spread = (max(endings) - min(endings)) / max(abs(statistics.mean(endings)), 1)
        confidence = round(max(0.2, min(0.95, (1.0 - min(spread, 1.0)) * (1.0 if bases["available"] else 0.7))), 2)
        return {
            "metric": metric, "base_value": round(base, 2), "months": months,
            "scenarios": scenarios, "confidence": confidence,
            "data_available": bases["available"],
        }

    def forecast_all(self, months: int = 12) -> dict:
        metrics = ["revenue", "expenses", "cash_flow", "savings"]
        return {m: self.forecast_metric(m, months) for m in metrics}

    def retirement_projection(self, current_assets: float, monthly_contribution: float,
                              years: int = 30, annual_return: float = 0.07) -> dict:
        months = years * 12
        monthly_return = annual_return / 12
        scenarios = {}
        for name, ret_adj in (("conservative", -0.03), ("expected", 0.0), ("aggressive", 0.03)):
            r = (annual_return + ret_adj) / 12
            value = current_assets
            for _ in range(months):
                value = value * (1.0 + r) + monthly_contribution
            scenarios[name] = round(value, 2)
        return {
            "current_assets": current_assets, "monthly_contribution": monthly_contribution,
            "years": years, "scenarios": scenarios, "confidence": 0.6,
        }


_instance: Optional[ForecastEngine] = None


def get_forecast_engine() -> ForecastEngine:
    global _instance
    if _instance is None:
        _instance = ForecastEngine()
    return _instance
