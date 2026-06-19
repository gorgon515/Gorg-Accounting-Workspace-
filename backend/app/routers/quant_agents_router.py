"""Phase 14 investment agents API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/quant-agents", tags=["quant-agents"])


class AgentRun(BaseModel):
    trigger: str = "manual"
    inputs: dict = {}


@router.get("")
def list_agents():
    from quant_agents.agents import list_quant_agents
    return list_quant_agents()


@router.post("/{agent_key}/run")
def run_agent(agent_key: str, body: AgentRun):
    from quant_agents.agents import get_quant_agent
    try:
        agent = get_quant_agent(agent_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return agent.run(trigger=body.trigger, inputs=body.inputs).to_dict()


@router.get("/{agent_key}/runs")
def agent_runs(agent_key: str, limit: int = 20):
    from quant_agents.agents import get_quant_agent
    try:
        agent = get_quant_agent(agent_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return agent.list_runs(limit=limit)


@router.get("/{agent_key}/actions")
def agent_actions(agent_key: str, status: str = "pending"):
    from quant_agents.agents import get_quant_agent
    try:
        agent = get_quant_agent(agent_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return agent.list_proposed_actions(status=status)
