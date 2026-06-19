from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class IngestRequest(BaseModel):
    title: str
    content: str
    domain: str = "general"
    kind: str = "document"
    source: str = ""
    author: str = ""
    confidence: float = 1.0
    authority: float = 0.5
    tags: list[str] = []
    citations: list[str] = []
    parent_id: Optional[str] = None


class LinkRequest(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0


class GapRequest(BaseModel):
    domain: str
    description: str
    priority: float = 0.5


class ConflictResolution(BaseModel):
    resolution: str


@router.post("/ingest")
def ingest(req: IngestRequest):
    from knowledge.engine import get_knowledge_engine
    return get_knowledge_engine().ingest(**req.model_dump())


@router.get("/items")
def list_items(domain: Optional[str] = None, kind: Optional[str] = None,
               status: str = "active", limit: int = 50, offset: int = 0):
    from knowledge.engine import get_knowledge_engine
    return {"items": get_knowledge_engine().list(domain, kind, status, limit, offset)}


@router.get("/items/{item_id}")
def get_item(item_id: str):
    from knowledge.engine import get_knowledge_engine
    item = get_knowledge_engine().get(item_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(404, "Not found")
    return item


@router.patch("/items/{item_id}")
def update_item(item_id: str, fields: dict):
    from knowledge.engine import get_knowledge_engine
    return get_knowledge_engine().update(item_id, **fields)


@router.post("/link")
def link(req: LinkRequest):
    from knowledge.engine import get_knowledge_engine
    get_knowledge_engine().link(req.source_id, req.target_id, req.relation, req.weight)
    return {"linked": True}


@router.get("/links/{item_id}")
def links(item_id: str):
    from knowledge.engine import get_knowledge_engine
    return {"links": get_knowledge_engine().links(item_id)}


@router.get("/conflicts")
def conflicts(resolved: bool = False):
    from knowledge.engine import get_knowledge_engine
    return {"conflicts": get_knowledge_engine().conflicts(resolved)}


@router.post("/conflicts/{conflict_id}/resolve")
def resolve(conflict_id: int, req: ConflictResolution):
    from knowledge.engine import get_knowledge_engine
    get_knowledge_engine().resolve_conflict(conflict_id, req.resolution)
    return {"resolved": True}


@router.get("/gaps")
def gaps(status: str = "open"):
    from knowledge.engine import get_knowledge_engine
    return {"gaps": get_knowledge_engine().gaps(status)}


@router.post("/gaps")
def add_gap(req: GapRequest):
    from knowledge.engine import get_knowledge_engine
    return get_knowledge_engine().add_gap(req.domain, req.description, req.priority)


@router.get("/health")
def health():
    from knowledge.engine import get_knowledge_engine
    return get_knowledge_engine().health()


@router.get("/stats")
def stats():
    from knowledge.engine import get_knowledge_engine
    return get_knowledge_engine().stats()
