"""Accounts Payable — vendors, bills, payments, aging, 1099, cash forecast.

Bills and payments post real journal entries into the GL (Dr expense / Cr AP on a
bill; Dr AP / Cr cash on payment), so AP ties to the trial balance and statements.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from . import coa, gl
from .db import audit, now_iso


def add_vendor(conn, name: str, *, email: str = "", terms_days: int = 30,
               is_1099: bool = False, tin: str = "", user: str = "system") -> dict:
    cur = conn.execute("INSERT INTO vendor (name,email,terms_days,is_1099,tin,created_at) VALUES (?,?,?,?,?,?)",
                       (name, email, terms_days, 1 if is_1099 else 0, tin, now_iso()))
    conn.commit()
    audit(conn, entity="vendor", entity_id=cur.lastrowid, action="create", new={"name": name}, user=user)
    conn.commit()
    return dict(conn.execute("SELECT * FROM vendor WHERE id=?", (cur.lastrowid,)).fetchone())


def list_vendors(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM vendor ORDER BY name")]


def add_bill(conn, vendor_id: int, amount: float, bill_date: str, expense_account: str, *,
             due_date: Optional[str] = None, number: str = "", ap_account: str = "2000",
             user: str = "system") -> dict:
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("bill amount must be positive")
    vendor = conn.execute("SELECT * FROM vendor WHERE id=?", (vendor_id,)).fetchone()
    if not vendor:
        raise ValueError("unknown vendor")
    if not due_date:
        due_date = (date.fromisoformat(bill_date[:10]) + timedelta(days=vendor["terms_days"] or 30)).isoformat()
    exp = coa.by_number(conn, expense_account) or coa.get_account(conn, expense_account)
    ap = coa.by_number(conn, ap_account)
    je = gl.create_entry(conn, bill_date,
                         [{"account_id": exp["id"], "debit": amount},
                          {"account_id": ap["id"], "credit": amount}],
                         memo=f"Bill {number or ''} from {vendor['name']}".strip(), source="ap")
    cur = conn.execute(
        "INSERT INTO bill (vendor_id,number,bill_date,due_date,amount,expense_account_id,ap_account_id,status,paid,je_id,created_at) "
        "VALUES (?,?,?,?,?,?,?, 'open', 0, ?, ?)",
        (vendor_id, number, bill_date, due_date, amount, exp["id"], ap["id"], je["id"], now_iso()))
    conn.commit()
    audit(conn, entity="bill", entity_id=cur.lastrowid, action="create",
          new={"vendor": vendor["name"], "amount": amount, "due": due_date}, user=user)
    conn.commit()
    return get_bill(conn, cur.lastrowid)


def get_bill(conn, bill_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM bill WHERE id=?", (bill_id,)).fetchone()
    return dict(r) if r else None


def pay_bill(conn, bill_id: int, amount: float, pay_date: str, *, cash_account: str = "1000",
             user: str = "system") -> dict:
    bill = get_bill(conn, bill_id)
    if not bill:
        raise ValueError("unknown bill")
    amount = round(float(amount), 2)
    cash = coa.by_number(conn, cash_account)
    gl.create_entry(conn, pay_date,
                    [{"account_id": bill["ap_account_id"], "debit": amount},
                     {"account_id": cash["id"], "credit": amount}],
                    memo=f"Payment on bill #{bill_id}", source="ap")
    paid = round(bill["paid"] + amount, 2)
    status = "paid" if paid + 0.005 >= bill["amount"] else "partial"
    conn.execute("UPDATE bill SET paid=?, status=? WHERE id=?", (paid, status, bill_id))
    audit(conn, entity="bill", entity_id=bill_id, action="payment",
          old={"paid": bill["paid"]}, new={"paid": paid, "status": status}, user=user)
    conn.commit()
    return get_bill(conn, bill_id)


def _buckets(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def aging(conn, as_of: Optional[str] = None) -> dict:
    as_of_d = date.fromisoformat((as_of or date.today().isoformat())[:10])
    buckets = {"current": 0.0, "1-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    rows = []
    for b in conn.execute("SELECT b.*, v.name AS vendor FROM bill b JOIN vendor v ON v.id=b.vendor_id "
                          "WHERE b.status != 'paid'"):
        bal = round(b["amount"] - b["paid"], 2)
        if bal <= 0:
            continue
        overdue = (as_of_d - date.fromisoformat(b["due_date"][:10])).days if b["due_date"] else 0
        bucket = _buckets(overdue)
        buckets[bucket] = round(buckets[bucket] + bal, 2)
        rows.append({"bill_id": b["id"], "vendor": b["vendor"], "balance": bal,
                     "due_date": b["due_date"], "bucket": bucket})
    return {"as_of": as_of_d.isoformat(), "buckets": buckets,
            "total": round(sum(buckets.values()), 2), "bills": rows}


def cash_requirements(conn, weeks: int = 4, as_of: Optional[str] = None) -> dict:
    as_of_d = date.fromisoformat((as_of or date.today().isoformat())[:10])
    horizon = as_of_d + timedelta(weeks=weeks)
    due = []
    for b in conn.execute("SELECT b.*, v.name AS vendor FROM bill b JOIN vendor v ON v.id=b.vendor_id "
                          "WHERE b.status != 'paid'"):
        bal = round(b["amount"] - b["paid"], 2)
        if bal > 0 and b["due_date"] and b["due_date"][:10] <= horizon.isoformat():
            due.append({"vendor": b["vendor"], "balance": bal, "due_date": b["due_date"]})
    return {"weeks": weeks, "total_due": round(sum(d["balance"] for d in due), 2), "bills": due}


def vendor_1099_totals(conn, year: int) -> dict:
    """Total paid to 1099 vendors in a year (from AP payment JEs)."""
    out = []
    for v in conn.execute("SELECT * FROM vendor WHERE is_1099=1"):
        total = 0.0
        for b in conn.execute("SELECT * FROM bill WHERE vendor_id=?", (v["id"],)):
            # Payments are AP debits on this bill's AP account in the year.
            r = conn.execute(
                "SELECT COALESCE(SUM(jl.debit),0) d FROM journal_line jl JOIN journal_entry je ON je.id=jl.entry_id "
                "WHERE je.status='posted' AND je.source='ap' AND jl.account_id=? AND je.date LIKE ? "
                "AND je.memo LIKE ?", (b["ap_account_id"], f"{year}%", f"%bill #{b['id']}%")).fetchone()
            total += r["d"]
        if total > 0:
            out.append({"vendor": v["name"], "tin": v["tin"], "total_paid": round(total, 2),
                        "reportable": total >= 600})
    return {"year": year, "vendors": out}
