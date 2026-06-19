"""Alternative Data Platform API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/altdata", tags=["altdata"])


class AltIngest(BaseModel):
    dataset: str
    observations: list[dict]


@router.get("/datasets")
def datasets():
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().datasets()


@router.post("/ingest")
def ingest(body: AltIngest):
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().ingest(body.dataset, body.observations)


@router.get("/observations/{dataset}")
def observations(dataset: str, symbol: Optional[str] = None, limit: int = 100):
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().get_observations(dataset, symbol=symbol, limit=limit)


@router.get("/changes/{dataset}/{symbol}")
def changes(dataset: str, symbol: str, threshold: float = 0.2):
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().detect_changes(dataset, symbol.upper(), threshold)


@router.post("/signals/{dataset}")
def generate_signals(dataset: str):
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().generate_signals(dataset)


@router.get("/signals")
def list_signals(dataset: Optional[str] = None, limit: int = 50):
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().list_signals(dataset=dataset, limit=limit)


@router.get("/stats")
def stats():
    from altdata.platform import get_altdata_platform
    return get_altdata_platform().stats()
