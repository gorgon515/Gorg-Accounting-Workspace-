"""Accounting Intelligence endpoints: ASC knowledge base + memo generator."""
from __future__ import annotations

from fastapi import APIRouter

from ..models import MemoRequest
from ..services import accounting_research as research

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("/topics")
def topics() -> dict:
    return {"topics": research.list_topics()}


@router.get("/asc/{topic}")
def asc(topic: str) -> dict:
    return research.explain_asc(topic)


@router.post("/memo")
def memo(req: MemoRequest) -> dict:
    return research.generate_memo(req.issue, req.facts, req.topic, req.conclusion)
