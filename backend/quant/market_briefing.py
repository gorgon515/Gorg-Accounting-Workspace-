"""Daily market-briefing generator — computed from real quote data.

Synthesizes a market overview, sector rotation, top movers, portfolio risks, and
research opportunities from a list of quotes. Earnings/macro events are included
only when supplied by the caller (never invented).
"""
from __future__ import annotations

from statistics import mean
from typing import Optional

from app.services import risk


def _chg(q: dict) -> Optional[float]:
    v = q.get("changePercent", q.get("change_percent"))
    return float(v) if isinstance(v, (int, float)) else None


def generate_market_briefing(quotes: list[dict], *, portfolio: Optional[list[dict]] = None,
                             watchlist_changes: Optional[list[str]] = None,
                             earnings: Optional[list[dict]] = None,
                             macro: Optional[list[dict]] = None) -> dict:
    valid = [q for q in quotes if _chg(q) is not None]
    changes = [_chg(q) for q in valid]
    up = sum(1 for c in changes if c > 0)
    down = sum(1 for c in changes if c < 0)

    ranked = sorted(valid, key=lambda q: _chg(q), reverse=True)
    gainers = [{"symbol": q.get("symbol"), "change_percent": round(_chg(q), 2)} for q in ranked[:5]]
    losers = [{"symbol": q.get("symbol"), "change_percent": round(_chg(q), 2)} for q in ranked[-5:][::-1]]

    # Sector rotation (only if quotes carry a sector).
    sectors: dict[str, list[float]] = {}
    for q in valid:
        sec = q.get("sector")
        if sec:
            sectors.setdefault(sec, []).append(_chg(q))
    sector_rotation = sorted(
        ({"sector": s, "avg_change_percent": round(mean(v), 2), "names": len(v)} for s, v in sectors.items()),
        key=lambda x: x["avg_change_percent"], reverse=True,
    )

    overview = {
        "names": len(valid),
        "advancers": up,
        "decliners": down,
        "breadth": round((up - down) / len(valid), 3) if valid else None,
        "avg_change_percent": round(mean(changes), 2) if changes else None,
        "tone": ("risk-on" if up > down * 1.5 else "risk-off" if down > up * 1.5 else "mixed") if valid else "no data",
    }

    portfolio_risks = None
    if portfolio:
        try:
            rep = risk.portfolio_report([{"symbol": p.get("symbol"), "value": p.get("value", p.get("weight", 0)),
                                          "sector": p.get("sector")} for p in portfolio])
            portfolio_risks = {
                "concentration_hhi": rep["concentration_hhi"],
                "largest_position": rep["largest_position"],
                "top_sector": next(iter(rep["sector_exposure"].items()), None),
            }
        except ValueError:
            portfolio_risks = None

    opportunities = [
        {"symbol": g["symbol"], "note": f"Leading the tape (+{g['change_percent']}%) — flagged for research, not a recommendation."}
        for g in gainers if g["change_percent"] > 0
    ][:3]

    return {
        "market_overview": overview,
        "sector_rotation": sector_rotation,
        "top_movers": {"gainers": gainers, "losers": losers},
        "earnings_events": earnings or [],
        "macro_events": macro or [],
        "watchlist_changes": watchlist_changes or [],
        "portfolio_risks": portfolio_risks,
        "opportunities": opportunities,
        "disclaimer": "Computed from supplied quotes. Opportunities are research flags, not advice.",
    }
