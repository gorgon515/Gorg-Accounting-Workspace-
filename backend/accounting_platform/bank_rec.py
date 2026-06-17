"""Bank reconciliation — import (CSV/OFX/QFX), matching against posted GL cash
lines, and a reconciliation report with outstanding items and differences."""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import Optional

from . import coa, gl
from .db import now_iso

_TAG = re.compile(r"<([A-Z0-9.]+)>([^<\r\n]*)")
_STMTTRN = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.S | re.I)


def parse_csv(text: str, *, date_col="date", amount_col="amount", desc_col="description") -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            amount = float(norm.get(amount_col, "").replace(",", "").replace("$", ""))
        except ValueError:
            continue
        out.append({"date": norm.get(date_col, ""), "amount": round(amount, 2),
                    "description": norm.get(desc_col, "")})
    return out


def parse_ofx(text: str) -> list[dict]:
    """Parse OFX/QFX <STMTTRN> blocks (SGML-style tags)."""
    out = []
    for block in _STMTTRN.findall(text):
        fields = {t: v.strip() for t, v in _TAG.findall(block)}
        amt = fields.get("TRNAMT")
        if amt is None:
            continue
        raw = fields.get("DTPOSTED", "")[:8]
        iso = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw
        out.append({"date": iso, "amount": round(float(amt), 2),
                    "description": fields.get("NAME") or fields.get("MEMO", ""),
                    "fitid": fields.get("FITID")})
    return out


def import_transactions(conn, account_id: int, txns: list[dict]) -> dict:
    imported, skipped = 0, 0
    for t in txns:
        if t.get("fitid"):
            exists = conn.execute("SELECT 1 FROM bank_txn WHERE account_id=? AND fitid=?",
                                  (account_id, t["fitid"])).fetchone()
            if exists:
                skipped += 1
                continue
        conn.execute("INSERT INTO bank_txn (account_id,date,amount,description,fitid,status,imported_at) "
                     "VALUES (?,?,?,?,?, 'unmatched', ?)",
                     (account_id, t["date"], round(float(t["amount"]), 2), t.get("description", ""),
                      t.get("fitid"), now_iso()))
        imported += 1
    conn.commit()
    return {"imported": imported, "skipped_duplicates": skipped}


def auto_match(conn, account_id: int, tol_days: int = 3, tol_amount: float = 0.01) -> dict:
    """Match unmatched bank txns to posted GL lines on the cash account by signed
    amount (cash delta = debit - credit) within a date tolerance."""
    gl_lines = [dict(r) for r in conn.execute(
        "SELECT jl.id, je.date, (jl.debit - jl.credit) AS delta FROM journal_line jl "
        "JOIN journal_entry je ON je.id=jl.entry_id WHERE je.status='posted' AND jl.account_id=?",
        (account_id,))]
    used = set()
    matched = 0
    for bt in conn.execute("SELECT * FROM bank_txn WHERE account_id=? AND status='unmatched'", (account_id,)):
        bt_date = date.fromisoformat(bt["date"][:10]) if bt["date"] else None
        for gli in gl_lines:
            if gli["id"] in used:
                continue
            if abs(gli["delta"] - bt["amount"]) <= tol_amount:
                if bt_date and gli["date"]:
                    if abs((date.fromisoformat(gli["date"][:10]) - bt_date).days) > tol_days:
                        continue
                conn.execute("UPDATE bank_txn SET status='matched', matched_line_id=? WHERE id=?",
                             (gli["id"], bt["id"]))
                used.add(gli["id"])
                matched += 1
                break
    conn.commit()
    return {"matched": matched, "account_id": account_id}


def reconciliation_report(conn, account_id: int, as_of: Optional[str] = None) -> dict:
    acct = coa.get_account(conn, account_id)
    book = gl.account_balance(conn, account_id, as_of)["balance"]
    bank_rows = [dict(r) for r in conn.execute(
        "SELECT * FROM bank_txn WHERE account_id=?" + (" AND date<=?" if as_of else ""),
        [account_id] + ([as_of] if as_of else []))]
    bank_balance = round(sum(r["amount"] for r in bank_rows), 2)
    unmatched_bank = [r for r in bank_rows if r["status"] == "unmatched"]
    # Posted cash lines not matched to a bank txn = outstanding (in books, not on statement).
    matched_ids = {r["matched_line_id"] for r in bank_rows if r["matched_line_id"]}
    outstanding_book = [dict(r) for r in conn.execute(
        "SELECT jl.id, je.date, (jl.debit-jl.credit) AS delta, je.memo FROM journal_line jl "
        "JOIN journal_entry je ON je.id=jl.entry_id WHERE je.status='posted' AND jl.account_id=?", (account_id,))
        if r["id"] not in matched_ids]
    return {
        "account": acct["number"], "as_of": as_of, "book_balance": book, "bank_balance": bank_balance,
        "difference": round(book - bank_balance, 2),
        "unmatched_bank_items": unmatched_bank,
        "outstanding_book_items": outstanding_book,
        "reconciled": abs(book - bank_balance) < 0.01 and not unmatched_bank,
    }
