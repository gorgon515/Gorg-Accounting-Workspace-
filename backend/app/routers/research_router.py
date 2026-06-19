"""Research Missions API — Phase 13."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/research", tags=["research"])


class MissionCreate(BaseModel):
    name: str
    description: str = ""
    team: str = "market"
    topics: list[str] = []
    domain: str = ""
    connectors: list[str] = []
    schedule: str = "daily"


@router.get("/missions")
def list_missions(status: str = "active", team: Optional[str] = None):
    from research.missions import get_research_missions
    return get_research_missions().list_missions(status=status, team=team)


@router.post("/missions")
def create_mission(body: MissionCreate):
    from research.missions import get_research_missions
    return get_research_missions().create_mission(
        name=body.name, description=body.description, team=body.team,
        topics=body.topics, domain=body.domain, connectors=body.connectors,
        schedule=body.schedule,
    )


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str):
    from research.missions import get_research_missions
    mission = get_research_missions().get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("/missions/{mission_id}/run")
def run_mission(mission_id: str):
    from research.missions import get_research_missions
    return get_research_missions().run_mission(mission_id)


@router.post("/missions/{mission_id}/pause")
def pause_mission(mission_id: str):
    from research.missions import get_research_missions
    return get_research_missions().pause_mission(mission_id)


@router.get("/reports")
def list_reports(mission_id: Optional[str] = None, team: Optional[str] = None, limit: int = 20):
    from research.missions import get_research_missions
    return get_research_missions().list_reports(mission_id=mission_id, team=team, limit=limit)


@router.get("/teams")
def list_teams():
    from research.missions import get_research_missions
    return get_research_missions().teams()


@router.get("/stats")
def research_stats():
    from research.missions import get_research_missions
    return get_research_missions().stats()
