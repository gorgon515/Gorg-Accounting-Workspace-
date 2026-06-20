"""Idea Ranking System + Anti-MAG7 Diversification Logic.

Computes a composite score for every security from weighted factors
(Valuation, Quality, Growth, Momentum, Financial strength, Earnings revisions,
Sector tailwinds), then applies discovery-oriented penalties so mega-cap,
over-covered, and already-owned names are pushed down. The MAG7 are not in the
seed universe at all, but the same penalties would demote them if ingested.
"""
from __future__ import annotations
from typing import Optional

from .scanner import OpportunityScanner, _score_higher_better, _score_lower_better, _clip

# Per-sector tailwind adjustment (points added to the composite, -5..+5 range).
_SECTOR_TAILWINDS = {
    "Information Technology": 4.0,
    "Healthcare": 3.0,
    "Industrials": 2.0,
    "Communication Services": 1.0,
    "Financials": 1.0,
    "Energy": 0.0,
    "Consumer Staples": 0.0,
    "Consumer Discretionary": -1.0,
    "Materials": -2.0,
    "Utilities": -2.0,
    "Real Estate": -2.0,
}

# Symbols that would be considered "mega-cap concentration" risks if present.
MAG7 = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"}

# Factor weights (sum to 1.0).
_FACTOR_WEIGHTS = {
    "valuation": 0.20,
    "quality": 0.20,
    "growth": 0.18,
    "momentum": 0.12,
    "financial_strength": 0.15,
    "earnings_revisions": 0.10,
    "sector_tailwind": 0.05,
}


class IdeaRanker:
    def __init__(self, universe, scanner: Optional[OpportunityScanner] = None):
        self.universe = universe
        self.scanner = scanner or OpportunityScanner(universe)

    # ── factor scores (0-100) ────────────────────────────────────────────────
    def _factors(self, s: dict) -> dict:
        val, _, _ = self.scanner._value(s)
        qual, _, _ = self.scanner._quality(s)
        grow, _, _ = self.scanner._growth(s)

        # Momentum proxy: revenue + eps acceleration (no price feed needed).
        rg1, rg2 = self.scanner._series_deltas(s.get("revenue_3y", []))
        eg1, eg2 = self.scanner._series_deltas(s.get("eps_3y", []))
        momentum = _clip(
            0.5 * _score_higher_better(rg2 - rg1, bad=-0.05, good=0.10)
            + 0.5 * _score_higher_better(eg2 - eg1, bad=-0.05, good=0.15)
        )

        # Financial strength: low leverage + positive FCF.
        equity = s.get("equity", 0) or 0.0
        d2e = (s.get("total_debt", 0) / equity) if equity > 0 else 5.0
        lev = _score_lower_better(d2e, good=0.2, bad=2.5)
        fcf_pos = _score_higher_better(s.get("fcf_yield", 0), bad=-0.02, good=0.08)
        financial_strength = _clip(0.6 * lev + 0.4 * fcf_pos)

        # Earnings revisions proxy: current earnings_growth vs prior-year eps delta.
        prior = eg1
        revision = _score_higher_better(s.get("earnings_growth", 0) - prior,
                                        bad=-0.10, good=0.20)

        # Sector tailwind mapped to 0-100 (center 50).
        tail_pts = _SECTOR_TAILWINDS.get(s.get("sector", ""), 0.0)
        sector_tailwind = _clip(50.0 + tail_pts * 10.0)

        return {
            "valuation": round(val, 1),
            "quality": round(qual, 1),
            "growth": round(grow, 1),
            "momentum": round(momentum, 1),
            "financial_strength": round(financial_strength, 1),
            "earnings_revisions": round(revision, 1),
            "sector_tailwind": round(sector_tailwind, 1),
        }

    # ── penalties (0-100 points subtracted) ──────────────────────────────────
    def _penalties(self, s: dict, exclude_mega_cap: bool, penalize_coverage: bool,
                   portfolio_overlap: set) -> dict:
        mc = s.get("market_cap", 0) or 0.0
        # Mega-cap concentration penalty: scales above $200B, capped.
        mega_pen = 0.0
        if mc > 200000:
            mega_pen = min(40.0, (mc - 200000) / 50000 * 10.0 + 10.0)
        elif mc > 100000:
            mega_pen = (mc - 100000) / 100000 * 8.0
        if s["symbol"] in MAG7:
            mega_pen = max(mega_pen, 50.0)
        if exclude_mega_cap and (mc > 100000 or s["symbol"] in MAG7):
            mega_pen = max(mega_pen, 100.0)  # effectively excluded

        # Over-covered penalty: scales with analyst coverage.
        coverage_pen = 0.0
        if penalize_coverage:
            cov = s.get("analyst_coverage", 0) or 0
            coverage_pen = min(20.0, max(0.0, (cov - 12) * 1.5))

        # Existing-portfolio-overlap penalty: heavily demote owned names.
        overlap_pen = 60.0 if s["symbol"] in portfolio_overlap else 0.0

        return {
            "mega_cap": round(mega_pen, 1),
            "coverage": round(coverage_pen, 1),
            "portfolio_overlap": round(overlap_pen, 1),
        }

    def rank(self, limit: int = 100, exclude_mega_cap: bool = False,
             penalize_coverage: bool = True,
             portfolio_overlap: Optional[list[str]] = None) -> list[dict]:
        overlap = set(portfolio_overlap or [])
        out = []
        for s in self.universe.all():
            factors = self._factors(s)
            base = sum(factors[k] * w for k, w in _FACTOR_WEIGHTS.items())
            penalties = self._penalties(s, exclude_mega_cap, penalize_coverage, overlap)
            total_pen = sum(penalties.values())
            composite = _clip(base - total_pen)
            # Hard-exclude overlap / forced-excluded mega caps from the list.
            if s["symbol"] in overlap:
                continue
            if exclude_mega_cap and penalties["mega_cap"] >= 100.0:
                continue
            out.append({
                "symbol": s["symbol"], "name": s["name"], "sector": s["sector"],
                "cap_tier": self.universe.cap_tier(s.get("market_cap", 0)),
                "composite": round(composite, 1),
                "factors": factors, "penalties": penalties,
            })
        out.sort(key=lambda x: x["composite"], reverse=True)
        return out[: max(0, int(limit))]

    def ideas(self, tier: str = "top25") -> list[dict]:
        sizes = {"top10": 10, "top25": 25, "top50": 50, "top100": 100}
        if tier not in sizes:
            raise ValueError(f"unknown tier: {tier} (expected one of {sorted(sizes)})")
        return self.rank(limit=sizes[tier])
