from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryRecord(BaseModel):
    event_type: str
    title: str
    description: str = ""
    decision: str = ""
    rationale: str = ""
    outcome: str = ""
    confidence: float = 1.0
    who: str = ""
    domain: str = "general"
    tags: list[str] = []


class OutcomeUpdate(BaseModel):
    outcome: str
    confidence: float


@router.post("/record")
def record(req: MemoryRecord):
    from knowledge.memory import get_institutional_memory
    return get_institutional_memory().record(**req.model_dump())


@router.get("/events")
def list_events(event_type: Optional[str] = None, domain: Optional[str] = None,
                limit: int = 50, offset: int = 0):
    from knowledge.memory import get_institutional_memory
    return {"events": get_institutional_memory().list(event_type, domain, limit, offset)}


@router.get("/events/{mem_id}")
def get_event(mem_id: str):
    from knowledge.memory import get_institutional_memory
    event = get_institutional_memory().get(mem_id)
    if not event:
        from fastapi import HTTPException
        raise HTTPException(404, "Not found")
    return event


@router.patch("/events/{mem_id}/outcome")
def update_outcome(mem_id: str, req: OutcomeUpdate):
    from knowledge.memory import get_institutional_memory
    return get_institutional_memory().update_outcome(mem_id, req.outcome, req.confidence)


@router.get("/search")
def search(q: str, limit: int = 20):
    from knowledge.memory import get_institutional_memory
    return {"results": get_institutional_memory().search_by_keyword(q, limit)}


@router.get("/stats")
def stats():
    from knowledge.memory import get_institutional_memory
    return get_institutional_memory().stats()
