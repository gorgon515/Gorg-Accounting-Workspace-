"""
Event Intelligence Agent: monitors event streams, runs fusion engine, detects compound patterns.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class EventIntelligenceAgent(BaseAgent):
    agent_id = "agent_event"
    agent_name = "Event Intelligence Agent"
    domain = "operations"
    description = "Monitors events, runs intelligence fusion, detects compound patterns and risk signals"
    allowed_action_types = ["alert", "advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []

        try:
            from event_monitor.engine import get_event_monitor
            em = get_event_monitor()
            scan_results = em.scan_intelligence()
            for event in scan_results[:10]:
                findings.append({
                    "type": "triggered_event",
                    "event_id": event.get("id"),
                    "category": event.get("category"),
                    "title": event.get("title"),
                    "severity": event.get("severity"),
                })
            deadline_events = em.check_deadlines()
            for event in deadline_events[:5]:
                findings.append({
                    "type": "deadline_event",
                    "event_id": event.get("id"),
                    "title": event.get("title"),
                    "severity": event.get("severity"),
                    "due_date": event.get("due_date"),
                })
                if event.get("severity") in ("critical", "high"):
                    proposed_actions.append({
                        "type": "alert",
                        "title": event.get("title", ""),
                        "description": event.get("description", ""),
                        "payload": {"event_id": event.get("id")},
                        "requires_approval": False,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "event_monitor", "error": str(e)})

        try:
            from fusion.engine import get_fusion_engine
            fe = get_fusion_engine()
            fusion_events = fe.run_fusion()
            for event in fusion_events[:5]:
                findings.append({
                    "type": "fusion_event",
                    "event_id": event.get("id"),
                    "title": event.get("title"),
                    "pattern": event.get("pattern"),
                    "confidence": event.get("confidence"),
                    "action_type": event.get("action_type"),
                })
                if event.get("confidence", 0) >= 0.6:
                    proposed_actions.append({
                        "type": "advisory",
                        "title": f"Intelligence Fusion Alert: {event.get('title', '')}",
                        "description": event.get("description", ""),
                        "payload": {
                            "fusion_event_id": event.get("id"),
                            "draft_action": event.get("draft_action"),
                        },
                        "requires_approval": True,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "fusion_engine", "error": str(e)})

        self.remember("last_event_count", len(findings))
        summary = f"Event agent detected {len(findings)} item(s), proposed {len(proposed_actions)} action(s)."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_event_agent() -> EventIntelligenceAgent:
    global _instance
    if _instance is None:
        _instance = EventIntelligenceAgent()
    return _instance
