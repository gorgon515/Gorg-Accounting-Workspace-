"""Accounting Platform API — GL, COA, journal entries, AP/AR, fixed assets, bank
reconciliation, statements, clients, documents, import, audit, and dashboard.

Engine ValueErrors map to HTTP 400 via the app-wide handler, so the double-entry
validation is the single source of truth for request correctness.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Query

from accounting_platform import (
    ap, ar, bank_rec, clients, coa, dashboard, db, documents, fixed_assets, gl, importers, statements,
)

router = APIRouter(prefix="/platform", tags=["accounting-platform"])
_conn = db.connect()  # shared, file-backed accounting database


# ---- Chart of accounts ----
@router.post("/coa/seed")
def seed(template: str = Query("general_small_business")):
    return coa.seed_template(_conn, template)


@router.get("/coa")
def chart(active_only: bool = False):
    return {"accounts": coa.list_accounts(_conn, active_only), "templates": list(coa.TEMPLATES)}


@router.post("/coa/account")
def add_account(body: dict = Body(...)):
    return coa.create_account(_conn, body["number"], body["name"], body["type"],
                              subtype=body.get("subtype"), cash=bool(body.get("cash")),
                              cashflow=body.get("cashflow"))


# ---- General ledger ----
@router.post("/journal")
def journal(body: dict = Body(...)):
    return gl.create_entry(_conn, body["date"], body["lines"], memo=body.get("memo", ""),
                           source=body.get("source", "manual"), entry_type=body.get("entry_type", "standard"),
                           post=body.get("post", True))


@router.get("/journal")
def entries(start: Optional[str] = None, end: Optional[str] = None, status: Optional[str] = None):
    return {"entries": gl.list_entries(_conn, start=start, end=end, status=status)}


@router.post("/journal/{eid}/reverse")
def reverse(eid: int, date: Optional[str] = None):
    return gl.reverse_entry(_conn, eid, date)


@router.get("/trial-balance")
def trial_balance(as_of: Optional[str] = None):
    return gl.trial_balance(_conn, as_of)


@router.get("/account/{account_id}/ledger")
def ledger(account_id: int, start: Optional[str] = None, end: Optional[str] = None):
    return gl.account_ledger(_conn, account_id, start, end)


@router.post("/period/close")
def close_period(year: int, month: int):
    return db.close_period(_conn, year, month)


# ---- Financial statements ----
@router.get("/statements/balance-sheet")
def balance_sheet(as_of: Optional[str] = None):
    return statements.balance_sheet(_conn, as_of)


@router.get("/statements/income")
def income(start: str, end: str):
    return statements.income_statement(_conn, start, end)


@router.get("/statements/cash-flow")
def cash_flow(start: str, end: str):
    return statements.cash_flow(_conn, start, end)


# ---- Accounts payable ----
@router.post("/ap/vendor")
def add_vendor(body: dict = Body(...)):
    return ap.add_vendor(_conn, body["name"], email=body.get("email", ""),
                         terms_days=body.get("terms_days", 30), is_1099=bool(body.get("is_1099")),
                         tin=body.get("tin", ""))


@router.get("/ap/vendors")
def vendors():
    return {"vendors": ap.list_vendors(_conn)}


@router.post("/ap/bill")
def add_bill(body: dict = Body(...)):
    return ap.add_bill(_conn, body["vendor_id"], body["amount"], body["bill_date"],
                       body["expense_account"], due_date=body.get("due_date"), number=body.get("number", ""))


@router.post("/ap/bill/{bid}/pay")
def pay_bill(bid: int, body: dict = Body(...)):
    return ap.pay_bill(_conn, bid, body["amount"], body["pay_date"], cash_account=body.get("cash_account", "1000"))


@router.get("/ap/aging")
def ap_aging(as_of: Optional[str] = None):
    return ap.aging(_conn, as_of)


@router.get("/ap/1099")
def ap_1099(year: int):
    return ap.vendor_1099_totals(_conn, year)


# ---- Accounts receivable ----
@router.post("/ar/customer")
def add_customer(body: dict = Body(...)):
    return ar.add_customer(_conn, body["name"], email=body.get("email", ""), terms_days=body.get("terms_days", 30))


@router.get("/ar/customers")
def customers():
    return {"customers": ar.list_customers(_conn)}


@router.post("/ar/invoice")
def add_invoice(body: dict = Body(...)):
    return ar.add_invoice(_conn, body["customer_id"], body["amount"], body["invoice_date"],
                          due_date=body.get("due_date"), number=body.get("number", ""))


@router.post("/ar/invoice/{iid}/pay")
def pay_invoice(iid: int, body: dict = Body(...)):
    return ar.record_payment(_conn, iid, body["amount"], body["pay_date"], cash_account=body.get("cash_account", "1000"))


@router.get("/ar/aging")
def ar_aging(as_of: Optional[str] = None):
    return ar.aging(_conn, as_of)


# ---- Fixed assets ----
@router.post("/assets")
def add_asset(body: dict = Body(...)):
    return fixed_assets.add_asset(_conn, body["name"], body["acquired_on"], body["cost"], body["life_months"],
                                  salvage=body.get("salvage", 0), method=body.get("method", "straight_line"),
                                  units_total=body.get("units_total"))


@router.get("/assets")
def assets():
    return {"assets": fixed_assets.list_assets(_conn)}


@router.get("/assets/{aid}/schedule")
def asset_schedule(aid: int):
    return fixed_assets.depreciation_schedule(_conn, aid)


@router.post("/assets/{aid}/depreciate")
def depreciate(aid: int, body: dict = Body(...)):
    return fixed_assets.post_depreciation(_conn, aid, body["amount"], body["entry_date"])


# ---- Bank reconciliation ----
@router.post("/bank/import")
def bank_import(body: dict = Body(...)):
    fmt = body.get("format", "csv")
    txns = bank_rec.parse_ofx(body["content"]) if fmt in ("ofx", "qfx") else bank_rec.parse_csv(body["content"])
    return bank_rec.import_transactions(_conn, body["account_id"], txns)


@router.post("/bank/match")
def bank_match(account_id: int):
    return bank_rec.auto_match(_conn, account_id)


@router.get("/bank/reconciliation")
def bank_reconciliation(account_id: int, as_of: Optional[str] = None):
    return bank_rec.reconciliation_report(_conn, account_id, as_of)


# ---- Clients / documents ----
@router.post("/clients")
def add_client(body: dict = Body(...)):
    return clients.add_client(_conn, body["name"], kind=body.get("kind", ""), email=body.get("email", ""))


@router.get("/clients")
def list_clients():
    return {"clients": clients.list_clients(_conn), "deadlines": clients.upcoming_deadlines(_conn)}


@router.post("/clients/engagement")
def add_engagement(body: dict = Body(...)):
    return clients.add_engagement(_conn, body["client_id"], body["name"],
                                  due_date=body.get("due_date"), deliverable=body.get("deliverable", ""))


@router.post("/documents")
def add_document(body: dict = Body(...)):
    return documents.add_document(_conn, body["title"], doc_type=body.get("doc_type", ""),
                                  tags=body.get("tags", []), client_id=body.get("client_id"))


@router.get("/documents")
def search_documents(q: str = "", doc_type: Optional[str] = None, tag: Optional[str] = None):
    return {"documents": documents.search(_conn, q, doc_type=doc_type, tag=tag)}


# ---- Import / audit / dashboard ----
@router.post("/import/journal")
def import_journal(body: dict = Body(...)):
    return importers.import_journal_csv(_conn, body["csv"], post=body.get("post", True))


@router.get("/audit")
def audit(limit: int = 100, entity: Optional[str] = None):
    return {"events": db.audit_log(_conn, limit, entity)}


@router.get("/dashboard")
def acct_dashboard(as_of: Optional[str] = None):
    return dashboard.overview(_conn, as_of)
