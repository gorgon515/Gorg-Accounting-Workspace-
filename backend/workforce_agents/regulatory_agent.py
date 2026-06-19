"""
Regulatory Intelligence Agent: monitors tax law, accounting standards, SEC rules.
Proposes client advisories for human review — never files or submits autonomously.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class RegulatoryIntelligenceAgent(BaseAgent):
    agent_id = "agent_regulatory"
    agent_name = "Regulatory Intelligence Agent"
    domain = "tax"
    description = "Monitors IRS guidance, FASB updates, SEC rules, and compliance requirements"
    allowed_action_types = ["advisory", "alert"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []

        try:
            from cpa_ops.monitor import get_cpa_monitor
            monitor = get_cpa_monitor()
            new_updates = monitor.ingest_regulatory_updates()
            for update in new_updates[:10]:
                findings.append({
                    "type": "regulatory_update",
                    "category": update.get("category"),
                    "title": update.get("title"),
                    "priority": update.get("priority"),
                    "action_required": bool(update.get("action_required")),
                })
            high_priority = [u for u in new_updates if u.get("priority") == "high"]
            if high_priority:
                proposed_actions.append({
                    "type": "advisory",
                    "title": f"Review {len(high_priority)} high-priority regulatory update(s)",
                    "description": "New high-priority regulatory updates detected. Draft advisories have been created for review.",
                    "payload": {"update_ids": [u.get("id") for u in high_priority]},
                    "requires_approval": True,
                })
        except Exception as e:
            findings.append({"type": "error", "source": "cpa_monitor", "error": str(e)})

        try:
            from live_intelligence.monitor import get_monitor
            monitor_intel = get_monitor()
            tax_items = monitor_intel.list_items(domain="tax", limit=10)
            accounting_items = monitor_intel.list_items(domain="accounting", limit=10)
            for item in (tax_items + accounting_items)[:8]:
                findings.append({
                    "type": "intelligence_item",
                    "title": item.get("title", ""),
                    "domain": item.get("domain", ""),
                    "source": item.get("source", ""),
                    "importance": item.get("importance", 0.5),
                })
        except Exception as e:
            findings.append({"type": "error", "source": "live_intel", "error": str(e)})

        try:
            from event_monitor.engine import get_event_monitor
            em = get_event_monitor()
            events = em.list_events(category="tax_regulatory", limit=5)
            events += em.list_events(category="accounting_standards", limit=5)
            for event in events[:5]:
                findings.append({
                    "type": "monitored_event",
                    "title": event.get("title"),
                    "severity": event.get("severity"),
                    "category": event.get("category"),
                })
        except Exception as e:
            findings.append({"type": "error", "source": "event_monitor", "error": str(e)})

        self.remember("last_update_count", len(findings))
        summary = f"Regulatory agent reviewed {len(findings)} items, proposed {len(proposed_actions)} action(s)."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_regulatory_agent() -> RegulatoryIntelligenceAgent:
    global _instance
    if _instance is None:
        _instance = RegulatoryIntelligenceAgent()
    return _instance
