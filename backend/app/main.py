"""HELIOS Intelligence Sidecar — FastAPI app.

The compute tier of HELIOS: the Quant Research Engine and Accounting Intelligence
Engine, served on localhost for the Electron app to call. Bound to 127.0.0.1 and
unreachable off-box; the service layer it wraps is pure-Python and unit-tested.

Run:  uvicorn app.main:app --host 127.0.0.1 --port 8420
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .routers import (
    accounting, accounting_intel, accounting_platform_router, execution_router, health, markets,
    n8n_router, personal, quant, quant_research, workbench,
    security_router, backup_router, sync_router, health_router,
    workspaces_router, licensing_router, monitoring_router, updates_router,
    plugins_router, public_api_router, webhooks_router,
    reasoning_router, intelligence_router, forecasting_router, advisory_router, executive_router,
    knowledge_router, memory_router, rag_router, synthesis_router, self_improvement_router,
)
from .services.market_data import DataUnavailable

app = FastAPI(
    title="HELIOS Intelligence Sidecar",
    version=config.VERSION,
    description="Quant Research + Accounting Intelligence compute tier for HELIOS.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(app://\.|http://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _value_error(_req: Request, exc: ValueError) -> JSONResponse:
    # Bad/insufficient input → 400 with the underlying message.
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(DataUnavailable)
async def _data_unavailable(_req: Request, exc: DataUnavailable) -> JSONResponse:
    # Provider/network problem → 503 so the caller can degrade gracefully.
    return JSONResponse(status_code=503, content={"error": str(exc)})


app.include_router(health.router)
app.include_router(quant.router)
app.include_router(quant_research.router)
app.include_router(markets.router)
app.include_router(accounting.router)
app.include_router(accounting_intel.router)
app.include_router(n8n_router.router)
app.include_router(personal.router)
app.include_router(accounting_platform_router.router)
app.include_router(workbench.router)
app.include_router(execution_router.router)
# Phase 9 — security, backup, sync, health
app.include_router(security_router.router)
app.include_router(backup_router.router)
app.include_router(sync_router.router)
app.include_router(health_router.router)
# Phase 10 — productization, deployment & commercial readiness
app.include_router(workspaces_router.router)
app.include_router(licensing_router.router)
app.include_router(monitoring_router.router)
app.include_router(updates_router.router)
app.include_router(plugins_router.router)
app.include_router(public_api_router.router)
app.include_router(webhooks_router.router)
# Phase 11 — autonomous intelligence & strategic reasoning
app.include_router(reasoning_router.router)
app.include_router(intelligence_router.router)
app.include_router(forecasting_router.router)
app.include_router(advisory_router.router)
app.include_router(executive_router.router)
# Phase 12 — knowledge engine, RAG, institutional memory & self-improving intelligence
app.include_router(knowledge_router.router)
app.include_router(memory_router.router)
app.include_router(rag_router.router)
app.include_router(synthesis_router.router)
app.include_router(self_improvement_router.router)


def main() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":  # pragma: no cover
    main()
