"""Tax & Advisory Workbench API — document intelligence, tax research + organizer,
workpapers, financial-statement analysis, due diligence, and global search.

Workpapers/analysis/search operate on the same accounting database the platform
router uses, so they reflect the live books.
"""
from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, Body, Query

from document_intelligence import ocr, pipeline
from document_intelligence.store import DocStore
from tax_research import engine as tax
from tax_research.organizer import TaxOrganizer
from workpapers import engine as wp
from advisory import fs_analysis, due_diligence
import global_search
from .accounting_platform_router import _conn as ACCT

router = APIRouter(prefix="/workbench", tags=["workbench"])
_docs = DocStore()
_taxorg = TaxOrganizer()


# ---- Document intelligence ----
@router.get("/docs/ocr-status")
def ocr_status():
    return ocr.engine_status()


@router.post("/docs/process")
def process_doc(body: dict = Body(...)):
    if body.get("base64"):
        result = pipeline.process_bytes(body.get("filename", "upload.bin"), base64.b64decode(body["base64"]))
    elif body.get("text") is not None:
        result = pipeline.process_text(body["text"], body.get("filename", "inline.txt"))
    else:
        from fastapi import HTTPException
        raise HTTPException(400, "provide 'text' or base64 'content'")
    if body.get("save"):
        result["stored"] = _docs.save(result, client_id=body.get("client_id"),
                                      link_entity=body.get("link_entity"), link_id=body.get("link_id"))
    return result


@router.get("/docs/search")
def docs_search(q: str = "", doc_type: Optional[str] = None):
    return {"documents": _docs.search(q, doc_type=doc_type), "stats": _docs.stats()}


# ---- Tax research ----
@router.get("/tax/topics")
def tax_topics():
    return {"topics": tax.list_topics()}


@router.post("/tax/research")
def tax_research(body: dict = Body(...)):
    return tax.research(body["query"])


@router.post("/tax/memo")
def tax_memo(body: dict = Body(...)):
    return tax.generate_memo(body["facts"], body["issues"], body["topic"],
                             alternatives=body.get("alternatives"), conclusion=body.get("conclusion"))


# ---- Tax organizer ----
@router.post("/tax/organizer/client")
def org_add_client(body: dict = Body(...)):
    return _taxorg.add_client(body["name"], entity_type=body.get("entity_type", "individual"),
                              tax_year=body.get("tax_year"), deadline=body.get("deadline"))


@router.get("/tax/organizer/dashboard")
def org_dashboard():
    return _taxorg.dashboard()


@router.post("/tax/organizer/received")
def org_received(request_id: int):
    return _taxorg.mark_received(request_id)


# ---- Workpapers ----
@router.get("/workpapers/trial-balance")
def wp_tb(as_of: Optional[str] = None):
    return wp.trial_balance_workpaper(ACCT, as_of)


@router.get("/workpapers/lead/{account_type}")
def wp_lead(account_type: str, as_of: Optional[str] = None):
    return wp.lead_schedule(ACCT, account_type, as_of)


@router.get("/workpapers/depreciation")
def wp_dep():
    return wp.depreciation_workpaper(ACCT)


@router.get("/workpapers/tax/{year}")
def wp_tax(year: int):
    return wp.tax_workpaper(ACCT, year)


# ---- Advisory: financial analysis + due diligence ----
@router.get("/advisory/analysis")
def advisory_analysis(as_of: str):
    return fs_analysis.analyze(ACCT, as_of)


@router.get("/advisory/due-diligence")
def advisory_dd(year: int):
    return due_diligence.report(ACCT, year)


# ---- Global search ----
@router.get("/search")
def search(q: str = Query(...)):
    return global_search.search_all(q, doc_store=_docs, acct_conn=ACCT)
