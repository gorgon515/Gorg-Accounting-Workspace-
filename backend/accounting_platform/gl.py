"""General Ledger: balanced journal entries, posting with period controls,
account balances, trial balance, and reversing entries. The single source of
truth — AP/AR and fixed assets all post here.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import coa
from .db import audit, ensure_period, now_iso, period_status

CENT = 0.005


def _resolve_account(conn, line: dict) -> dict:
    if line.get("account_id"):
        acct = coa.get_account(conn, line["account_id"])
    elif line.get("account"):
        acct = coa.by_number(conn, str(line["account"]))
    else:
        raise ValueError("each line needs account_id or account (number)")
    if not acct:
        raise ValueError(f"unknown account: {line.get('account') or line.get('account_id')}")
    if not acct["active"]:
        raise ValueError(f"account {acct['number']} is inactive")
    return acct


def validate_lines(conn, lines: list[dict]) -> tuple[float, float]:
    if not lines or len(lines) < 2:
        raise ValueError("a journal entry needs at least two lines")
    debits = credits = 0.0
    for ln in lines:
        d, c = float(ln.get("debit", 0) or 0), float(ln.get("credit", 0) or 0)
        if d < 0 or c < 0:
            raise ValueError("debit/credit cannot be negative")
        if d > 0 and c > 0:
            raise ValueError("a line cannot have both a debit and a credit")
        if d == 0 and c == 0:
            raise ValueError("each line needs a non-zero debit or credit")
        _resolve_account(conn, ln)
        debits += d
        credits += c
    if abs(debits - credits) > CENT:
        raise ValueError(f"entry not balanced: debits {debits:.2f} != credits {credits:.2f}")
    return round(debits, 2), round(credits, 2)


def create_entry(conn: sqlite3.Connection, date: str, lines: list[dict], *, memo: str = "",
                 source: str = "manual", entry_type: str = "standard", user: str = "system",
                 post: bool = True) -> dict:
    validate_lines(conn, lines)
    cur = conn.execute(
        "INSERT INTO journal_entry (date,memo,source,status,entry_type,created_by,created_at) "
        "VALUES (?,?,?,'draft',?,?,?)", (date, memo, source, entry_type, user, now_iso()))
    eid = cur.lastrowid
    for ln in lines:
        acct = _resolve_account(conn, ln)
        conn.execute("INSERT INTO journal_line (entry_id,account_id,debit,credit,memo) VALUES (?,?,?,?,?)",
                     (eid, acct["id"], float(ln.get("debit", 0) or 0), float(ln.get("credit", 0) or 0), ln.get("memo")))
    conn.commit()
    audit(conn, entity="journal_entry", entity_id=eid, action="create", new={"date": date, "memo": memo}, user=user)
    conn.commit()
    if post:
        return post_entry(conn, eid, user=user)
    return get_entry(conn, eid)


def post_entry(conn: sqlite3.Connection, entry_id: int, user: str = "system") -> dict:
    e = get_entry(conn, entry_id)
    if not e:
        raise ValueError("no such entry")
    if e["status"] == "posted":
        return e
    y, m = int(e["date"][:4]), int(e["date"][5:7])
    if period_status(conn, y, m) == "closed":
        raise ValueError(f"period {y}-{m:02d} is closed")
    ensure_period(conn, y, m)
    conn.execute("UPDATE journal_entry SET status='posted', posted_at=? WHERE id=?", (now_iso(), entry_id))
    audit(conn, entity="journal_entry", entity_id=entry_id, action="post",
          old={"status": "draft"}, new={"status": "posted"}, user=user)
    conn.commit()
    return get_entry(conn, entry_id)


def reverse_entry(conn: sqlite3.Connection, entry_id: int, date: Optional[str] = None, user: str = "system") -> dict:
    e = get_entry(conn, entry_id)
    if not e:
        raise ValueError("no such entry")
    swapped = [{"account_id": ln["account_id"], "debit": ln["credit"], "credit": ln["debit"],
                "memo": f"reversal of #{entry_id}"} for ln in e["lines"]]
    return create_entry(conn, date or e["date"], swapped, memo=f"Reversal of #{entry_id}: {e['memo']}",
                        source="reversal", entry_type="reversing", user=user)


def get_entry(conn: sqlite3.Connection, entry_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM journal_entry WHERE id=?", (entry_id,)).fetchone()
    if not r:
        return None
    e = dict(r)
    e["lines"] = [dict(l) for l in conn.execute(
        "SELECT jl.*, a.number AS account_number, a.name AS account_name "
        "FROM journal_line jl JOIN account a ON a.id=jl.account_id WHERE entry_id=?", (entry_id,))]
    return e


def list_entries(conn: sqlite3.Connection, start: Optional[str] = None, end: Optional[str] = None,
                 status: Optional[str] = None, limit: int = 200) -> list[dict]:
    sql, args = "SELECT id FROM journal_entry WHERE 1=1", []
    if start:
        sql += " AND date >= ?"; args.append(start)
    if end:
        sql += " AND date <= ?"; args.append(end)
    if status:
        sql += " AND status = ?"; args.append(status)
    sql += " ORDER BY date DESC, id DESC LIMIT ?"; args.append(limit)
    return [get_entry(conn, r["id"]) for r in conn.execute(sql, args)]


def _account_movement(conn, account_id: int, as_of: Optional[str] = None, start: Optional[str] = None) -> tuple[float, float]:
    sql = ("SELECT COALESCE(SUM(jl.debit),0) d, COALESCE(SUM(jl.credit),0) c FROM journal_line jl "
           "JOIN journal_entry je ON je.id=jl.entry_id WHERE je.status='posted' AND jl.account_id=?")
    args = [account_id]
    if start:
        sql += " AND je.date >= ?"; args.append(start)
    if as_of:
        sql += " AND je.date <= ?"; args.append(as_of)
    r = conn.execute(sql, args).fetchone()
    return round(r["d"], 2), round(r["c"], 2)


def account_balance(conn: sqlite3.Connection, account_id: int, as_of: Optional[str] = None) -> dict:
    acct = coa.get_account(conn, account_id)
    d, c = _account_movement(conn, account_id, as_of=as_of)
    return {"account_id": account_id, "number": acct["number"], "name": acct["name"],
            "type": acct["type"], "debits": d, "credits": c,
            "balance": coa.signed_balance(acct["type"], d, c)}


def trial_balance(conn: sqlite3.Connection, as_of: Optional[str] = None) -> dict:
    rows, total_debit_col, total_credit_col = [], 0.0, 0.0
    for acct in coa.list_accounts(conn):
        d, c = _account_movement(conn, acct["id"], as_of=as_of)
        if d == 0 and c == 0:
            continue
        bal = coa.signed_balance(acct["type"], d, c)
        debit_col = bal if acct["type"] in coa.DEBIT_NORMAL and bal >= 0 else (-bal if acct["type"] not in coa.DEBIT_NORMAL and bal < 0 else 0)
        credit_col = bal if acct["type"] not in coa.DEBIT_NORMAL and bal >= 0 else (-bal if acct["type"] in coa.DEBIT_NORMAL and bal < 0 else 0)
        total_debit_col += round(debit_col, 2)
        total_credit_col += round(credit_col, 2)
        rows.append({"number": acct["number"], "name": acct["name"], "type": acct["type"],
                     "debit": round(debit_col, 2), "credit": round(credit_col, 2)})
    return {"as_of": as_of, "rows": rows, "total_debit": round(total_debit_col, 2),
            "total_credit": round(total_credit_col, 2),
            "balanced": abs(total_debit_col - total_credit_col) < CENT}


def account_ledger(conn: sqlite3.Connection, account_id: int, start: Optional[str] = None,
                   end: Optional[str] = None) -> dict:
    acct = coa.get_account(conn, account_id)
    rows = conn.execute(
        "SELECT je.id, je.date, je.memo, jl.debit, jl.credit FROM journal_line jl "
        "JOIN journal_entry je ON je.id=jl.entry_id WHERE je.status='posted' AND jl.account_id=? "
        + (" AND je.date >= ?" if start else "") + (" AND je.date <= ?" if end else "")
        + " ORDER BY je.date, je.id",
        [account_id] + ([start] if start else []) + ([end] if end else []))
    debit_normal = acct["type"] in coa.DEBIT_NORMAL
    running, out = 0.0, []
    for r in rows:
        running += (r["debit"] - r["credit"]) if debit_normal else (r["credit"] - r["debit"])
        out.append({"entry_id": r["id"], "date": r["date"], "memo": r["memo"],
                    "debit": r["debit"], "credit": r["credit"], "balance": round(running, 2)})
    return {"account": {"number": acct["number"], "name": acct["name"], "type": acct["type"]}, "entries": out}
