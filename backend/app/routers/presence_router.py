from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from presence.engine import get_presence_engine

router = APIRouter(prefix="/api/presence", tags=["presence"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/state")
async def get_state():
    try: return get_presence_engine().get_state()
    except Exception as e: return _e(e)


@router.post("/mode")
async def set_mode(request: Request):
    try:
        b = await request.json()
        return get_presence_engine().set_mode(
            mode=b.get("mode", "work"),
            context=b.get("context", {}),
        )
    except Exception as e: return _e(e)


@router.get("/mode")
async def get_mode():
    try: return get_presence_engine().get_mode()
    except Exception as e: return _e(e)


@router.post("/context")
async def update_context(request: Request):
    try:
        b = await request.json()
        return get_presence_engine().update_context(
            app=b.get("app", ""),
            task=b.get("task", ""),
            url=b.get("url", ""),
            document=b.get("document", ""),
        )
    except Exception as e: return _e(e)


@router.get("/context")
async def get_context():
    try: return get_presence_engine().get_context()
    except Exception as e: return _e(e)


@router.post("/calendar")
async def set_calendar(request: Request):
    try:
        b = await request.json()
        return get_presence_engine().set_calendar_status(
            status=b.get("status", "free"),
            meeting_title=b.get("meeting_title", ""),
            ends_at=b.get("ends_at"),
        )
    except Exception as e: return _e(e)


@router.get("/calendar")
async def get_calendar():
    try: return get_presence_engine().get_calendar_status()
    except Exception as e: return _e(e)


@router.post("/focus")
async def set_focus(request: Request):
    try:
        b = await request.json()
        return get_presence_engine().set_focus(
            enabled=b.get("enabled", True),
            duration_min=b.get("duration_min", 60),
            goal=b.get("goal", ""),
        )
    except Exception as e: return _e(e)


@router.get("/focus")
async def get_focus():
    try: return get_presence_engine().get_focus()
    except Exception as e: return _e(e)


@router.get("/history")
async def history(limit: int = 20):
    try: return get_presence_engine().mode_history(limit=limit)
    except Exception as e: return _e(e)


@router.get("/adaptive")
async def adaptive():
    try: return get_presence_engine().adaptive_config()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_presence_engine().stats()
    except Exception as e: return _e(e)
