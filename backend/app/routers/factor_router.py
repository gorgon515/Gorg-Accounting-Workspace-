"""Factor Research Framework API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/factors", tags=["factors"])


class FactorRank(BaseModel):
    symbols: list[str]
    factor: str = "value"


class FactorCombine(BaseModel):
    symbols: list[str]
    weights: dict


class CustomFactor(BaseModel):
    name: str
    description: str = ""
    definition: dict = {}


class Snapshot(BaseModel):
    symbols: list[str]


@router.get("/library")
def library():
    from quant_lab.factors import get_factor_library
    return get_factor_library().library()


@router.get("/score/{symbol}")
def score(symbol: str):
    from quant_lab.factors import get_factor_library
    return get_factor_library().score_symbol(symbol.upper())


@router.post("/rank")
def rank(body: FactorRank):
    from quant_lab.factors import get_factor_library
    return get_factor_library().rank([s.upper() for s in body.symbols], body.factor)


@router.post("/combine")
def combine(body: FactorCombine):
    from quant_lab.factors import get_factor_library
    return get_factor_library().combine([s.upper() for s in body.symbols], body.weights)


@router.get("/persistence/{symbol}/{factor}")
def persistence(symbol: str, factor: str):
    from quant_lab.factors import get_factor_library
    return get_factor_library().persistence(symbol.upper(), factor)


@router.post("/snapshot")
def snapshot(body: Snapshot):
    from quant_lab.factors import get_factor_library
    n = get_factor_library().snapshot([s.upper() for s in body.symbols])
    return {"recorded": n}


@router.get("/custom")
def list_custom():
    from quant_lab.factors import get_factor_library
    return get_factor_library().list_custom()


@router.post("/custom")
def create_custom(body: CustomFactor):
    from quant_lab.factors import get_factor_library
    return get_factor_library().create_custom(body.name, body.description, body.definition)


@router.get("/stats")
def stats():
    from quant_lab.factors import get_factor_library
    return get_factor_library().stats()
