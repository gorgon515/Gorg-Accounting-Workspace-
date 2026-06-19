"""PersonalAdvisory — life dashboard and time-horizon recommendations."""
from __future__ import annotations

from typing import Optional


class PersonalAdvisory:
    def __init__(self):
        pass

    def life_dashboard(self) -> dict:
        from intelligence.sources import goals_snapshot, tasks_snapshot, accounting_snapshot
        goals = goals_snapshot()
        tasks = tasks_snapshot()
        acct = accounting_snapshot()

        by_category: dict[str, list] = {}
        for g in goals.get("goals", []):
            by_category.setdefault(g.get("category", "personal"), []).append(g)

        categories = []
        for cat, items in by_category.items():
            avg = sum(i.get("progress", 0) for i in items) / max(len(items), 1)
            categories.append({"category": cat, "goal_count": len(items),
                               "avg_progress": round(avg, 1)})

        overall = (sum(g.get("progress", 0) for g in goals.get("goals", []))
                   / max(goals["total"], 1)) if goals["total"] else 0
        return {
            "overall_progress": round(overall, 1),
            "categories": categories,
            "active_goals": goals["active"],
            "at_risk_goals": goals["at_risk"],
            "pending_tasks": tasks["pending_count"],
            "financial_net": acct["net"],
        }

    def recommendations(self, horizon: str = "weekly") -> dict:
        """Generate horizon-specific recommendations (weekly/monthly/quarterly/annual)."""
        if horizon not in ("weekly", "monthly", "quarterly", "annual"):
            raise ValueError("horizon must be weekly, monthly, quarterly, or annual")
        from intelligence.sources import goals_snapshot, tasks_snapshot
        goals = goals_snapshot()
        tasks = tasks_snapshot()
        recs = []

        if horizon == "weekly":
            if tasks["pending_count"] > 0:
                recs.append(f"Clear your top {min(tasks['pending_count'], 5)} priority tasks this week.")
            if goals["at_risk"] > 0:
                recs.append(f"Spend focused time on {goals['at_risk']} at-risk goal(s).")
            recs.append("Review the daily strategic briefing each morning.")
        elif horizon == "monthly":
            recs.append("Reconcile financial accounts and review month-end reports.")
            if goals["active"] > 0:
                recs.append(f"Reassess progress on {goals['active']} active goals; rebalance effort.")
            recs.append("Run a scenario simulation on a key decision you're weighing.")
        elif horizon == "quarterly":
            recs.append("Conduct a quarterly goal review and set next-quarter targets.")
            recs.append("Review CPA/career progress and update your development plan.")
            recs.append("Refresh financial forecasts for the next 12 months.")
        else:  # annual
            recs.append("Complete annual planning: financial, career, and personal goals.")
            recs.append("Review retirement trajectory and contribution strategy.")
            recs.append("Audit the past year's recommendation accuracy and adjust strategy.")

        return {"horizon": horizon, "recommendations": recs,
                "context": {"active_goals": goals["active"], "at_risk": goals["at_risk"],
                            "pending_tasks": tasks["pending_count"]}}


_instance: Optional[PersonalAdvisory] = None


def get_personal_advisory() -> PersonalAdvisory:
    global _instance
    if _instance is None:
        _instance = PersonalAdvisory()
    return _instance
