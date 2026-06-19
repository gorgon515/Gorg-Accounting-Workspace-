from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from runtime.engine import get_runtime_engine

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/mode")
async def get_mode():
    try: return get_runtime_engine().get_mode()
    except Exception as e: return _e(e)


@router.post("/mode")
async def set_mode(request: Request):
    try:
        b = await request.json()
        return get_runtime_engine().set_mode(mode=b.get("mode", "production"))
    except Exception as e: return _e(e)


@router.get("/experimental")
async def experimental():
    try: return {"experimental_enabled": get_runtime_engine().is_experimental_enabled()}
    except Exception as e: return _e(e)


@router.get("/diagnostics")
async def diagnostics():
    try: return get_runtime_engine().run_startup_diagnostics()
    except Exception as e: return _e(e)


@router.get("/dependency-check")
async def dependency_check():
    try: return get_runtime_engine().dependency_check()
    except Exception as e: return _e(e)


@router.get("/db-integrity")
async def db_integrity():
    try: return get_runtime_engine().db_integrity_check()
    except Exception as e: return _e(e)


@router.get("/health-validation")
async def health_validation():
    try: return get_runtime_engine().health_validation()
    except Exception as e: return _e(e)


@router.post("/safe-startup")
async def safe_startup():
    try: return get_runtime_engine().safe_startup()
    except Exception as e: return _e(e)


@router.post("/daily-driver")
async def daily_driver():
    try: return get_runtime_engine().daily_driver_startup()
    except Exception as e: return _e(e)


@router.post("/crash")
async def record_crash(request: Request):
    try:
        b = await request.json()
        return get_runtime_engine().record_crash(
            component=b.get("component", ""),
            error=b.get("error", ""),
            severity=b.get("severity", "error"),
        )
    except Exception as e: return _e(e)


@router.post("/crash/{crash_id}/recover")
async def recover_crash(crash_id: str):
    try: return get_runtime_engine().attempt_recovery(crash_id)
    except Exception as e: return _e(e)


@router.get("/crashes")
async def crashes(limit: int = 50):
    try: return get_runtime_engine().list_crashes(limit=limit)
    except Exception as e: return _e(e)


@router.get("/mode/history")
async def mode_history(limit: int = 20):
    try: return get_runtime_engine().mode_history(limit=limit)
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_runtime_engine().stats()
    except Exception as e: return _e(e)
