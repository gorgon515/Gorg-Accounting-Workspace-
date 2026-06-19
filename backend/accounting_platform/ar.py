"""Accounts Receivable — customers, invoices, payments, aging, analytics.

Invoices and payments post real journal entries (Dr AR / Cr revenue on an
invoice; Dr cash / Cr AR on payment), so AR ties to the GL and statements.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from . import coa, gl
from .db import audit, now_iso
from .ap import _buckets


def add_customer(conn, name: str, *, email: str = "", terms_days: int = 30, user: str = "system") -> dict:
    cur = conn.execute("INSERT INTO customer (name,email,terms_days,created_at) VALUES (?,?,?,?)",
                       (name, email, terms_days, now_iso()))
    conn.commit()
    audit(conn, entity="customer", entity_id=cur.lastrowid, action="create", new={"name": name}, user=user)
    conn.commit()
    return dict(conn.execute("SELECT * FROM customer WHERE id=?", (cur.lastrowid,)).fetchone())


def list_customers(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM customer ORDER BY name")]


def add_invoice(conn, customer_id: int, amount: float, invoice_date: str, *,
                revenue_account: str = "4000", ar_account: str = "1200",
                due_date: Optional[str] = None, number: str = "", user: str = "system") -> dict:
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("invoice amount must be positive")
    cust = conn.execute("SELECT * FROM customer WHERE id=?", (customer_id,)).fetchone()
    if not cust:
        raise ValueError("unknown customer")
    if not due_date:
        due_date = (date.fromisoformat(invoice_date[:10]) + timedelta(days=cust["terms_days"] or 30)).isoformat()
    rev = coa.by_number(conn, revenue_account)
    ar = coa.by_number(conn, ar_account)
    je = gl.create_entry(conn, invoice_date,
                         [{"account_id": ar["id"], "debit": amount},
                          {"account_id": rev["id"], "credit": amount}],
                         memo=f"Invoice {number or ''} to {cust['name']}".strip(), source="ar")
    cur = conn.execute(
        "INSERT INTO ar_invoice (customer_id,number,invoice_date,due_date,amount,revenue_account_id,ar_account_id,status,paid,je_id,created_at) "
        "VALUES (?,?,?,?,?,?,?, 'open', 0, ?, ?)",
        (customer_id, number, invoice_date, due_date, amount, rev["id"], ar["id"], je["id"], now_iso()))
    conn.commit()
    audit(conn, entity="ar_invoice", entity_id=cur.lastrowid, action="create",
          new={"customer": cust["name"], "amount": amount, "due": due_date}, user=user)
    conn.commit()
    return get_invoice(conn, cur.lastrowid)


def get_invoice(conn, invoice_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM ar_invoice WHERE id=?", (invoice_id,)).fetchone()
    return dict(r) if r else None


def record_payment(conn, invoice_id: int, amount: float, pay_date: str, *,
                   cash_account: str = "1000", user: str = "system") -> dict:
    inv = get_invoice(conn, invoice_id)
    if not inv:
        raise ValueError("unknown invoice")
    amount = round(float(amount), 2)
    cash = coa.by_number(conn, cash_account)
    gl.create_entry(conn, pay_date,
                    [{"account_id": cash["id"], "debit": amount},
                     {"account_id": inv["ar_account_id"], "credit": amount}],
                    memo=f"Payment on invoice #{invoice_id}", source="ar")
    paid = round(inv["paid"] + amount, 2)
    status = "paid" if paid + 0.005 >= inv["amount"] else "partial"
    conn.execute("UPDATE ar_invoice SET paid=?, status=? WHERE id=?", (paid, status, invoice_id))
    audit(conn, entity="ar_invoice", entity_id=invoice_id, action="payment",
          old={"paid": inv["paid"]}, new={"paid": paid, "status": status}, user=user)
    conn.commit()
    return get_invoice(conn, invoice_id)


def aging(conn, as_of: Optional[str] = None) -> dict:
    as_of_d = date.fromisoformat((as_of or date.today().isoformat())[:10])
    buckets = {"current": 0.0, "1-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    rows = []
    for i in conn.execute("SELECT inv.*, c.name AS customer FROM ar_invoice inv "
                          "JOIN customer c ON c.id=inv.customer_id WHERE inv.status != 'paid'"):
        bal = round(i["amount"] - i["paid"], 2)
        if bal <= 0:
            continue
        overdue = (as_of_d - date.fromisoformat(i["due_date"][:10])).days if i["due_date"] else 0
        bucket = _buckets(overdue)
        buckets[bucket] = round(buckets[bucket] + bal, 2)
        rows.append({"invoice_id": i["id"], "customer": i["customer"], "balance": bal,
                     "due_date": i["due_date"], "bucket": bucket})
    return {"as_of": as_of_d.isoformat(), "buckets": buckets,
            "total": round(sum(buckets.values()), 2), "invoices": rows}


def outstanding(conn) -> dict:
    rows = aging(conn)["invoices"]
    return {"count": len(rows), "total": round(sum(r["balance"] for r in rows), 2), "invoices": rows}


def revenue_analytics(conn, year: int) -> dict:
    by_customer = {}
    for i in conn.execute("SELECT inv.amount, c.name AS customer FROM ar_invoice inv "
                          "JOIN customer c ON c.id=inv.customer_id WHERE inv.invoice_date LIKE ?", (f"{year}%",)):
        by_customer[i["customer"]] = round(by_customer.get(i["customer"], 0.0) + i["amount"], 2)
    return {"year": year, "total_invoiced": round(sum(by_customer.values()), 2),
            "by_customer": dict(sorted(by_customer.items(), key=lambda kv: -kv[1]))}
