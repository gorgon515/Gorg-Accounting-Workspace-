"""Execution & Automation Operating System API — approval queue, execution engine,
document→accounting automation, month-end close, outcomes/learning, operations
dashboards, and the AI workflow builder. Shares the live accounting DB.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Query

from execution.engine import ExecutionEngine
from execution import automation
from operations.close import CloseStore, close_package
from operations import dashboards
from outcomes.engine import OutcomeStore
from tax_research.organizer import TaxOrganizer
from document_intelligence import pipeline
from n8n import generator
from .accounting_platform_router import _conn as ACCT

router = APIRouter(tags=["execution"])
_engine = ExecutionEngine(context={"acct_conn": ACCT})
_close = CloseStore()
_outcomes = OutcomeStore()
_taxorg = TaxOrganizer()


# ---- Approval + execution ----
@router.get("/exec/queue")
def queue():
    return _engine.queue_summary()


@router.get("/exec/actions")
def actions(status: Optional[str] = None):
    return {"actions": _engine.list(status=status)}


@router.post("/exec/propose")
def propose(body: dict = Body(...)):
    return _engine.propose(body["type"], body.get("payload", {}), confidence=body.get("confidence"),
                           affected=body.get("affected"), proposed_by=body.get("proposed_by", "user"),
                           auto=body.get("auto", False))


@router.get("/exec/{action_id}")
def get_action(action_id: int):
    return _engine.get(action_id)


@router.post("/exec/{action_id}/approve")
def approve(action_id: int, body: dict = Body(default={})):
    return _engine.approve(action_id, approved_by=body.get("approved_by", "user"), confirm=body.get("confirm", False))


@router.post("/exec/{action_id}/reject")
def reject(action_id: int, body: dict = Body(default={})):
    return _engine.reject(action_id, reason=body.get("reason", ""))


@router.post("/exec/{action_id}/execute")
def execute(action_id: int):
    return _engine.execute(action_id)


@router.post("/exec/{action_id}/rollback")
def rollback(action_id: int):
    return _engine.rollback(action_id)


@router.post("/exec/{action_id}/retry")
def retry(action_id: int):
    return _engine.retry(action_id)


# ---- Document → accounting automation ----
@router.post("/exec/automation/document")
def automate_document(body: dict = Body(...)):
    result = pipeline.process_text(body["text"], body.get("filename", "inline.txt")) if body.get("text") is not None \
        else pipeline.process_bytes(body["filename"], __import__("base64").b64decode(body["base64"]))
    action = automation.propose_from_document(_engine, result, vendor_id=body.get("vendor_id"),
                                              customer_id=body.get("customer_id"),
                                              expense_account=body.get("expense_account"))
    return {"extraction": {"doc_type": result["doc_type"], "fields": result["fields"]}, "proposed_action": action}


# ---- Month-end close ----
@router.post("/close/start")
def close_start(period: str = Query(...)):
    return _close.start(period)


@router.post("/close/update")
def close_update(body: dict = Body(...)):
    return _close.update_item(body["period"], body["key"], body["status"])


@router.get("/close/dashboard")
def close_dashboard():
    return _close.dashboard()


@router.get("/close/{period}/package")
def close_pkg(period: str):
    return close_package(ACCT, period)


# ---- Outcomes + learning ----
@router.post("/outcomes/recommendation")
def rec(body: dict = Body(...)):
    return _outcomes.record_recommendation(body["agent"], body["summary"],
                                            confidence=body.get("confidence"), ref=body.get("ref"))


@router.post("/outcomes/outcome")
def outcome(body: dict = Body(...)):
    return _outcomes.record_outcome(body["recommendation_id"], success=body["success"],
                                    satisfaction=body.get("satisfaction"), note=body.get("note", ""))


@router.get("/outcomes/metrics")
def outcome_metrics():
    return _outcomes.metrics()


# ---- Operations dashboards ----
@router.get("/ops/tax-season")
def ops_tax():
    return dashboards.tax_season(_taxorg)


@router.get("/ops/firm")
def ops_firm():
    return dashboards.firm_ops(ACCT)


@router.get("/ops/portfolio")
def ops_portfolio():
    return dashboards.portfolio_ops(_engine)


# ---- AI workflow builder ----
@router.post("/workflow/build")
def workflow_build(body: dict = Body(...)):
    return generator.build_plan(body)
