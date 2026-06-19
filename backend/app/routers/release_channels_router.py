from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from release_channels.engine import get_release_channels

router = APIRouter(prefix="/api/release-channels", tags=["release_channels"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/")
async def list_channels():
    try: return get_release_channels().list_channels()
    except Exception as e: return _e(e)


@router.get("/assignments")
async def list_assignments():
    try: return get_release_channels().list_assignments()
    except Exception as e: return _e(e)


@router.post("/assign")
async def assign(request: Request):
    try:
        b = await request.json()
        return get_release_channels().set_channel(
            target_type=b.get("target_type", ""),
            target_id=b.get("target_id", ""),
            channel=b.get("channel", "stable"),
        )
    except Exception as e: return _e(e)


@router.get("/assigned")
async def assigned(target_type: str, target_id: str):
    try:
        return {"channel": get_release_channels().get_assigned_channel(
            target_type, target_id)}
    except Exception as e: return _e(e)


@router.post("/pin")
async def pin(request: Request):
    try:
        b = await request.json()
        return get_release_channels().pin_version(
            target_type=b.get("target_type", ""),
            target_id=b.get("target_id", ""),
            version=b.get("version", ""),
        )
    except Exception as e: return _e(e)


@router.get("/pin")
async def get_pin(target_type: str, target_id: str):
    try: return get_release_channels().get_pin(target_type, target_id)
    except Exception as e: return _e(e)


@router.post("/rollback")
async def rollback(request: Request):
    try:
        b = await request.json()
        return get_release_channels().rollback(
            target_type=b.get("target_type", ""),
            target_id=b.get("target_id", ""),
        )
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_release_channels().stats()
    except Exception as e: return _e(e)
