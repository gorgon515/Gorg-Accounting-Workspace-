"""
Economic Intelligence Agent: tracks macro indicators, Fed policy, employment data.
Proposes briefings and risk assessments — never executes financial actions.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class EconomicIntelligenceAgent(BaseAgent):
    agent_id = "agent_economic"
    agent_name = "Economic Intelligence Agent"
    domain = "finance"
    description = "Tracks GDP, CPI, unemployment, Fed policy, yield curve, and macro trends"
    allowed_action_types = ["signal", "advisory"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []

        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            series_map = {
                "GDP": "GDP Growth",
                "CPIAUCSL": "CPI Inflation",
                "UNRATE": "Unemployment Rate",
                "FEDFUNDS": "Fed Funds Rate",
                "GS10": "10-Year Treasury Yield",
            }
            eco_data = {}
            for series_id, name in series_map.items():
                rows = hub.get_economic(series_id, limit=2)
                if rows:
                    current = rows[0].get("value")
                    prev = rows[1].get("value") if len(rows) > 1 else None
                    change = round(current - prev, 3) if (current is not None and prev is not None) else None
                    eco_data[series_id] = {"name": name, "current": current, "change": change}
                    findings.append({
                        "type": "economic_indicator",
                        "series": series_id,
                        "name": name,
                        "value": current,
                        "change": change,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "economic_data", "error": str(e)})

        try:
            from live_intelligence.monitor import get_monitor
            monitor = get_monitor()
            items = monitor.list_items(domain="finance", limit=10)
            for item in items[:5]:
                findings.append({
                    "type": "intelligence_item",
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "importance": item.get("importance", 0.5),
                })
        except Exception as e:
            findings.append({"type": "error", "source": "live_intel", "error": str(e)})

        if findings:
            proposed_actions.append({
                "type": "advisory",
                "title": "Economic Intelligence Brief Ready",
                "description": f"Economic agent compiled {len(findings)} macro data points. Review for client briefings.",
                "payload": {"finding_count": len(findings)},
                "requires_approval": False,
            })

        self.remember("last_run_findings_count", len(findings))
        summary = f"Economic Intelligence Agent gathered {len(findings)} macro data points."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_economic_agent() -> EconomicIntelligenceAgent:
    global _instance
    if _instance is None:
        _instance = EconomicIntelligenceAgent()
    return _instance
