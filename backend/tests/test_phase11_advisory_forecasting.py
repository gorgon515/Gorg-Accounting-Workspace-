"""Phase 11 — Forecasting, scenario simulation, and advisory tests."""
from __future__ import annotations

import pytest


# ---- Forecasting ----

def test_forecast_metric():
    from forecasting.engine import ForecastEngine
    fe = ForecastEngine()
    result = fe.forecast_metric("revenue", months=12)
    assert set(result["scenarios"]) == {"conservative", "expected", "aggressive"}
    assert len(result["scenarios"]["expected"]["series"]) == 12
    assert 0 <= result["confidence"] <= 1


def test_forecast_scenarios_ordered():
    from forecasting.engine import ForecastEngine
    fe = ForecastEngine()
    r = fe.forecast_metric("revenue", months=24)
    cons = r["scenarios"]["conservative"]["ending_value"]
    agg = r["scenarios"]["aggressive"]["ending_value"]
    assert agg > cons


def test_forecast_invalid_metric():
    from forecasting.engine import ForecastEngine
    fe = ForecastEngine()
    with pytest.raises(ValueError):
        fe.forecast_metric("not_a_metric")


def test_forecast_all():
    from forecasting.engine import ForecastEngine
    fe = ForecastEngine()
    allf = fe.forecast_all(6)
    assert "revenue" in allf and "cash_flow" in allf


def test_retirement_projection():
    from forecasting.engine import ForecastEngine
    fe = ForecastEngine()
    r = fe.retirement_projection(50000, 1000, years=20)
    assert r["scenarios"]["aggressive"] > r["scenarios"]["conservative"]


# ---- Scenario simulation ----

def test_scenario_revenue_increase():
    from forecasting.scenarios import ScenarioSimulator
    sim = ScenarioSimulator()
    result = sim.simulate({"revenue_change_pct": 20}, label="growth")
    assert result["projected"]["revenue"] > result["baseline"]["revenue"]
    assert result["delta_net"] != 0


def test_scenario_hiring():
    from forecasting.scenarios import ScenarioSimulator
    sim = ScenarioSimulator()
    result = sim.simulate({"headcount_delta": 2, "avg_salary": 90000})
    assert result["projected"]["expenses"] > result["baseline"]["expenses"]


def test_scenario_sensitivity():
    from forecasting.scenarios import ScenarioSimulator
    sim = ScenarioSimulator()
    result = sim.sensitivity({"revenue_change_pct": 0, "expense_change_pct": 0})
    assert "sensitivity" in result
    assert len(result["sensitivity"]) >= 1
    # rows sorted by swing descending
    swings = [r["swing"] for r in result["sensitivity"]]
    assert swings == sorted(swings, reverse=True)


# ---- Advisory ----

def test_personal_dashboard():
    from advisory.personal import PersonalAdvisory
    pa = PersonalAdvisory()
    dash = pa.life_dashboard()
    assert "overall_progress" in dash
    assert "categories" in dash


def test_personal_recommendations_horizons():
    from advisory.personal import PersonalAdvisory
    pa = PersonalAdvisory()
    for h in ("weekly", "monthly", "quarterly", "annual"):
        rec = pa.recommendations(h)
        assert rec["horizon"] == h
        assert len(rec["recommendations"]) > 0


def test_personal_invalid_horizon():
    from advisory.personal import PersonalAdvisory
    pa = PersonalAdvisory()
    with pytest.raises(ValueError):
        pa.recommendations("hourly")


def test_business_analysis():
    from advisory.business import BusinessAdvisory
    ba = BusinessAdvisory()
    analysis = ba.firm_analysis()
    assert "profit_margin_pct" in analysis
    assert analysis["health"] in ("strong", "fair", "weak", "critical")


def test_business_executive_report():
    from advisory.business import BusinessAdvisory
    ba = BusinessAdvisory()
    report = ba.executive_report()
    assert "growth_recommendations" in report
    assert "operational_recommendations" in report


def test_business_capacity():
    from advisory.business import BusinessAdvisory
    ba = BusinessAdvisory()
    cap = ba.capacity_planning(billable_hours_available=160, avg_engagement_hours=20)
    assert "utilization_pct" in cap
    assert cap["status"] in ("healthy", "near_capacity", "over_capacity")
