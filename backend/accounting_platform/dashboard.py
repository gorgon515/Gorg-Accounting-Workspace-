"""Accounting dashboard — live aggregation for the React HUD."""
from __future__ import annotations

from datetime import date
from typing import Optional

from . import ap, ar, clients, coa, gl, statements


def overview(conn, as_of: Optional[str] = None) -> dict:
    as_of = as_of or date.today().isoformat()
    y = as_of[:4]
    ytd_start = f"{y}-01-01"
    mtd_start = as_of[:7] + "-01"

    cash = round(sum(gl.account_balance(conn, a["id"], as_of)["balance"]
                     for a in coa.list_accounts(conn) if a["cash"]), 2)
    ar_aging = ar.aging(conn, as_of)
    ap_aging = ap.aging(conn, as_of)
    ytd = statements.income_statement(conn, ytd_start, as_of)
    mtd = statements.income_statement(conn, mtd_start, as_of)
    bs = statements.balance_sheet(conn, as_of)

    alerts = []
    if cash < 0:
        alerts.append({"severity": "high", "message": f"Negative cash position ({cash})."})
    overdue_ar = ar_aging["buckets"]["31-60"] + ar_aging["buckets"]["61-90"] + ar_aging["buckets"]["90+"]
    if overdue_ar > 0:
        alerts.append({"severity": "medium", "message": f"{overdue_ar:.2f} in receivables over 30 days past due."})
    cash_req = ap.cash_requirements(conn, weeks=2, as_of=as_of)
    if cash_req["total_due"] > cash:
        alerts.append({"severity": "high", "message": f"Bills due in 2 weeks ({cash_req['total_due']}) exceed cash ({cash})."})

    return {
        "as_of": as_of,
        "cash_position": cash,
        "receivables": {"total": ar_aging["total"], "buckets": ar_aging["buckets"]},
        "payables": {"total": ap_aging["total"], "buckets": ap_aging["buckets"]},
        "profitability": {"mtd_net_income": mtd["net_income"], "ytd_net_income": ytd["net_income"],
                          "ytd_revenue": ytd["total_revenue"], "ytd_expenses": ytd["total_expenses"]},
        "balance_sheet_summary": {"total_assets": bs["total_assets"], "total_liabilities": bs["total_liabilities"],
                                  "total_equity": bs["total_equity"], "balanced": bs["balanced"]},
        "recent_entries": [{"id": e["id"], "date": e["date"], "memo": e["memo"], "source": e["source"],
                            "amount": round(sum(l["debit"] for l in e["lines"]), 2)}
                           for e in gl.list_entries(conn, status="posted", limit=8)],
        "upcoming_deadlines": clients.upcoming_deadlines(conn, days=30),
        "alerts": alerts,
    }
