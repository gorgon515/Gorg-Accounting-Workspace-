"""Fixed Asset module — straight-line, double-declining, and units-of-production
depreciation, schedules, and GL-posting of depreciation entries."""
from __future__ import annotations

from typing import Optional

from . import coa, gl
from .db import audit, now_iso


def straight_line(cost: float, salvage: float, life_periods: int) -> list[float]:
    base = round(cost - salvage, 2)
    per = round(base / life_periods, 2)
    sched = [per] * life_periods
    sched[-1] = round(base - per * (life_periods - 1), 2)  # absorb rounding in the last period
    return sched


def double_declining(cost: float, salvage: float, life_periods: int) -> list[float]:
    rate = 2 / life_periods
    book, sched = cost, []
    for _ in range(life_periods):
        dep = round(book * rate, 2)
        if book - dep < salvage:
            dep = round(book - salvage, 2)
        dep = max(dep, 0.0)
        sched.append(dep)
        book = round(book - dep, 2)
    return sched


def units_of_production_rate(cost: float, salvage: float, units_total: float) -> float:
    return round((cost - salvage) / units_total, 6)


def add_asset(conn, name: str, acquired_on: str, cost: float, life_months: int, *,
              salvage: float = 0, method: str = "straight_line", units_total: Optional[float] = None,
              asset_account: str = "1500", expense_account: str = "5300",
              accumdep_account: str = "1510", user: str = "system") -> dict:
    if method not in ("straight_line", "double_declining", "units_of_production"):
        raise ValueError("invalid depreciation method")
    aa = coa.by_number(conn, asset_account)
    ea = coa.by_number(conn, expense_account)
    ad = coa.by_number(conn, accumdep_account)
    cur = conn.execute(
        "INSERT INTO fixed_asset (name,acquired_on,cost,salvage,life_months,method,units_total,"
        "asset_account_id,expense_account_id,accumdep_account_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (name, acquired_on, round(cost, 2), round(salvage, 2), life_months, method, units_total,
         aa["id"] if aa else None, ea["id"] if ea else None, ad["id"] if ad else None, now_iso()))
    conn.commit()
    audit(conn, entity="fixed_asset", entity_id=cur.lastrowid, action="create",
          new={"name": name, "cost": cost, "method": method}, user=user)
    conn.commit()
    return get_asset(conn, cur.lastrowid)


def get_asset(conn, asset_id: int) -> Optional[dict]:
    r = conn.execute("SELECT * FROM fixed_asset WHERE id=?", (asset_id,)).fetchone()
    return dict(r) if r else None


def list_assets(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM fixed_asset ORDER BY acquired_on")]


def depreciation_schedule(conn, asset_id: int) -> dict:
    a = get_asset(conn, asset_id)
    if not a:
        raise ValueError("unknown asset")
    base = round(a["cost"] - a["salvage"], 2)
    if a["method"] == "units_of_production":
        return {"asset": a["name"], "method": a["method"], "depreciable_base": base,
                "rate_per_unit": units_of_production_rate(a["cost"], a["salvage"], a["units_total"] or 1),
                "note": "Period depreciation = units produced × rate_per_unit."}
    amounts = (straight_line if a["method"] == "straight_line" else double_declining)(
        a["cost"], a["salvage"], a["life_months"])
    periods, accumulated = [], 0.0
    for i, dep in enumerate(amounts, 1):
        accumulated = round(accumulated + dep, 2)
        periods.append({"period": i, "depreciation": dep, "accumulated": accumulated,
                        "book_value": round(a["cost"] - accumulated, 2)})
    return {"asset": a["name"], "method": a["method"], "depreciable_base": base,
            "total_depreciation": round(sum(amounts), 2), "periods": periods}


def post_depreciation(conn, asset_id: int, amount: float, entry_date: str, user: str = "system") -> dict:
    a = get_asset(conn, asset_id)
    if not a:
        raise ValueError("unknown asset")
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("depreciation amount must be positive")
    je = gl.create_entry(conn, entry_date,
                         [{"account_id": a["expense_account_id"], "debit": amount},
                          {"account_id": a["accumdep_account_id"], "credit": amount}],
                         memo=f"Depreciation: {a['name']}", source="fixed_assets", entry_type="adjusting")
    audit(conn, entity="fixed_asset", entity_id=asset_id, action="depreciate",
          new={"amount": amount, "entry": je["id"]}, user=user)
    conn.commit()
    return {"asset_id": asset_id, "amount": amount, "entry_id": je["id"]}
