from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from plugin_upgrades.engine import get_plugin_upgrade_engine

router = APIRouter(prefix="/api/plugin-upgrades", tags=["plugin-upgrades"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/register")
async def register_plugin(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().register_plugin(
            plugin_id=b.get("plugin_id", ""),
            version=b.get("version", ""),
            dependencies=b.get("dependencies"),
            min_helios=b.get("min_helios", "0.0.0"),
        )
    except Exception as e: return _e(e)


@router.get("/versions")
async def versions(plugin_id: str = None):
    try: return get_plugin_upgrade_engine().list_versions(plugin_id=plugin_id)
    except Exception as e: return _e(e)


@router.get("/installed")
async def installed(plugin_id: str):
    try: return get_plugin_upgrade_engine().installed_version(plugin_id)
    except Exception as e: return _e(e)


@router.post("/compatibility")
async def compatibility(request: Request):
    try:
        b = await request.json()
        eng = get_plugin_upgrade_engine()
        helios_version = b.get("helios_version")
        if helios_version:
            return eng.check_compatibility(
                b.get("plugin_id", ""), b.get("version", ""), helios_version
            )
        return eng.check_compatibility(b.get("plugin_id", ""), b.get("version", ""))
    except Exception as e: return _e(e)


@router.post("/resolve")
async def resolve(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().resolve_dependencies(
            b.get("plugin_id", ""), b.get("version", "")
        )
    except Exception as e: return _e(e)


@router.post("/plan")
async def plan(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().plan_upgrade(
            b.get("plugin_id", ""), b.get("target_version", "")
        )
    except Exception as e: return _e(e)


@router.post("/sandbox-verify")
async def sandbox_verify(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().verify_in_sandbox(
            b.get("plugin_id", ""), b.get("version", "")
        )
    except Exception as e: return _e(e)


@router.post("/apply")
async def apply(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().apply_upgrade(
            b.get("plugin_id", ""),
            b.get("target_version", ""),
            require_sandbox=b.get("require_sandbox", True),
        )
    except Exception as e: return _e(e)


@router.post("/rollback")
async def rollback(request: Request):
    try:
        b = await request.json()
        return get_plugin_upgrade_engine().rollback_upgrade(
            b.get("plugin_id", ""), b.get("to_version", "")
        )
    except Exception as e: return _e(e)


@router.get("/history")
async def history(plugin_id: str = None, limit: int = 50):
    try:
        return get_plugin_upgrade_engine().upgrade_history(
            plugin_id=plugin_id, limit=limit
        )
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_plugin_upgrade_engine().stats()
    except Exception as e: return _e(e)
