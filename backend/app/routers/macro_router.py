"""Macro Intelligence Platform API — Phase 14."""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/indicators")
def indicators():
    from macro.engine import get_macro_engine
    return get_macro_engine().indicators()


@router.get("/yield-curve")
def yield_curve():
    from macro.engine import get_macro_engine
    return get_macro_engine().yield_curve()


@router.post("/regime")
def classify_regime():
    from macro.engine import get_macro_engine
    return get_macro_engine().classify_regime()


@router.get("/regime/history")
def regime_history(limit: int = 20):
    from macro.engine import get_macro_engine
    return get_macro_engine().regime_history(limit=limit)


@router.get("/stats")
def stats():
    from macro.engine import get_macro_engine
    return get_macro_engine().stats()
