"""Data-integrity verification — ledger consistency and audit verification."""
from __future__ import annotations

from accounting_platform import gl


def ledger_integrity(acct_conn) -> dict:
    """Verify every posted entry balances, the trial balance ties, and global
    debits equal credits."""
    unbalanced = []
    entries = 0
    g_debit = g_credit = 0.0
    for e in acct_conn.execute("SELECT id FROM journal_entry WHERE status='posted'"):
        entries += 1
        row = acct_conn.execute(
            "SELECT COALESCE(SUM(debit),0) d, COALESCE(SUM(credit),0) c FROM journal_line WHERE entry_id=?",
            (e["id"],)).fetchone()
        g_debit += row["d"]; g_credit += row["c"]
        if abs(row["d"] - row["c"]) > 0.005:
            unbalanced.append({"entry_id": e["id"], "debit": round(row["d"], 2), "credit": round(row["c"], 2)})
    tb = gl.trial_balance(acct_conn)
    return {
        "entries_checked": entries,
        "unbalanced_entries": unbalanced,
        "global_debits": round(g_debit, 2), "global_credits": round(g_credit, 2),
        "global_balanced": abs(g_debit - g_credit) < 0.01,
        "trial_balance_balanced": tb["balanced"],
        "valid": not unbalanced and abs(g_debit - g_credit) < 0.01 and tb["balanced"],
    }


def audit_verification(acct_conn) -> dict:
    """Confirm posted entries left a create + post audit trail."""
    posted = {r["id"] for r in acct_conn.execute("SELECT id FROM journal_entry WHERE status='posted'")}
    audited_post = {int(r["entity_id"]) for r in acct_conn.execute(
        "SELECT entity_id FROM audit_event WHERE entity='journal_entry' AND action='post' AND entity_id IS NOT NULL")}
    missing = sorted(posted - audited_post)
    return {"posted_entries": len(posted), "with_post_audit": len(posted & audited_post),
            "missing_audit": missing, "valid": not missing}
