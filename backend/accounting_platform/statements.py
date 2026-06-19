"""Financial Statement engine — derived entirely from posted GL lines.

Balance Sheet provably ties to Assets = Liabilities + Equity + Net Income (the
accounting identity holds because every entry is balanced). Cash flow uses a
direct method, attributing each cash movement to the counterpart account's
cash-flow section.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Optional

from . import coa, gl


def trial_balance(conn, as_of: Optional[str] = None) -> dict:
    return gl.trial_balance(conn, as_of)


def _sum_by_type(conn, type_: str, start: Optional[str], end: Optional[str]) -> list[dict]:
    out = []
    for acct in coa.list_accounts(conn):
        if acct["type"] != type_:
            continue
        d, c = gl._account_movement(conn, acct["id"], as_of=end, start=start)
        bal = coa.signed_balance(type_, d, c)
        if abs(bal) > 0.005:
            out.append({"number": acct["number"], "name": acct["name"], "balance": bal})
    return out


def income_statement(conn, start: str, end: str) -> dict:
    revenue = _sum_by_type(conn, "revenue", start, end)
    expenses = _sum_by_type(conn, "expense", start, end)
    total_rev = round(sum(r["balance"] for r in revenue), 2)
    total_exp = round(sum(e["balance"] for e in expenses), 2)
    net = round(total_rev - total_exp, 2)
    return {"period": {"start": start, "end": end}, "revenue": revenue, "expenses": expenses,
            "total_revenue": total_rev, "total_expenses": total_exp, "net_income": net}


def net_income_to_date(conn, as_of: Optional[str]) -> float:
    rev = sum(r["balance"] for r in _sum_by_type(conn, "revenue", None, as_of))
    exp = sum(e["balance"] for e in _sum_by_type(conn, "expense", None, as_of))
    return round(rev - exp, 2)


def balance_sheet(conn, as_of: Optional[str] = None) -> dict:
    assets = _sum_by_type(conn, "asset", None, as_of)
    liabilities = _sum_by_type(conn, "liability", None, as_of)
    equity = _sum_by_type(conn, "equity", None, as_of)
    ni = net_income_to_date(conn, as_of)
    total_assets = round(sum(a["balance"] for a in assets), 2)
    total_liab = round(sum(l["balance"] for l in liabilities), 2)
    total_equity_posted = round(sum(e["balance"] for e in equity), 2)
    total_equity = round(total_equity_posted + ni, 2)
    return {
        "as_of": as_of, "assets": assets, "liabilities": liabilities,
        "equity": equity + [{"number": "—", "name": "Current Earnings (net income)", "balance": ni}],
        "total_assets": total_assets, "total_liabilities": total_liab,
        "total_equity": total_equity, "net_income": ni,
        "balanced": abs(total_assets - (total_liab + total_equity)) < 0.01,
    }


def cash_flow(conn, start: str, end: str) -> dict:
    """Direct method: attribute each cash movement to its counterpart section."""
    cash_ids = {a["id"] for a in coa.list_accounts(conn) if a["cash"]}
    sections = {"operating": 0.0, "investing": 0.0, "financing": 0.0}

    entries = conn.execute(
        "SELECT id FROM journal_entry WHERE status='posted' AND date >= ? AND date <= ?", (start, end))
    for (eid,) in [(r["id"],) for r in entries]:
        lines = [dict(l) for l in conn.execute(
            "SELECT jl.account_id, jl.debit, jl.credit, a.cash, a.cashflow, a.type "
            "FROM journal_line jl JOIN account a ON a.id=jl.account_id WHERE entry_id=?", (eid,))]
        cash_delta = sum((l["debit"] - l["credit"]) for l in lines if l["account_id"] in cash_ids)
        noncash = [l for l in lines if l["account_id"] not in cash_ids]
        weight = sum(l["debit"] + l["credit"] for l in noncash)
        if abs(cash_delta) < 0.005 or weight == 0:
            continue
        for l in noncash:
            w = (l["debit"] + l["credit"]) / weight
            sections[l["cashflow"] or "operating"] = round(
                sections.get(l["cashflow"] or "operating", 0.0) + cash_delta * w, 2)

    begin = _cash_balance(conn, _prev_day(start), cash_ids)
    net_change = round(sum(sections.values()), 2)
    end_bal = _cash_balance(conn, end, cash_ids)
    return {"period": {"start": start, "end": end}, **{f"{k}_activities": round(v, 2) for k, v in sections.items()},
            "net_change_in_cash": net_change, "beginning_cash": begin, "ending_cash": end_bal,
            "reconciles": abs((begin + net_change) - end_bal) < 0.01}


def _cash_balance(conn, as_of: Optional[str], cash_ids: set) -> float:
    total = 0.0
    for aid in cash_ids:
        d, c = gl._account_movement(conn, aid, as_of=as_of)
        total += d - c
    return round(total, 2)


def _prev_day(d: str) -> str:
    return (date.fromisoformat(d[:10]) - timedelta(days=1)).isoformat()


def comparative_income(conn, periods: list[dict]) -> dict:
    """periods: [{label, start, end}] → side-by-side income statements."""
    cols = []
    for p in periods:
        s = income_statement(conn, p["start"], p["end"])
        cols.append({"label": p.get("label", f"{p['start']}–{p['end']}"),
                     "total_revenue": s["total_revenue"], "total_expenses": s["total_expenses"],
                     "net_income": s["net_income"]})
    return {"columns": cols}


def general_ledger_report(conn, start: Optional[str] = None, end: Optional[str] = None) -> dict:
    return {"entries": gl.list_entries(conn, start=start, end=end, status="posted", limit=1000)}
