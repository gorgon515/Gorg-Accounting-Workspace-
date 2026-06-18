"""Action registry — risk tiers and executors.

Maps each action type to a risk tier and a real executor (with optional rollback).
The tiers enforce the safety policy: Tier 1 may auto-execute; Tier 2/3 require
human approval; Tier 4 (broker actions, tax filings, external submissions) is NEVER
executed autonomously and, even after approval, HELIOS only *prepares* — a human
performs the external act outside HELIOS.
"""
from __future__ import annotations

from typing import Callable, Optional

# action_type -> risk tier (1=low … 4=critical)
TIERS: dict[str, int] = {
    # Tier 1 — low risk, auto-executable
    "create_task": 1, "generate_report": 1, "schedule_meeting": 1, "create_note": 1,
    # Tier 2 — moderate, requires approval
    "create_journal_entry": 2, "create_ap_bill": 2, "create_ar_invoice": 2, "create_workflow": 2,
    # Tier 3 — high, requires explicit approval
    "delete_accounting": 3, "modify_closed_period": 3, "client_record_change": 3, "tax_document": 3,
    # Tier 4 — critical, never auto; prepare-only
    "broker_action": 4, "tax_filing": 4, "external_submission": 4,
}

TIER_LABEL = {1: "low", 2: "moderate", 3: "high", 4: "critical"}


def tier_of(action_type: str) -> int:
    if action_type not in TIERS:
        raise ValueError(f"unknown action type: {action_type}")
    return TIERS[action_type]


# ---- executors: run(payload, ctx) -> result ; rollback(payload, result, ctx) ----
def _acct(ctx):
    conn = (ctx or {}).get("acct_conn")
    if conn is None:
        raise ValueError("no accounting connection in execution context")
    return conn


def _run_journal_entry(payload, ctx):
    from accounting_platform import gl
    e = gl.create_entry(_acct(ctx), payload["date"], payload["lines"],
                        memo=payload.get("memo", ""), source=payload.get("source", "execution"),
                        entry_type=payload.get("entry_type", "standard"))
    return {"entry_id": e["id"], "status": e["status"]}


def _rollback_journal_entry(payload, result, ctx):
    from accounting_platform import gl
    rev = gl.reverse_entry(_acct(ctx), result["entry_id"])
    return {"reversed_by": rev["id"]}


def _run_ap_bill(payload, ctx):
    from accounting_platform import ap
    b = ap.add_bill(_acct(ctx), payload["vendor_id"], payload["amount"], payload["bill_date"],
                    payload["expense_account"], due_date=payload.get("due_date"), number=payload.get("number", ""))
    return {"bill_id": b["id"], "je_id": b["je_id"]}


def _rollback_ap_bill(payload, result, ctx):
    from accounting_platform import gl
    rev = gl.reverse_entry(_acct(ctx), result["je_id"])
    return {"reversed_by": rev["id"]}


def _run_ar_invoice(payload, ctx):
    from accounting_platform import ar
    i = ar.add_invoice(_acct(ctx), payload["customer_id"], payload["amount"], payload["invoice_date"],
                       due_date=payload.get("due_date"), number=payload.get("number", ""))
    return {"invoice_id": i["id"], "je_id": i["je_id"]}


def _rollback_ar_invoice(payload, result, ctx):
    from accounting_platform import gl
    rev = gl.reverse_entry(_acct(ctx), result["je_id"])
    return {"reversed_by": rev["id"]}


def _run_workflow(payload, ctx):
    from n8n import generator
    return {"workflow": generator.from_spec(payload)}


def _run_record_only(payload, ctx):
    # Tier-1 informational actions and generic tier-3 record actions.
    return {"recorded": True, "payload": payload}


def _run_prepare_only(payload, ctx):
    # Tier-4 critical actions: HELIOS only PREPARES. A human must submit externally.
    return {"prepared": True, "status": "awaiting_external_submission",
            "note": "HELIOS never submits this automatically. A human must review and "
                    "execute the broker/tax/external action outside HELIOS.",
            "package": payload}


_EXECUTORS: dict[str, dict] = {
    "create_journal_entry": {"run": _run_journal_entry, "rollback": _rollback_journal_entry},
    "create_ap_bill": {"run": _run_ap_bill, "rollback": _rollback_ap_bill},
    "create_ar_invoice": {"run": _run_ar_invoice, "rollback": _rollback_ar_invoice},
    "create_workflow": {"run": _run_workflow, "rollback": None},
    "create_task": {"run": _run_record_only, "rollback": None},
    "generate_report": {"run": _run_record_only, "rollback": None},
    "schedule_meeting": {"run": _run_record_only, "rollback": None},
    "create_note": {"run": _run_record_only, "rollback": None},
    "delete_accounting": {"run": _run_record_only, "rollback": None},
    "modify_closed_period": {"run": _run_record_only, "rollback": None},
    "client_record_change": {"run": _run_record_only, "rollback": None},
    "tax_document": {"run": _run_record_only, "rollback": None},
    "broker_action": {"run": _run_prepare_only, "rollback": None},
    "tax_filing": {"run": _run_prepare_only, "rollback": None},
    "external_submission": {"run": _run_prepare_only, "rollback": None},
}


def executor(action_type: str) -> Optional[dict]:
    return _EXECUTORS.get(action_type)
