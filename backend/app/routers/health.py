"""Health & service-info endpoints (used by the Electron supervisor)."""
from __future__ import annotations

from fastapi import APIRouter

from .. import config

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": config.SERVICE, "version": config.VERSION}


@router.get("/")
def root() -> dict:
    return {
        "service": config.SERVICE,
        "version": config.VERSION,
        "endpoints": {
            "quant": ["/quant/analyze", "/quant/factors", "/quant/risk", "/quant/portfolio"],
            "markets": ["/markets/quote/{symbol}", "/markets/history/{symbol}"],
            "accounting": ["/accounting/topics", "/accounting/asc/{topic}", "/accounting/memo"],
        },
    }
