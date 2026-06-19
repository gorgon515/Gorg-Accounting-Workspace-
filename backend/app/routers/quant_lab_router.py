"""Quant Research Lab API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/quant-lab", tags=["quant-lab"])


class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "signal"
    definition: dict = {}
    tags: list[str] = []


class StrategyUpdate(BaseModel):
    definition: dict
    note: str = ""


class HypothesisCreate(BaseModel):
    statement: str
    rationale: str = ""


class ExperimentRun(BaseModel):
    name: str
    symbol: str
    definition: dict
    strategy_id: str = ""
    hypothesis_id: str = ""
    commission_bps: float = 1.0
    slippage_bps: float = 5.0


class NotebookCreate(BaseModel):
    title: str
    content: str = ""
    strategy_id: str = ""
    cells: list = []


@router.get("/strategies")
def list_strategies(status: Optional[str] = None, category: Optional[str] = None):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().list_strategies(status=status, category=category)


@router.post("/strategies")
def create_strategy(body: StrategyCreate):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().create_strategy(body.name, body.description, body.category,
                                           body.definition, body.tags)


@router.get("/strategies/{sid}")
def get_strategy(sid: str):
    from quant_lab.lab import get_quant_lab
    s = get_quant_lab().get_strategy(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.put("/strategies/{sid}")
def update_strategy(sid: str, body: StrategyUpdate):
    from quant_lab.lab import get_quant_lab
    s = get_quant_lab().update_strategy(sid, body.definition, body.note)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.get("/strategies/{sid}/versions")
def strategy_versions(sid: str):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().strategy_versions(sid)


@router.post("/strategies/{sid}/status")
def set_status(sid: str, status: str):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().set_strategy_status(sid, status)


@router.post("/signals")
def generate_signal(symbol: str, body: dict):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().generate_signal(symbol, body)


@router.post("/experiments")
def run_experiment(body: ExperimentRun):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().run_experiment(
        body.name, body.symbol, body.definition, body.strategy_id,
        body.hypothesis_id, body.commission_bps, body.slippage_bps)


@router.get("/experiments")
def list_experiments(strategy_id: Optional[str] = None, limit: int = 50):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().list_experiments(strategy_id=strategy_id, limit=limit)


@router.get("/hypotheses")
def list_hypotheses(status: Optional[str] = None):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().list_hypotheses(status=status)


@router.post("/hypotheses")
def create_hypothesis(body: HypothesisCreate):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().create_hypothesis(body.statement, body.rationale)


@router.post("/hypotheses/{hid}/resolve")
def resolve_hypothesis(hid: str, conclusion: str, status: str = "confirmed"):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().resolve_hypothesis(hid, conclusion, status)


@router.get("/notebooks")
def list_notebooks():
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().list_notebooks()


@router.post("/notebooks")
def create_notebook(body: NotebookCreate):
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().create_notebook(body.title, body.content, body.strategy_id, body.cells)


@router.get("/notebooks/{nid}")
def get_notebook(nid: str):
    from quant_lab.lab import get_quant_lab
    nb = get_quant_lab().get_notebook(nid)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return nb


@router.get("/stats")
def stats():
    from quant_lab.lab import get_quant_lab
    return get_quant_lab().stats()
