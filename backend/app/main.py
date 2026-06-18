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


def main() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":  # pragma: no cover
    main()
