"""Portfolio Candidate Builder.

Assembles advisory candidate baskets for five styles (conservative, growth,
value, dividend, small_cap). Each style ranks the universe with a style-specific
score, selects the top N, and assigns score-proportional weights that sum to
~1.0. All advisory — these are idea baskets, not orders.
"""
from __future__ import annotations
from typing import Optional

from .scanner import OpportunityScanner, _score_higher_better, _score_lower_better, _clip


class CandidateBuilder:
    def __init__(self, universe, scanner: Optional[OpportunityScanner] = None):
        self.universe = universe
        self.scanner = scanner or OpportunityScanner(universe)

    _STYLES = {
        "conservative": "Low-volatility quality & dividend tilt — stable, cash-generative leaders.",
        "growth": "Accelerating revenue and earnings with expanding margins.",
        "value": "Cheap on earnings, EV/EBITDA, and free cash flow.",
        "dividend": "Highest sustainable dividend yields with payout sanity checks.",
        "small_cap": "Quality small- and micro-cap names below $2B market cap.",
    }

    def styles(self) -> list[dict]:
        return [{"id": k, "description": v} for k, v in self._STYLES.items()]

    # ── per-style scoring ────────────────────────────────────────────────────
    def _score(self, style: str, s: dict):
        if style == "conservative":
            qual, _, _ = self.scanner._quality(s)
            div = _score_higher_better(s.get("dividend_yield", 0), bad=0.0, good=0.05)
            # low-vol proxy: large, profitable, low leverage
            equity = s.get("equity", 0) or 0.0
            d2e = (s.get("total_debt", 0) / equity) if equity > 0 else 5.0
            stability = _score_lower_better(d2e, good=0.3, bad=2.5)
            score = 0.45 * qual + 0.30 * stability + 0.25 * div
            reason = f"Quality {qual:.0f}/100, {s['dividend_yield'] * 100:.1f}% yield, low leverage."
            return score, reason
        if style == "growth":
            score, _, r = self.scanner._growth(s)
            return score, r
        if style == "value":
            score, _, r = self.scanner._value(s)
            return score, r
        if style == "dividend":
            dy = s.get("dividend_yield", 0) or 0.0
            div = _score_higher_better(dy, bad=0.0, good=0.07)
            # payout sanity: must be profitable and FCF-covered
            payout_ok = 1.0 if (s.get("net_income", 0) > 0 and s.get("fcf", 0) > 0) else 0.3
            qual, _, _ = self.scanner._quality(s)
            score = (0.65 * div + 0.35 * qual) * payout_ok
            reason = f"{dy * 100:.1f}% dividend yield, {'FCF-covered' if payout_ok == 1.0 else 'coverage caution'}."
            return score, reason
        if style == "small_cap":
            qual, _, _ = self.scanner._quality(s)
            grow, _, _ = self.scanner._growth(s)
            score = 0.5 * qual + 0.5 * grow
            reason = f"Quality {qual:.0f} / growth {grow:.0f} small-cap."
            return score, reason
        raise ValueError(f"unknown style: {style}")

    def _eligible(self, style: str, s: dict) -> bool:
        tier = self.universe.cap_tier(s.get("market_cap", 0))
        if style == "small_cap":
            return tier in ("micro", "small")
        if style == "dividend":
            return (s.get("dividend_yield", 0) or 0.0) > 0.0
        if style == "conservative":
            # avoid unprofitable / negative-equity names
            return s.get("net_income", 0) > 0
        return True

    def build(self, style: str, size: int = 10) -> dict:
        if style not in self._STYLES:
            raise ValueError(f"unknown style: {style} (expected one of {sorted(self._STYLES)})")
        size = max(1, int(size))
        scored = []
        for s in self.universe.all():
            if not self._eligible(style, s):
                continue
            score, reason = self._score(style, s)
            scored.append((score, s, reason))
        scored.sort(key=lambda x: x[0], reverse=True)
        chosen = scored[:size]

        total = sum(max(sc, 0.01) for sc, _, _ in chosen) or 1.0
        holdings = []
        for sc, s, reason in chosen:
            weight = max(sc, 0.01) / total
            holdings.append({
                "symbol": s["symbol"], "name": s["name"], "sector": s["sector"],
                "weight": round(weight, 4), "reason": reason,
            })
        # Normalize any rounding drift so weights sum to exactly 1.0.
        if holdings:
            drift = round(1.0 - sum(h["weight"] for h in holdings), 4)
            holdings[0]["weight"] = round(holdings[0]["weight"] + drift, 4)

        notes = (f"Advisory {style} candidate basket of {len(holdings)} names, "
                 f"score-weighted. Not investment advice; review before acting.")
        return {"style": style, "holdings": holdings, "notes": notes}


_instance = None
