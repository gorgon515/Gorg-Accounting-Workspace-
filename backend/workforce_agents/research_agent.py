"""
Research Agent: executes research missions, synthesizes findings, generates reports.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class ResearchAgent(BaseAgent):
    agent_id = "agent_research"
    agent_name = "Research Agent"
    domain = "general"
    description = "Executes research missions, synthesizes intelligence, produces structured reports"
    allowed_action_types = ["advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []
        mission_id = inputs.get("mission_id")

        if mission_id:
            try:
                from research.missions import get_research_missions
                rm = get_research_missions()
                result = rm.run_mission(mission_id)
                findings.append({
                    "type": "mission_run",
                    "mission_id": mission_id,
                    "report_id": result.get("report_id"),
                    "items_collected": result.get("items_collected", 0),
                    "findings": result.get("findings", []),
                })
                if result.get("items_collected", 0) > 0:
                    proposed_actions.append({
                        "type": "advisory",
                        "title": f"Research Report Ready: Mission {mission_id[:8]}",
                        "description": f"Mission produced {result.get('items_collected')} intelligence items. Report available for review.",
                        "payload": {"report_id": result.get("report_id")},
                        "requires_approval": False,
                    })
            except Exception as e:
                findings.append({"type": "error", "source": "research_mission", "error": str(e)})
        else:
            try:
                from research.missions import get_research_missions
                rm = get_research_missions()
                missions = rm.list_missions()
                for mission in missions[:5]:
                    findings.append({
                        "type": "mission_status",
                        "id": mission.get("id"),
                        "name": mission.get("name"),
                        "team": mission.get("team"),
                        "run_count": mission.get("run_count", 0),
                        "next_run": mission.get("next_run"),
                    })
            except Exception as e:
                findings.append({"type": "error", "source": "missions_list", "error": str(e)})

        try:
            from synthesis.engine import get_synthesis_engine
            topic = inputs.get("topic", "")
            if topic:
                domain = inputs.get("domain", "general")
                synth = get_synthesis_engine().synthesize(topic, n_sources=8, domain=domain)
                findings.append({
                    "type": "synthesis",
                    "topic": topic,
                    "summary": synth.get("summary", "")[:500],
                    "source_count": synth.get("source_count", 0),
                    "confidence": synth.get("confidence", 0.5),
                })
        except Exception as e:
            findings.append({"type": "error", "source": "synthesis", "error": str(e)})

        self.remember("last_run_findings", len(findings))
        summary = f"Research agent completed run with {len(findings)} finding(s)."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_research_agent() -> ResearchAgent:
    global _instance
    if _instance is None:
        _instance = ResearchAgent()
    return _instance
