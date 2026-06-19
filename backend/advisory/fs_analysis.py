"""Financial Statement Analysis — liquidity, profitability, leverage, efficiency,
growth, cash-flow & earnings quality, plus executive/management/board summaries.
Computed from the accounting-platform statements.
"""
from __future__ import annotations

from typing import Optional

from accounting_platform import coa, gl, statements


def _safe(n, d):
    return round(n / d, 4) if d else None


def _current_assets_liabilities(conn, as_of):
    ca = cl = 0.0
    for a in coa.list_accounts(conn):
        bal = gl.account_balance(conn, a["id"], as_of)["balance"]
        if a["type"] == "asset" and a["subtype"] in ("cash", "ar"):
            ca += bal
        if a["type"] == "liability" and a["subtype"] in ("ap", None):  # AP + accrued ≈ current
            cl += bal
    return round(ca, 2), round(cl, 2)


def analyze(conn, as_of: str, year: Optional[int] = None) -> dict:
    year = year or int(as_of[:4])
    bs = statements.balance_sheet(conn, as_of)
    inc = statements.income_statement(conn, f"{year}-01-01", as_of)
    cf = statements.cash_flow(conn, f"{year}-01-01", as_of)
    ca, cl = _current_assets_liabilities(conn, as_of)

    assets = bs["total_assets"]
    equity = bs["total_equity"]
    liab = bs["total_liabilities"]
    rev = inc["total_revenue"]
    ni = inc["net_income"]
    ocf = cf["operating_activities"]
    ar = next((a["balance"] for a in bs["assets"] if "Receivable" in a["name"]), 0.0)

    ratios = {
        "liquidity": {"current_ratio": _safe(ca, cl), "working_capital": round(ca - cl, 2)},
        "profitability": {"net_margin": _safe(ni, rev), "return_on_assets": _safe(ni, assets),
                          "return_on_equity": _safe(ni, equity)},
        "leverage": {"debt_to_equity": _safe(liab, equity), "debt_ratio": _safe(liab, assets)},
        "efficiency": {"asset_turnover": _safe(rev, assets), "receivables_turnover": _safe(rev, ar) if ar else None},
        "cash_flow_quality": {"operating_cf_to_net_income": _safe(ocf, ni)},
        "earnings_quality": {"accruals_ratio": _safe(ni - ocf, assets)},
    }

    flags = []
    if ratios["liquidity"]["current_ratio"] is not None and ratios["liquidity"]["current_ratio"] < 1:
        flags.append("Current ratio below 1.0 — potential liquidity pressure.")
    if ratios["cash_flow_quality"]["operating_cf_to_net_income"] is not None and \
            ratios["cash_flow_quality"]["operating_cf_to_net_income"] < 0.8 and ni > 0:
        flags.append("Operating cash flow lags net income — earnings-quality concern.")
    if ratios["leverage"]["debt_to_equity"] is not None and ratios["leverage"]["debt_to_equity"] > 2:
        flags.append("High leverage (D/E > 2).")

    exec_summary = (f"Revenue {rev:,.0f}, net income {ni:,.0f} "
                    f"(margin {(_safe(ni, rev) or 0)*100:.1f}%). "
                    f"Liquidity: current ratio {ratios['liquidity']['current_ratio']}. "
                    + ("Flags: " + "; ".join(flags) if flags else "No major flags."))
    return {
        "as_of": as_of, "ratios": ratios, "flags": flags,
        "summaries": {
            "executive": exec_summary,
            "management": {"revenue": rev, "net_income": ni, "operating_cash_flow": ocf,
                           "total_assets": assets, "equity": equity, "ratios": ratios},
            "board": f"Net income {ni:,.0f} on revenue {rev:,.0f}; "
                     f"{'healthy' if not flags else str(len(flags)) + ' risk flag(s)'}.",
        },
    }
