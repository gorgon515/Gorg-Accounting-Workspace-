from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ambient.engine import get_ambient_engine

router = APIRouter(prefix="/api/ambient", tags=["ambient"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/briefing")
async def generate_briefing(request: Request):
    try:
        b = await request.json()
        return get_ambient_engine().generate_briefing(include_sections=b.get("sections"))
    except Exception as e: return _e(e)


@router.get("/briefing")
async def latest_briefing():
    try:
        b = get_ambient_engine().get_latest_briefing()
        return b or {"message": "No briefing generated yet"}
    except Exception as e: return _e(e)


@router.get("/briefing/history")
async def briefing_history(limit: int = 10):
    try: return get_ambient_engine().briefing_history(limit=limit)
    except Exception as e: return _e(e)


@router.post("/reminders")
async def add_reminder(request: Request):
    try:
        b = await request.json()
        return get_ambient_engine().add_reminder(
            title=b.get("title", ""),
            body=b.get("body", ""),
            remind_at=b.get("remind_at", 0),
            category=b.get("category", "general"),
            repeat=b.get("repeat", "none"),
        )
    except Exception as e: return _e(e)


@router.get("/reminders")
async def list_reminders(active_only: bool = True):
    try: return get_ambient_engine().list_reminders(active_only=active_only)
    except Exception as e: return _e(e)


@router.post("/reminders/{rid}/dismiss")
async def dismiss_reminder(rid: str):
    try: return {"success": get_ambient_engine().dismiss_reminder(rid)}
    except Exception as e: return _e(e)


@router.get("/triggers")
async def check_triggers():
    try: return get_ambient_engine().check_triggers()
    except Exception as e: return _e(e)


@router.post("/alerts")
async def record_alert(request: Request):
    try:
        b = await request.json()
        return get_ambient_engine().record_alert(
            alert_type=b.get("alert_type", "info"),
            title=b.get("title", ""),
            body=b.get("body", ""),
            source=b.get("source", ""),
            severity=b.get("severity", "info"),
        )
    except Exception as e: return _e(e)


@router.get("/alerts")
async def list_alerts(limit: int = 50):
    try: return get_ambient_engine().list_alerts(limit=limit)
    except Exception as e: return _e(e)


@router.post("/alerts/{aid}/acknowledge")
async def acknowledge_alert(aid: str):
    try: return {"success": get_ambient_engine().acknowledge_alert(aid)}
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_ambient_engine().stats()
    except Exception as e: return _e(e)
