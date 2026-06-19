"""ScenarioSimulator — 'what-if' analysis over a base financial model.

Applies parameter deltas (revenue change, headcount, contribution changes, etc.)
to the current baseline and reports projected outcomes, risks, opportunities, and
a one-at-a-time sensitivity analysis.
"""
from __future__ import annotations

from typing import Optional

KNOWN_LEVERS = {
    "revenue_change_pct": "Revenue change (%)",
    "expense_change_pct": "Expense change (%)",
    "headcount_delta": "Headcount change (FTE)",
    "avg_salary": "Average annual salary per hire",
    "retirement_contribution_delta": "Monthly retirement contribution change",
    "tax_rate_delta": "Effective tax-rate change (pp)",
}


class ScenarioSimulator:
    def __init__(self):
        pass

    def _baseline(self) -> dict:
        from intelligence.sources import accounting_snapshot
        acct = accounting_snapshot()
        revenue = acct["revenue"] if acct["revenue"] > 0 else 120000.0
        expenses = acct["expenses"] if acct["expenses"] > 0 else 84000.0
        return {"revenue": revenue, "expenses": expenses, "net": revenue - expenses}

    def simulate(self, levers: dict, label: str = "scenario") -> dict:
        base = self._baseline()
        revenue = base["revenue"]
        expenses = base["expenses"]

        rev_pct = float(levers.get("revenue_change_pct", 0) or 0) / 100.0
        exp_pct = float(levers.get("expense_change_pct", 0) or 0) / 100.0
        headcount = float(levers.get("headcount_delta", 0) or 0)
        avg_salary = float(levers.get("avg_salary", 90000) or 90000)
        tax_delta = float(levers.get("tax_rate_delta", 0) or 0) / 100.0

        new_revenue = revenue * (1.0 + rev_pct)
        new_expenses = expenses * (1.0 + exp_pct) + headcount * avg_salary
        new_net = new_revenue - new_expenses
        tax_effect = -new_net * tax_delta if new_net > 0 else 0.0
        new_net_after_tax = new_net + tax_effect

        base_net = base["net"]
        delta_net = new_net_after_tax - base_net

        risks, opportunities = [], []
        if new_net < 0:
            risks.append("Scenario turns net income negative — runway risk.")
        if headcount > 0 and new_net < base_net:
            risks.append(f"Adding {headcount:.0f} FTE reduces net income by "
                         f"${base_net - new_net_after_tax:.0f} until capacity is utilized.")
        if delta_net > 0:
            opportunities.append(f"Net income improves by ${delta_net:.0f}.")
        if rev_pct > 0 and exp_pct <= 0:
            opportunities.append("Revenue growth with flat costs expands margin.")

        return {
            "label": label,
            "baseline": {"revenue": round(revenue, 2), "expenses": round(expenses, 2),
                         "net": round(base_net, 2)},
            "projected": {"revenue": round(new_revenue, 2), "expenses": round(new_expenses, 2),
                          "net": round(new_net_after_tax, 2)},
            "delta_net": round(delta_net, 2),
            "delta_net_pct": round((delta_net / max(abs(base_net), 1)) * 100, 1),
            "risks": risks,
            "opportunities": opportunities,
            "levers": levers,
        }

    def sensitivity(self, levers: dict, vary: Optional[list[str]] = None,
                    step_pct: float = 10.0) -> dict:
        """One-at-a-time sensitivity: perturb each lever ±step and measure net impact."""
        vary = vary or ["revenue_change_pct", "expense_change_pct"]
        base_result = self.simulate(levers)
        base_net = base_result["projected"]["net"]
        rows = []
        for lever in vary:
            up = dict(levers)
            up[lever] = float(levers.get(lever, 0) or 0) + step_pct
            down = dict(levers)
            down[lever] = float(levers.get(lever, 0) or 0) - step_pct
            net_up = self.simulate(up)["projected"]["net"]
            net_down = self.simulate(down)["projected"]["net"]
            rows.append({
                "lever": lever,
                "label": KNOWN_LEVERS.get(lever, lever),
                "net_up": round(net_up, 2),
                "net_down": round(net_down, 2),
                "swing": round(abs(net_up - net_down), 2),
            })
        rows.sort(key=lambda r: r["swing"], reverse=True)
        return {"base_net": round(base_net, 2), "step_pct": step_pct, "sensitivity": rows}

    def levers(self) -> list[dict]:
        return [{"key": k, "label": v} for k, v in KNOWN_LEVERS.items()]


_instance: Optional[ScenarioSimulator] = None


def get_scenario_simulator() -> ScenarioSimulator:
    global _instance
    if _instance is None:
        _instance = ScenarioSimulator()
    return _instance
