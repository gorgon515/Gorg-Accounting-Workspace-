"""Document → accounting automation.

Turns a processed document (from document_intelligence) into *draft* approval
actions — never auto-posting. An invoice becomes a draft AP bill; a receipt a
draft journal entry; everything else a recorded note. The user approves, then the
execution engine posts to the GL.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

# Heuristic expense-account suggestions by keyword (account numbers in the templates).
_EXPENSE_HINTS = [
    (("rent", "lease"), "5100"),
    (("salary", "wage", "payroll"), "5000"),
    (("software", "subscription", "saas", "research"), "5200"),
    (("legal", "professional", "consulting", "accounting"), "5400"),
]


def suggest_expense_account(text: str, default: str = "5200") -> str:
    t = (text or "").lower()
    for kws, acct in _EXPENSE_HINTS:
        if any(k in t for k in kws):
            return acct
    return default


def propose_from_document(engine, result: dict, *, vendor_id: Optional[int] = None,
                          customer_id: Optional[int] = None, expense_account: Optional[str] = None,
                          cash_account: str = "1000", revenue_account: str = "4000") -> dict:
    """Create the appropriate draft action for a processed document. Returns the
    proposed action (pending approval)."""
    doc_type = result.get("doc_type")
    fields = result.get("fields", {})
    amount = fields.get("total") or fields.get("compensation") or fields.get("max_amount")
    when = (fields.get("dates") or [date.today().isoformat()])[0][:10]
    conf = result.get("classification_confidence")
    summary = result.get("summary", "")
    acct = expense_account or suggest_expense_account(summary or doc_type or "")

    if doc_type == "invoice" and amount and vendor_id:
        return engine.propose("create_ap_bill", {
            "vendor_id": vendor_id, "amount": amount, "bill_date": when,
            "expense_account": acct, "number": fields.get("invoice_number", "")},
            confidence=conf, affected={"accounts": [acct, "2000"], "documents": [result.get("filename")]},
            proposed_by="document_automation")

    if doc_type == "receipt" and amount:
        return engine.propose("create_journal_entry", {
            "date": when, "memo": f"Receipt: {result.get('filename') or 'expense'}",
            "lines": [{"account": acct, "debit": amount}, {"account": cash_account, "credit": amount}],
            "source": "receipt"},
            confidence=conf, affected={"accounts": [acct, cash_account], "documents": [result.get("filename")]},
            proposed_by="document_automation")

    if doc_type in ("invoice",) and amount and customer_id:
        return engine.propose("create_ar_invoice", {
            "customer_id": customer_id, "amount": amount, "invoice_date": when},
            confidence=conf, affected={"accounts": ["1200", revenue_account]}, proposed_by="document_automation")

    # Fallback: record the extraction for review (tier 1).
    return engine.propose("create_note", {"note": f"Processed {doc_type}: {summary}", "fields": fields},
                          confidence=conf, proposed_by="document_automation")
