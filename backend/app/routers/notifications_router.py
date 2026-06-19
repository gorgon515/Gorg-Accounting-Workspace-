from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from notifications.engine import get_notification_engine

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/send")
async def send(request: Request):
    try:
        b = await request.json()
        return get_notification_engine().send(
            title=b.get("title", ""),
            body=b.get("body", ""),
            priority=b.get("priority", "medium"),
            category=b.get("category", "general"),
            channel=b.get("channel", "desktop"),
            source=b.get("source", ""),
            action_url=b.get("action_url", ""),
            metadata=b.get("metadata", {}),
        )
    except Exception as e: return _e(e)


@router.get("/")
async def list_notifications(status: str = "unread", priority: str = "",
                              limit: int = 50):
    try:
        return get_notification_engine().list(
            status=status or None, priority=priority or None, limit=limit
        )
    except Exception as e: return _e(e)


@router.post("/{nid}/read")
async def mark_read(nid: str):
    try: return {"success": get_notification_engine().mark_read(nid)}
    except Exception as e: return _e(e)


@router.post("/read-all")
async def read_all():
    try: return {"marked": get_notification_engine().mark_all_read()}
    except Exception as e: return _e(e)


@router.post("/{nid}/dismiss")
async def dismiss(nid: str):
    try: return {"success": get_notification_engine().dismiss(nid)}
    except Exception as e: return _e(e)


@router.post("/{nid}/escalate")
async def escalate(nid: str, request: Request):
    try:
        b = await request.json()
        return get_notification_engine().escalate(nid, new_priority=b.get("priority", "high"))
    except Exception as e: return _e(e)


@router.get("/quiet-hours")
async def get_quiet_hours():
    try: return get_notification_engine().get_quiet_hours()
    except Exception as e: return _e(e)


@router.post("/quiet-hours")
async def set_quiet_hours(request: Request):
    try:
        b = await request.json()
        return get_notification_engine().set_quiet_hours(
            start_hour=b.get("start_hour", 22),
            end_hour=b.get("end_hour", 7),
            enabled=b.get("enabled", True),
        )
    except Exception as e: return _e(e)


@router.get("/focus-mode")
async def get_focus():
    try: return get_notification_engine().get_focus_mode()
    except Exception as e: return _e(e)


@router.post("/focus-mode")
async def set_focus(request: Request):
    try:
        b = await request.json()
        return get_notification_engine().set_focus_mode(
            enabled=b.get("enabled", True),
            duration_minutes=b.get("duration_minutes", 60),
        )
    except Exception as e: return _e(e)


@router.get("/batch")
async def batch():
    try: return get_notification_engine().batch_pending()
    except Exception as e: return _e(e)


@router.get("/channels")
async def channels():
    try: return get_notification_engine().channels()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_notification_engine().stats()
    except Exception as e: return _e(e)
