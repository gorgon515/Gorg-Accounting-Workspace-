"""Data import — CSV journal entries, vendors, customers, and bank transactions.

Journal CSV rows are grouped by a 'ref' column into balanced entries before
posting, so imports go through the same double-entry validation as manual entries.
"""
from __future__ import annotations

import csv
import io

from . import ap, ar, bank_rec, gl


def import_journal_csv(conn, text: str, *, default_date: str = None, post: bool = True, user: str = "system") -> dict:
    """Columns: ref,date,account,debit,credit,memo  — rows sharing a ref form one entry."""
    reader = csv.DictReader(io.StringIO(text))
    groups: dict[str, list] = {}
    meta: dict[str, dict] = {}
    for row in reader:
        r = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        ref = r.get("ref") or r.get("date") or "1"
        groups.setdefault(ref, []).append({
            "account": r.get("account"),
            "debit": float(r["debit"]) if r.get("debit") else 0,
            "credit": float(r["credit"]) if r.get("credit") else 0,
            "memo": r.get("memo", ""),
        })
        meta.setdefault(ref, {"date": r.get("date") or default_date, "memo": r.get("memo", "")})
    created, errors = [], []
    for ref, lines in groups.items():
        try:
            e = gl.create_entry(conn, meta[ref]["date"], lines, memo=meta[ref]["memo"],
                                source="import", user=user, post=post)
            created.append(e["id"])
        except ValueError as exc:
            errors.append({"ref": ref, "error": str(exc)})
    return {"entries_created": len(created), "entry_ids": created, "errors": errors}


def import_vendors_csv(conn, text: str, user: str = "system") -> dict:
    reader = csv.DictReader(io.StringIO(text))
    n = 0
    for row in reader:
        r = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if r.get("name"):
            ap.add_vendor(conn, r["name"], email=r.get("email", ""),
                          terms_days=int(r.get("terms_days") or 30),
                          is_1099=str(r.get("is_1099", "")).lower() in ("1", "true", "yes"),
                          tin=r.get("tin", ""), user=user)
            n += 1
    return {"vendors_imported": n}


def import_customers_csv(conn, text: str, user: str = "system") -> dict:
    reader = csv.DictReader(io.StringIO(text))
    n = 0
    for row in reader:
        r = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if r.get("name"):
            ar.add_customer(conn, r["name"], email=r.get("email", ""),
                            terms_days=int(r.get("terms_days") or 30), user=user)
            n += 1
    return {"customers_imported": n}


def import_bank_csv(conn, account_id: int, text: str) -> dict:
    return bank_rec.import_transactions(conn, account_id, bank_rec.parse_csv(text))
