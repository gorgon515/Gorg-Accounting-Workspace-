"""Accounting Intelligence endpoints: live intel feed, daily briefing, knowledge
graph, implementation checklists, and the full technical memo."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..models import ChecklistRequest, MemoFullRequest
from accounting.briefing.generator import generate_briefing
from accounting.collectors.registry import collect_all
from accounting.storage.db import IntelStore
from accounting import knowledge_graph as kg
from accounting import research

router = APIRouter(prefix="/accounting", tags=["accounting-intel"])

# One shared, file-backed store (path overridable via HELIOS_INTEL_DB).
_store = IntelStore()


def _refresh() -> dict:
    """Live-collect from the standard-setters and persist. Network-guarded:
    unreachable sources are reported, not fatal."""
    items, errors = collect_all()
    result = _store.upsert_many(items)
    result["source_errors"] = errors
    return result


@router.get("/intel")
def intel(source: Optional[str] = None, doc_type: Optional[str] = None, limit: int = 100):
    return {"items": _store.query(source=source, doc_type=doc_type, limit=limit), "stored": _store.count()}


@router.post("/intel/refresh")
def intel_refresh():
    return _refresh()


@router.get("/briefing")
def briefing(refresh: bool = Query(False)):
    errors = {}
    if refresh or _store.count() == 0:
        try:
            errors = _refresh().get("source_errors", {})
        except Exception as exc:  # noqa: BLE001 - never let a dead feed 500 the briefing
            errors = {"collector": str(exc)}
    items = _store.query(limit=200)
    return generate_briefing(items, source_errors=errors)


@router.get("/graph")
def graph(asc: Optional[str] = None):
    items = _store.query(limit=200)
    return kg.subgraph_for_asc(asc, items) if asc else kg.build_graph(items)


@router.post("/checklist")
def checklist(req: ChecklistRequest):
    return research.implementation_checklist(req.topic)


@router.post("/memo/full")
def memo_full(req: MemoFullRequest):
    return research.technical_memo(req.facts, req.issue, req.topic,
                                   alternatives=req.alternatives, conclusion=req.conclusion)
