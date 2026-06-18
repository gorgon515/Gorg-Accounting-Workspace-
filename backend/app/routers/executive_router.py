"""HELIOS Executive Command Center API — the flagship aggregated dashboard.

Pulls together top priorities, risks, opportunities, forecasts, goal progress,
and system health into one home-screen payload.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/executive", tags=["executive"])


@router.get("/command-center")
def command_center():
    """One-call aggregation for the Executive Command Center home screen."""
    out: dict = {}

    # Opportunities & risks (use latest persisted scan; scan if empty).
    try:
        from intelligence.opportunities import get_opportunity_engine
        oe = get_opportunity_engine()
        opps = oe.list(status="open")
        if not opps:
            opps = oe.scan()
        out["opportunities"] = opps[:5]
    except Exception as e:
        out["opportunities"] = []
        out["opportunities_error"] = str(e)

    try:
        from intelligence.risks import get_risk_engine
        re = get_risk_engine()
        risks = re.list(status="open")
        if not risks:
            risks = re.scan()
        out["risks"] = risks[:5]
        out["risk_summary"] = re.summary()
    except Exception as e:
        out["risks"] = []
        out["risks_error"] = str(e)

    # Strategic recommendations.
    try:
        from reasoning.engine import get_reasoning_engine
        out["recommendations"] = get_reasoning_engine().recommend()["recommendations"][:5]
    except Exception as e:
        out["recommendations"] = []
        out["recommendations_error"] = str(e)

    # Forecast snapshot (expected scenario, 12 months).
    try:
        from forecasting.engine import get_forecast_engine
        cf = get_forecast_engine().forecast_metric("cash_flow", 12)
        out["forecast"] = {
            "metric": "cash_flow",
            "expected_ending": cf["scenarios"]["expected"]["ending_value"],
            "confidence": cf["confidence"],
        }
    except Exception as e:
        out["forecast"] = {}
        out["forecast_error"] = str(e)

    # Goal progress + financials.
    try:
        from intelligence.sources import goals_snapshot, accounting_snapshot, tasks_snapshot
        goals = goals_snapshot()
        acct = accounting_snapshot()
        tasks = tasks_snapshot()
        out["goals"] = {"active": goals["active"], "at_risk": goals["at_risk"],
                        "total": goals["total"]}
        out["financials"] = {"revenue": acct["revenue"], "expenses": acct["expenses"],
                             "net": acct["net"]}
        out["tasks"] = {"pending": tasks["pending_count"]}
    except Exception as e:
        out["context_error"] = str(e)

    # Pending proposals.
    try:
        from reasoning.proposals import get_proposal_loop
        out["pending_proposals"] = get_proposal_loop().stats().get("pending", 0)
    except Exception as e:
        out["pending_proposals"] = 0

    # System health.
    try:
        from health.monitor import HealthMonitor
        out["health"] = HealthMonitor().check_all()
    except Exception:
        out["health"] = {"status": "unknown"}

    return out


@router.get("/morning-briefing")
def morning_briefing():
    """Run the autonomous proposal loop and return the day's briefing + drafts."""
    try:
        from reasoning.proposals import get_proposal_loop
        return get_proposal_loop().run_daily()
    except Exception as e:
        return {"error": str(e)}
