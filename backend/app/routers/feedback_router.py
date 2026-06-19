from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from feedback.engine import get_feedback_engine

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/")
async def capture(request: Request):
    try:
        b = await request.json()
        return get_feedback_engine().capture(
            kind=b.get("kind", "action"),
            title=b.get("title", ""),
            detail=b.get("detail", ""),
            severity=b.get("severity", "medium"),
            impact=b.get("impact", ""),
            suggested_fix=b.get("suggested_fix", ""),
            context=b.get("context"),
        )
    except Exception as e: return _e(e)


@router.get("/")
async def list_feedback(kind: str = None, status: str = None,
                        severity: str = None, limit: int = 100):
    try:
        return get_feedback_engine().list(
            kind=kind, status=status, severity=severity, limit=limit
        )
    except Exception as e: return _e(e)


@router.get("/top/friction")
async def top_friction(limit: int = 10):
    try: return get_feedback_engine().top_friction(limit=limit)
    except Exception as e: return _e(e)


@router.get("/top/failures")
async def top_failures(limit: int = 10):
    try: return get_feedback_engine().top_failures(limit=limit)
    except Exception as e: return _e(e)


@router.get("/summary")
async def summary():
    try: return get_feedback_engine().summary()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_feedback_engine().stats()
    except Exception as e: return _e(e)


@router.get("/{fid}")
async def get_feedback(fid: str):
    try: return get_feedback_engine().get(fid)
    except Exception as e: return _e(e)


@router.post("/{fid}/status")
async def update_status(fid: str, request: Request):
    try:
        b = await request.json()
        return get_feedback_engine().update_status(fid, b.get("status", "open"))
    except Exception as e: return _e(e)


@router.post("/{fid}/resolve")
async def resolve(fid: str, request: Request):
    try:
        try: b = await request.json()
        except Exception: b = {}
        return get_feedback_engine().resolve(fid, suggested_fix=b.get("suggested_fix"))
    except Exception as e: return _e(e)
