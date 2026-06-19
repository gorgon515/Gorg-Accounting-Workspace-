from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ops_dashboard.engine import get_ops_dashboard_engine

router = APIRouter(prefix="/api/ops-dashboard", tags=["ops_dashboard"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/overview")
async def overview():
    try: return get_ops_dashboard_engine().overview()
    except Exception as e: return _e(e)


@router.get("/system-health")
async def system_health():
    try: return get_ops_dashboard_engine().system_health()
    except Exception as e: return _e(e)


@router.get("/agent-health")
async def agent_health():
    try: return get_ops_dashboard_engine().agent_health()
    except Exception as e: return _e(e)


@router.get("/connector-health")
async def connector_health():
    try: return get_ops_dashboard_engine().connector_health()
    except Exception as e: return _e(e)


@router.get("/voice-health")
async def voice_health():
    try: return get_ops_dashboard_engine().voice_health()
    except Exception as e: return _e(e)


@router.get("/storage")
async def storage_usage():
    try: return get_ops_dashboard_engine().storage_usage()
    except Exception as e: return _e(e)


@router.get("/memory-growth")
async def memory_growth():
    try: return get_ops_dashboard_engine().memory_growth()
    except Exception as e: return _e(e)


@router.get("/knowledge-growth")
async def knowledge_growth():
    try: return get_ops_dashboard_engine().knowledge_growth()
    except Exception as e: return _e(e)


@router.get("/most-used")
async def most_used_features(limit: int = 10):
    try: return get_ops_dashboard_engine().most_used_features(limit=limit)
    except Exception as e: return _e(e)


@router.get("/recent-failures")
async def recent_failures(limit: int = 10):
    try: return get_ops_dashboard_engine().recent_failures(limit=limit)
    except Exception as e: return _e(e)


@router.get("/pending-approvals")
async def pending_approvals():
    try: return get_ops_dashboard_engine().pending_approvals()
    except Exception as e: return _e(e)


@router.post("/snapshot")
async def snapshot():
    try: return get_ops_dashboard_engine().snapshot()
    except Exception as e: return _e(e)


@router.get("/snapshots")
async def snapshot_history(limit: int = 20):
    try: return get_ops_dashboard_engine().snapshot_history(limit=limit)
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_ops_dashboard_engine().stats()
    except Exception as e: return _e(e)
