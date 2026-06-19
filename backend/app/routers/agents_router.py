"""Workforce Agents API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENT_MAP = {
    "market": ("workforce_agents.market_agent", "get_market_agent"),
    "economic": ("workforce_agents.economic_agent", "get_economic_agent"),
    "regulatory": ("workforce_agents.regulatory_agent", "get_regulatory_agent"),
    "research": ("workforce_agents.research_agent", "get_research_agent"),
    "connector": ("workforce_agents.connector_agent", "get_connector_agent"),
    "event": ("workforce_agents.event_agent", "get_event_agent"),
}


def _get_agent(agent_id: str):
    entry = AGENT_MAP.get(agent_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    module_path, fn_name = entry
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, fn_name)()


class AgentRunRequest(BaseModel):
    trigger: str = "manual"
    inputs: dict = {}


class ActionResolution(BaseModel):
    approved_by: str = "user"


@router.get("")
def list_agents():
    return [
        {"id": aid, "module": entry[0], "getter": entry[1]}
        for aid, entry in AGENT_MAP.items()
    ]


@router.post("/{agent_id}/run")
def run_agent(agent_id: str, body: AgentRunRequest):
    agent = _get_agent(agent_id)
    result = agent.run(trigger=body.trigger, inputs=body.inputs)
    return result.to_dict()


@router.get("/{agent_id}/runs")
def agent_runs(agent_id: str, limit: int = 20):
    agent = _get_agent(agent_id)
    return agent.list_runs(limit=limit)


@router.get("/{agent_id}/actions")
def agent_pending_actions(agent_id: str, status: str = "pending"):
    agent = _get_agent(agent_id)
    return agent.list_proposed_actions(status=status)


@router.get("/approvals/pending")
def list_pending_approvals(limit: int = 50):
    from workforce_agents.base import list_pending_approvals
    return list_pending_approvals(limit=limit)


@router.post("/actions/{action_id}/approve")
def approve_action(action_id: str, body: ActionResolution):
    from workforce_agents.base import approve_action
    result = approve_action(action_id, approved_by=body.approved_by)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found")
    return result


@router.post("/actions/{action_id}/reject")
def reject_action(action_id: str):
    from workforce_agents.base import reject_action
    result = reject_action(action_id)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found")
    return result


@router.get("/stats/all")
def all_agent_stats():
    from workforce_agents.base import agent_stats
    return agent_stats()
