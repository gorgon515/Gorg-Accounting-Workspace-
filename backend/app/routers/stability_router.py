from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from stability.engine import get_stability_engine

router = APIRouter(prefix="/api/stability", tags=["stability"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/crash")
async def record_crash(request: Request):
    try:
        b = await request.json()
        return get_stability_engine().record_crash(
            component=b.get("component", "unknown"),
            error=b.get("error", ""),
            severity=b.get("severity", "error"),
            context=b.get("context"),
        )
    except Exception as e: return _e(e)


@router.get("/crashes")
async def list_crashes(limit: int = 50):
    try: return get_stability_engine().list_crashes(limit=limit)
    except Exception as e: return _e(e)


@router.get("/crash-analysis")
async def crash_analysis():
    try: return get_stability_engine().crash_analysis()
    except Exception as e: return _e(e)


@router.get("/clusters")
async def cluster_failures(limit: int = 20):
    try: return get_stability_engine().cluster_failures(limit=limit)
    except Exception as e: return _e(e)


@router.post("/workflow")
async def record_workflow(request: Request):
    try:
        b = await request.json()
        return get_stability_engine().record_workflow(
            name=b.get("name", ""), duration_ms=b.get("duration_ms", 0.0),
            status=b.get("status", "ok"))
    except Exception as e: return _e(e)


@router.get("/slow-workflows")
async def slow_workflows(threshold_ms: float = 1000.0, limit: int = 20):
    try: return get_stability_engine().slow_workflows(threshold_ms=threshold_ms, limit=limit)
    except Exception as e: return _e(e)


@router.post("/task")
async def record_task(request: Request):
    try:
        b = await request.json()
        return get_stability_engine().record_task(
            name=b.get("name", ""), duration_ms=b.get("duration_ms", 0.0),
            status=b.get("status", "ok"))
    except Exception as e: return _e(e)


@router.get("/long-tasks")
async def long_running_tasks(threshold_ms: float = 5000.0, limit: int = 20):
    try: return get_stability_engine().long_running_tasks(threshold_ms=threshold_ms, limit=limit)
    except Exception as e: return _e(e)


@router.post("/memory-sample")
async def record_memory_sample(request: Request):
    try:
        b = await request.json()
        return get_stability_engine().record_memory_sample(rss_mb=b.get("rss_mb", 0.0))
    except Exception as e: return _e(e)


@router.get("/memory-leak")
async def detect_memory_leak():
    try: return get_stability_engine().detect_memory_leak()
    except Exception as e: return _e(e)


@router.post("/reliability")
async def score_reliability(request: Request):
    try:
        b = await request.json()
        return get_stability_engine().score_reliability(
            kind=b.get("kind", "agent"), name=b.get("name", ""),
            success=b.get("success", True), total_delta=b.get("total_delta", 1))
    except Exception as e: return _e(e)


@router.get("/reliability")
async def reliability_scores(kind: str = None):
    try: return get_stability_engine().reliability_scores(kind=kind)
    except Exception as e: return _e(e)


@router.get("/reliability/agents")
async def agent_reliability():
    try: return get_stability_engine().agent_reliability()
    except Exception as e: return _e(e)


@router.get("/reliability/connectors")
async def connector_reliability():
    try: return get_stability_engine().connector_reliability()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_stability_engine().stats()
    except Exception as e: return _e(e)
