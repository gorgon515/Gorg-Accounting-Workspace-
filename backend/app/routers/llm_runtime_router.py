from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from llm_runtime.engine import get_llm_runtime

router = APIRouter(prefix="/api/llm-runtime", tags=["llm_runtime"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/models")
async def list_models(local_only: bool = False, capability: str = ""):
    try: return get_llm_runtime().list_models(local_only=local_only, capability=capability)
    except Exception as e: return _e(e)


@router.post("/models")
async def register_model(request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().register_model(
            name=b.get("name", ""),
            provider=b.get("provider", "custom"),
            context_window=b.get("context_window", 4096),
            cost_per_1k=b.get("cost_per_1k", 0.0),
            capabilities=b.get("capabilities", ["chat"]),
            local=b.get("local", False),
            gpu_required=b.get("gpu_required", False),
        )
    except Exception as e: return _e(e)


@router.get("/models/{name}")
async def get_model(name: str):
    try:
        m = get_llm_runtime().get_model(name)
        return m or JSONResponse({"error": "Not found"}, status_code=404)
    except Exception as e: return _e(e)


@router.post("/route")
async def route_task(request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().route_task(
            task_type=b.get("task_type", "chat"),
            context_length=b.get("context_length", 0),
            requires_local=b.get("requires_local", False),
        )
    except Exception as e: return _e(e)


@router.post("/budget-context")
async def budget_context(request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().budget_context(
            messages=b.get("messages", []),
            max_tokens=b.get("max_tokens", 4000),
        )
    except Exception as e: return _e(e)


@router.post("/optimize-prompt")
async def optimize_prompt(request: Request):
    try:
        b = await request.json()
        result = get_llm_runtime().optimize_prompt(
            prompt=b.get("prompt", ""),
            task_type=b.get("task_type", "chat"),
        )
        return {"optimized_prompt": result}
    except Exception as e: return _e(e)


@router.post("/cache")
async def cache_response(request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().cache_response(
            prompt_hash=b.get("prompt_hash", ""),
            response=b.get("response", ""),
            model=b.get("model", ""),
            tokens=b.get("tokens", 0),
        )
    except Exception as e: return _e(e)


@router.post("/inference")
async def record_inference(request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().record_inference(
            model=b.get("model", ""),
            prompt_tokens=b.get("prompt_tokens", 0),
            completion_tokens=b.get("completion_tokens", 0),
            latency_ms=b.get("latency_ms", 0),
            task_type=b.get("task_type", "chat"),
        )
    except Exception as e: return _e(e)


@router.get("/metrics")
async def metrics(model: str = "", hours: float = 24.0):
    try: return get_llm_runtime().inference_metrics(model=model, hours=hours)
    except Exception as e: return _e(e)


@router.get("/gpu")
async def detect_gpu():
    try: return get_llm_runtime().detect_gpu()
    except Exception as e: return _e(e)


@router.post("/benchmark/{name}")
async def benchmark(name: str, request: Request):
    try:
        b = await request.json()
        return get_llm_runtime().benchmark_model(name, test_prompt=b.get("test_prompt", "Hello, HELIOS."))
    except Exception as e: return _e(e)


@router.get("/performance")
async def performance():
    try: return get_llm_runtime().performance_report()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_llm_runtime().stats()
    except Exception as e: return _e(e)
