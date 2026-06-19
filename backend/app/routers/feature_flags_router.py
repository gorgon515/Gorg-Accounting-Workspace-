from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from feature_flags.engine import get_feature_flags

router = APIRouter(prefix="/api/feature-flags", tags=["feature_flags"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/")
async def create_flag(request: Request):
    try:
        b = await request.json()
        return get_feature_flags().create_flag(
            key=b.get("key", ""),
            name=b.get("name", ""),
            description=b.get("description", ""),
            enabled=b.get("enabled", False),
            rollout=b.get("rollout", "stable"),
            roles=b.get("roles"),
            workspaces=b.get("workspaces"),
        )
    except Exception as e: return _e(e)


@router.get("/")
async def list_flags():
    try: return get_feature_flags().list_flags()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_feature_flags().stats()
    except Exception as e: return _e(e)


@router.get("/{key}")
async def get_flag(key: str):
    try: return get_feature_flags().get_flag(key)
    except Exception as e: return _e(e)


@router.post("/{key}/enable")
async def enable(key: str):
    try: return get_feature_flags().enable(key)
    except Exception as e: return _e(e)


@router.post("/{key}/disable")
async def disable(key: str):
    try: return get_feature_flags().disable(key)
    except Exception as e: return _e(e)


@router.post("/{key}/rollout")
async def set_rollout(key: str, request: Request):
    try:
        b = await request.json()
        return get_feature_flags().set_rollout(key, b.get("channel", "stable"))
    except Exception as e: return _e(e)


@router.post("/{key}/roles")
async def set_roles(key: str, request: Request):
    try:
        b = await request.json()
        return get_feature_flags().set_roles(key, b.get("roles", []))
    except Exception as e: return _e(e)


@router.post("/{key}/workspaces")
async def set_workspaces(key: str, request: Request):
    try:
        b = await request.json()
        return get_feature_flags().set_workspaces(key, b.get("workspaces", []))
    except Exception as e: return _e(e)


@router.post("/{key}/kill")
async def kill(key: str):
    try: return get_feature_flags().kill(key)
    except Exception as e: return _e(e)


@router.post("/{key}/revive")
async def revive(key: str):
    try: return get_feature_flags().revive(key)
    except Exception as e: return _e(e)


@router.post("/{key}/evaluate")
async def evaluate(key: str, request: Request):
    try:
        b = await request.json()
        return {"enabled": get_feature_flags().is_enabled(
            key,
            role=b.get("role"),
            workspace=b.get("workspace"),
            channel=b.get("channel", "stable"),
        )}
    except Exception as e: return _e(e)


@router.get("/{key}/analytics")
async def analytics(key: str):
    try: return get_feature_flags().analytics(key)
    except Exception as e: return _e(e)
