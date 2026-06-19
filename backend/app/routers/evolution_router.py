from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from evolution.engine import get_evolution_engine

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/")
async def add_item(request: Request):
    try:
        b = await request.json()
        return get_evolution_engine().add_item(
            problem=b.get("problem", ""),
            impact=b.get("impact", ""),
            frequency=b.get("frequency", 1),
            suggested_solution=b.get("suggested_solution", ""),
            priority=b.get("priority", "medium"),
            owner=b.get("owner", ""),
            source=b.get("source", "manual"),
            tags=b.get("tags"),
        )
    except Exception as e: return _e(e)


@router.get("/")
async def list_items(status: str = None, priority: str = None, limit: int = 200):
    try: return get_evolution_engine().list_items(status=status, priority=priority, limit=limit)
    except Exception as e: return _e(e)


@router.get("/prioritized")
async def prioritized(limit: int = 50):
    try: return get_evolution_engine().prioritized(limit=limit)
    except Exception as e: return _e(e)


@router.get("/roadmap")
async def roadmap():
    try: return get_evolution_engine().roadmap()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_evolution_engine().stats()
    except Exception as e: return _e(e)


@router.get("/{item_id}")
async def get_item(item_id: str):
    try:
        item = get_evolution_engine().get_item(item_id)
        if item is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return item
    except Exception as e: return _e(e)


@router.post("/{item_id}")
async def update_item(item_id: str, request: Request):
    try:
        b = await request.json()
        return get_evolution_engine().update_item(item_id, **b)
    except Exception as e: return _e(e)


@router.post("/{item_id}/status")
async def set_status(item_id: str, request: Request):
    try:
        b = await request.json()
        return get_evolution_engine().set_status(item_id, b.get("status", "backlog"))
    except Exception as e: return _e(e)


@router.post("/{item_id}/assign")
async def assign(item_id: str, request: Request):
    try:
        b = await request.json()
        return get_evolution_engine().assign(item_id, b.get("owner", ""))
    except Exception as e: return _e(e)


@router.post("/{item_id}/bump")
async def bump(item_id: str, request: Request):
    try:
        try:
            b = await request.json()
        except Exception:
            b = {}
        return get_evolution_engine().bump_frequency(item_id, by=b.get("by", 1))
    except Exception as e: return _e(e)
