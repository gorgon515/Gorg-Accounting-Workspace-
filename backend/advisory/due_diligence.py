"""Due Diligence Engine — concentration, working capital, quality of earnings,
ratio review, and risk identification → a diligence report. Built on the platform.
"""
from __future__ import annotations

from . import fs_analysis
from accounting_platform import ar, statements


def _concentration(amounts_by_name: dict) -> dict:
    total = sum(amounts_by_name.values())
    if total <= 0:
        return {"total": 0.0, "top": None, "top_share": None, "hhi": None, "detail": {}}
    shares = {k: round(v / total, 4) for k, v in amounts_by_name.items()}
    top = max(shares, key=shares.get)
    hhi = round(sum(s * s for s in shares.values()), 4)
    return {"total": round(total, 2), "top": top, "top_share": shares[top], "hhi": hhi,
            "detail": dict(sorted(shares.items(), key=lambda kv: -kv[1]))}


def _vendor_concentration(conn) -> dict:
    by_vendor = {}
    for b in conn.execute("SELECT v.name AS vendor, b.amount FROM bill b JOIN vendor v ON v.id=b.vendor_id"):
        by_vendor[b["vendor"]] = round(by_vendor.get(b["vendor"], 0.0) + b["amount"], 2)
    return _concentration(by_vendor)


def report(conn, year: int, as_of: str = None) -> dict:
    as_of = as_of or f"{year}-12-31"
    fsa = fs_analysis.analyze(conn, as_of, year)
    rev = ar.revenue_analytics(conn, year)
    customer_conc = _concentration(rev["by_customer"])
    vendor_conc = _vendor_concentration(conn)
    cf = statements.cash_flow(conn, f"{year}-01-01", as_of)
    inc = statements.income_statement(conn, f"{year}-01-01", as_of)

    qoe = {"net_income": inc["net_income"], "operating_cash_flow": cf["operating_activities"],
           "cf_to_ni": fsa["ratios"]["cash_flow_quality"]["operating_cf_to_net_income"]}

    risks = list(fsa["flags"])
    if customer_conc["top_share"] and customer_conc["top_share"] > 0.30:
        risks.append(f"Customer concentration: {customer_conc['top']} is "
                     f"{customer_conc['top_share']*100:.0f}% of revenue.")
    if vendor_conc["top_share"] and vendor_conc["top_share"] > 0.30:
        risks.append(f"Vendor concentration: {vendor_conc['top']} is "
                     f"{vendor_conc['top_share']*100:.0f}% of spend.")
    if fsa["ratios"]["liquidity"]["working_capital"] < 0:
        risks.append("Negative working capital.")

    return {
        "year": year, "as_of": as_of,
        "ratios": fsa["ratios"],
        "revenue_concentration": customer_conc,
        "customer_concentration": customer_conc,
        "vendor_concentration": vendor_conc,
        "working_capital": fsa["ratios"]["liquidity"]["working_capital"],
        "quality_of_earnings": qoe,
        "risks": risks,
        "summary": (f"Diligence for {year}: revenue {inc['total_revenue']:,.0f}, "
                    f"top customer {(customer_conc['top_share'] or 0)*100:.0f}% of revenue, "
                    f"{len(risks)} risk flag(s)."),
    }
