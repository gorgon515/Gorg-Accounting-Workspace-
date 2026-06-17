"""Chart of Accounts: account CRUD, normal-balance rules, and firm templates."""
from __future__ import annotations

import sqlite3
from typing import Optional

from .db import audit, now_iso

# Normal balance by type: assets & expenses are debit-normal; the rest credit-normal.
DEBIT_NORMAL = {"asset", "expense"}


def normal_balance(account_type: str) -> str:
    return "debit" if account_type in DEBIT_NORMAL else "credit"


def signed_balance(account_type: str, debits: float, credits: float) -> float:
    """Balance in the account's natural sign (positive = normal side)."""
    return round(debits - credits, 2) if account_type in DEBIT_NORMAL else round(credits - debits, 2)


# ---- templates: (number, name, type, subtype, is_cash, cashflow_section) ----
_BASE = [
    ("1000", "Cash - Operating", "asset", "cash", 1, "operating"),
    ("1010", "Cash - Savings", "asset", "cash", 1, "operating"),
    ("1200", "Accounts Receivable", "asset", "ar", 0, "operating"),
    ("1500", "Fixed Assets", "asset", "ppe", 0, "investing"),
    ("1510", "Accumulated Depreciation", "asset", "contra", 0, "investing"),
    ("2000", "Accounts Payable", "liability", "ap", 0, "operating"),
    ("2100", "Accrued Liabilities", "liability", None, 0, "operating"),
    ("2500", "Notes Payable", "liability", "debt", 0, "financing"),
    ("3000", "Owner's Equity", "equity", None, 0, "financing"),
    ("3900", "Retained Earnings", "equity", "retained", 0, "financing"),
    ("4000", "Service Revenue", "revenue", None, 0, "operating"),
    ("5000", "Salaries & Wages", "expense", None, 0, "operating"),
    ("5100", "Rent Expense", "expense", None, 0, "operating"),
    ("5200", "Office Expense", "expense", None, 0, "operating"),
    ("5300", "Depreciation Expense", "expense", None, 0, "operating"),
    ("5400", "Professional Fees", "expense", None, 0, "operating"),
]

TEMPLATES = {
    "general_small_business": _BASE,
    "service_business": _BASE + [("4100", "Product Revenue", "revenue", None, 0, "operating")],
    "professional_firm": _BASE + [("4050", "Consulting Revenue", "revenue", None, 0, "operating"),
                                  ("5500", "Continuing Education", "expense", None, 0, "operating")],
    "consulting_firm": _BASE + [("4050", "Consulting Revenue", "revenue", None, 0, "operating"),
                                ("5600", "Subcontractor Costs", "expense", None, 0, "operating")],
    "tax_firm": _BASE + [("4060", "Tax Preparation Revenue", "revenue", None, 0, "operating"),
                         ("4070", "Advisory Revenue", "revenue", None, 0, "operating"),
                         ("5700", "Software & Research", "expense", None, 0, "operating")],
}


def create_account(conn: sqlite3.Connection, number: str, name: str, type: str, *,
                   subtype: Optional[str] = None, parent_id: Optional[int] = None,
                   cash: bool = False, cashflow: Optional[str] = None, user: str = "system") -> dict:
    if type not in ("asset", "liability", "equity", "revenue", "expense"):
        raise ValueError("invalid account type")
    cur = conn.execute(
        "INSERT INTO account (number,name,type,subtype,parent_id,active,cash,cashflow,created_at) "
        "VALUES (?,?,?,?,?,1,?,?,?)",
        (number, name, type, subtype, parent_id, 1 if cash else 0, cashflow, now_iso()))
    conn.commit()
    audit(conn, entity="account", entity_id=cur.lastrowid, action="create",
          new={"number": number, "name": name, "type": type}, user=user)
    conn.commit()
    return get_account(conn, cur.lastrowid)


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM account WHERE id=?", (account_id,)).fetchone()
    return dict(r) if r else None


def by_number(conn: sqlite3.Connection, number: str) -> Optional[dict]:
    r = conn.execute("SELECT * FROM account WHERE number=?", (number,)).fetchone()
    return dict(r) if r else None


def list_accounts(conn: sqlite3.Connection, active_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM account" + (" WHERE active=1" if active_only else "") + " ORDER BY number"
    return [dict(r) for r in conn.execute(sql)]


def set_active(conn: sqlite3.Connection, account_id: int, active: bool, user: str = "system") -> dict:
    old = get_account(conn, account_id)
    conn.execute("UPDATE account SET active=? WHERE id=?", (1 if active else 0, account_id))
    audit(conn, entity="account", entity_id=account_id, action="set_active",
          old={"active": bool(old["active"])}, new={"active": active}, user=user)
    conn.commit()
    return get_account(conn, account_id)


def seed_template(conn: sqlite3.Connection, template: str = "general_small_business", user: str = "system") -> dict:
    if template not in TEMPLATES:
        raise ValueError(f"unknown template; choose from {list(TEMPLATES)}")
    created = 0
    for number, name, type_, subtype, is_cash, cashflow in TEMPLATES[template]:
        if not by_number(conn, number):
            create_account(conn, number, name, type_, subtype=subtype, cash=bool(is_cash),
                           cashflow=cashflow, user=user)
            created += 1
    return {"template": template, "created": created, "total": len(list_accounts(conn))}
