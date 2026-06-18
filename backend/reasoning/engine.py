"""StrategicReasoningEngine — goal decomposition, dependency/trade-off/constraint
analysis, priority optimization, and risk-adjusted recommendations.
"""
from __future__ import annotations

from typing import Optional


class StrategicReasoningEngine:
    def __init__(self):
        pass

    # ---- Goal decomposition ----

    def decompose_goal(self, goal: str, target_value: float = 100.0,
                       horizon_months: int = 12) -> dict:
        """Break a goal into milestones with a dependency-ordered plan."""
        per = target_value / max(horizon_months, 1)
        milestones = []
        for m in range(1, horizon_months + 1):
            milestones.append({
                "month": m,
                "target_cumulative": round(per * m, 2),
                "depends_on": m - 1 if m > 1 else None,
            })
        return {
            "goal": goal, "target_value": target_value, "horizon_months": horizon_months,
            "milestones": milestones,
            "critical_path": [m["month"] for m in milestones],
        }

    # ---- Priority optimization ----

    def prioritize(self, items: list[dict]) -> list[dict]:
        """Rank items by a weighted impact/effort/urgency score.

        Each item: {id, title, impact(0..1), effort(0..1), urgency(0..1)}.
        Score favors high impact + urgency and penalizes effort.
        """
        ranked = []
        for it in items:
            impact = float(it.get("impact", 0.5))
            effort = float(it.get("effort", 0.5))
            urgency = float(it.get("urgency", 0.5))
            score = round((0.5 * impact + 0.3 * urgency) / (1.0 + 0.5 * effort) * 100, 1)
            ranked.append({**it, "priority_score": score})
        return sorted(ranked, key=lambda x: x["priority_score"], reverse=True)

    # ---- Trade-off & constraint analysis ----

    def analyze_tradeoffs(self, options: list[dict]) -> dict:
        """Compare options on cost/benefit/risk. Each option:
        {name, benefit(0..1), cost(0..1), risk(0..1)}."""
        scored = []
        for o in options:
            benefit = float(o.get("benefit", 0.5))
            cost = float(o.get("cost", 0.5))
            risk = float(o.get("risk", 0.5))
            # Risk-adjusted value.
            value = round((benefit * (1.0 - 0.5 * risk)) - 0.4 * cost, 3)
            scored.append({**o, "risk_adjusted_value": value})
        scored.sort(key=lambda x: x["risk_adjusted_value"], reverse=True)
        return {
            "options": scored,
            "recommended": scored[0]["name"] if scored else None,
            "alternatives": [s["name"] for s in scored[1:3]],
        }

    def check_constraints(self, plan: dict, constraints: dict) -> dict:
        """Validate a plan's resource demands against available constraints."""
        violations = []
        demands = plan.get("demands", {})
        for resource, available in constraints.items():
            demanded = demands.get(resource, 0)
            if demanded > available:
                violations.append({
                    "resource": resource, "demanded": demanded, "available": available,
                    "shortfall": round(demanded - available, 2),
                })
        return {"feasible": not violations, "violations": violations}

    # ---- Strategic recommendation synthesis ----

    def recommend(self) -> dict:
        """Synthesize a risk-adjusted strategic recommendation set from live signals."""
        from intelligence.opportunities import get_opportunity_engine
        from intelligence.risks import get_risk_engine
        opps = get_opportunity_engine().scan()
        risks = get_risk_engine().scan()

        top_opps = opps[:3]
        top_risks = risks[:3]

        recommendations = []
        for o in top_opps:
            recommendations.append({
                "type": "opportunity", "title": o["title"],
                "rationale": o["description"], "score": o["score"],
                "domain": o["domain"],
            })
        for r in top_risks:
            if r["severity"] in ("critical", "high"):
                recommendations.append({
                    "type": "risk_mitigation", "title": f"Mitigate: {r['title']}",
                    "rationale": (r["mitigation"][0] if r["mitigation"] else r["description"]),
                    "score": r["score"], "domain": r["domain"],
                })
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "recommendations": recommendations,
            "opportunity_count": len(opps),
            "risk_count": len(risks),
            "summary": self._summary(top_opps, top_risks),
        }

    @staticmethod
    def _summary(opps: list[dict], risks: list[dict]) -> str:
        parts = []
        if opps:
            parts.append(f"Top opportunity: {opps[0]['title']} (score {opps[0]['score']}).")
        if risks:
            parts.append(f"Top risk: {risks[0]['title']} ({risks[0]['severity']}).")
        if not parts:
            return "No significant opportunities or risks detected from current data."
        return " ".join(parts)


_instance: Optional[StrategicReasoningEngine] = None


def get_reasoning_engine() -> StrategicReasoningEngine:
    global _instance
    if _instance is None:
        _instance = StrategicReasoningEngine()
    return _instance
