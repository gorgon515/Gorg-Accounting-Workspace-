"""BusinessAdvisory — firm-level operational and growth advisory."""
from __future__ import annotations

from typing import Optional


class BusinessAdvisory:
    def __init__(self):
        pass

    def firm_analysis(self) -> dict:
        from intelligence.sources import accounting_snapshot, tasks_snapshot
        acct = accounting_snapshot()
        tasks = tasks_snapshot()

        margin = (acct["net"] / acct["revenue"] * 100) if acct["revenue"] > 0 else 0.0
        ar_ratio = (acct["ar_outstanding"] / acct["revenue"] * 100) if acct["revenue"] > 0 else 0.0

        health = "strong"
        if margin < 0:
            health = "critical"
        elif margin < 10:
            health = "weak"
        elif margin < 20:
            health = "fair"

        return {
            "revenue": acct["revenue"],
            "expenses": acct["expenses"],
            "net_income": acct["net"],
            "profit_margin_pct": round(margin, 1),
            "ar_ratio_pct": round(ar_ratio, 1),
            "workload_pending": tasks["pending_count"],
            "health": health,
        }

    def executive_report(self) -> dict:
        from intelligence.opportunities import get_opportunity_engine
        from intelligence.risks import get_risk_engine
        analysis = self.firm_analysis()
        opps = get_opportunity_engine().list(status="open")[:3]
        risks = get_risk_engine().list(status="open")[:3]

        growth_recs = []
        if analysis["profit_margin_pct"] < 20:
            growth_recs.append("Improve margin: review pricing on lowest-margin service lines.")
        if analysis["ar_ratio_pct"] > 20:
            growth_recs.append("Tighten collections to free up working capital.")
        if analysis["workload_pending"] > 10:
            growth_recs.append("Add capacity or automate to relieve workload bottlenecks.")
        if not growth_recs:
            growth_recs.append("Maintain trajectory; reinvest surplus into client acquisition.")

        operational_recs = []
        if analysis["workload_pending"] > 0:
            operational_recs.append(f"Triage {analysis['workload_pending']} open work items.")
        operational_recs.append("Standardize recurring engagements into reusable workflows.")

        return {
            "analysis": analysis,
            "top_opportunities": [{"title": o["title"], "score": o["score"]} for o in opps],
            "top_risks": [{"title": r["title"], "severity": r["severity"]} for r in risks],
            "growth_recommendations": growth_recs,
            "operational_recommendations": operational_recs,
        }

    def capacity_planning(self, billable_hours_available: float = 160.0,
                          avg_engagement_hours: float = 20.0) -> dict:
        from intelligence.sources import tasks_snapshot
        tasks = tasks_snapshot()
        committed = tasks["pending_count"] * avg_engagement_hours
        utilization = (committed / billable_hours_available * 100) if billable_hours_available else 0
        return {
            "available_hours": billable_hours_available,
            "committed_hours": round(committed, 1),
            "utilization_pct": round(utilization, 1),
            "status": "over_capacity" if utilization > 100 else
                      "near_capacity" if utilization > 80 else "healthy",
            "additional_capacity_hours": round(max(billable_hours_available - committed, 0), 1),
        }


_instance: Optional[BusinessAdvisory] = None


def get_business_advisory() -> BusinessAdvisory:
    global _instance
    if _instance is None:
        _instance = BusinessAdvisory()
    return _instance
