"""Operations dashboards: tax season, accounting-firm ops, and portfolio ops.
Thin aggregators over the existing engines."""
from __future__ import annotations

from typing import Optional

from accounting_platform import ar, ap, clients as acct_clients


def tax_season(org) -> dict:
    """Tax-season operating dashboard from the TaxOrganizer."""
    dash = org.dashboard()
    for c in dash["clients"]:
        c["filing_ready"] = c["missing_documents"] == 0 and c.get("status") in ("review", "ready", "filed")
    return {
        **dash,
        "filing_ready": sum(1 for c in dash["clients"] if c["filing_ready"]),
        "awaiting_documents": dash["awaiting_docs"],
        "by_status": _count_by(dash["clients"], "status"),
    }


def firm_ops(acct_conn) -> dict:
    """Accounting-firm operations: clients, engagements/deadlines, AR/AP status."""
    cl = acct_clients.list_clients(acct_conn)
    engagements = acct_clients.list_engagements(acct_conn)
    deadlines = acct_clients.upcoming_deadlines(acct_conn, days=30)
    return {
        "clients": len(cl),
        "engagements": engagements,
        "open_engagements": sum(1 for e in engagements if e["status"] == "active"),
        "upcoming_deadlines": deadlines,
        "receivables": ar.aging(acct_conn)["total"],
        "payables": ap.aging(acct_conn)["total"],
    }


def portfolio_ops(exec_engine, *, positions: Optional[list] = None, watchlist: Optional[list] = None,
                  theses: Optional[list] = None) -> dict:
    """Portfolio operations center: research queue, positions, and the approval
    queue for trade/broker actions (which are Tier-4 — never auto-executed)."""
    pending = exec_engine.list(status="proposed")
    trade_queue = [a for a in pending if a["type"] in ("broker_action",)]
    return {
        "research_queue": watchlist or [],
        "positions": positions or [],
        "position_count": len(positions or []),
        "investment_theses": theses or [],
        "approval_queue": [{"id": a["id"], "type": a["type"], "tier": a["tier"], "payload": a["payload"]}
                           for a in trade_queue],
        "note": "Trade/broker actions are Tier 4 — HELIOS prepares only; you execute at your broker.",
    }


def _count_by(rows, key):
    out = {}
    for r in rows:
        out[r.get(key)] = out.get(r.get(key), 0) + 1
    return out
