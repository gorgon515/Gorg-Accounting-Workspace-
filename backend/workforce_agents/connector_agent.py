"""
Connector Agent: manages data source health, polls connectors, ingests data.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class ConnectorAgent(BaseAgent):
    agent_id = "agent_connector"
    agent_name = "Connector Agent"
    domain = "operations"
    description = "Monitors connector health, polls data sources, reports ingestion statistics"
    allowed_action_types = ["alert", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []
        connector_id = inputs.get("connector_id")

        try:
            from connectors.registry import get_registry
            registry = get_registry()
            if connector_id:
                health = registry.health_check(connector_id)
                findings.append({
                    "type": "health_check",
                    "connector_id": connector_id,
                    "healthy": health.get("healthy"),
                    "latency_ms": health.get("latency_ms"),
                    "error": health.get("error"),
                })
                if not health.get("healthy"):
                    proposed_actions.append({
                        "type": "alert",
                        "title": f"Connector Offline: {connector_id}",
                        "description": f"Health check failed: {health.get('error', 'unknown error')}",
                        "payload": {"connector_id": connector_id},
                        "requires_approval": False,
                    })
            else:
                connectors = registry.list()
                for c in connectors:
                    cid = c.get("id")
                    try:
                        health = registry.health_check(cid)
                        findings.append({
                            "type": "connector_status",
                            "connector_id": cid,
                            "name": c.get("name"),
                            "healthy": health.get("healthy"),
                            "status": c.get("status"),
                        })
                        if not health.get("healthy"):
                            proposed_actions.append({
                                "type": "alert",
                                "title": f"Connector Issue: {c.get('name', cid)}",
                                "description": health.get("error", "Health check failed"),
                                "payload": {"connector_id": cid},
                                "requires_approval": False,
                            })
                    except Exception as e:
                        findings.append({
                            "type": "error",
                            "connector_id": cid,
                            "error": str(e),
                        })
        except Exception as e:
            findings.append({"type": "error", "source": "connector_registry", "error": str(e)})

        poll_targets = inputs.get("poll", [])
        for cid in poll_targets[:3]:
            try:
                from live_intelligence.monitor import get_monitor
                monitor = get_monitor()
                result = monitor.poll_connector(cid)
                findings.append({
                    "type": "poll_result",
                    "connector_id": cid,
                    "new_items": result.get("new_items", 0),
                    "status": result.get("status", "unknown"),
                })
            except Exception as e:
                findings.append({"type": "error", "connector_id": cid, "error": str(e)})

        self.remember("last_connector_scan", len(findings))
        summary = f"Connector agent checked {len(findings)} connector(s)."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_connector_agent() -> ConnectorAgent:
    global _instance
    if _instance is None:
        _instance = ConnectorAgent()
    return _instance
