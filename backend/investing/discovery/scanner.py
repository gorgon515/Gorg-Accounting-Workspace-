"""Opportunity Scanner — strategy-based scoring of the equity universe.

Each strategy reads the stored fundamentals and produces 0-100 subscores plus a
0-100 composite. Scanners return securities ranked descending with a short
rationale string. All scoring is deterministic and derived from real
fundamentals — no random numbers, no placeholders.
"""
from __future__ import annotations
from typing import Optional

import numpy as np


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(max(lo, min(hi, x)))


def _score_lower_better(value: float, good: float, bad: float) -> float:
    """Map a metric where LOWER is better onto 0-100 (good->100, bad->0)."""
    if value is None:
        return 0.0
    if value <= 0:  # negative/zero multiples are not meaningful as "cheap"
        return 0.0
    if bad == good:
        return 50.0
    frac = (bad - value) / (bad - good)
    return _clip(frac * 100.0)


def _score_higher_better(value: float, bad: float, good: float) -> float:
    """Map a metric where HIGHER is better onto 0-100 (good->100, bad->0)."""
    if value is None:
        return 0.0
    if good == bad:
        return 50.0
    frac = (value - bad) / (good - bad)
    return _clip(frac * 100.0)


class OpportunityScanner:
    def __init__(self, universe):
        self.universe = universe

    # ── helpers ──────────────────────────────────────────────────────────────
    def _all(self) -> list[dict]:
        return self.universe.all()

    @staticmethod
    def _series_deltas(series: list[float]) -> tuple[float, float]:
        """Return (older_growth, newer_growth) from a 3-point series."""
        if not series or len(series) < 3:
            return 0.0, 0.0
        a, b, c = series[0], series[1], series[2]
        g1 = (b - a) / abs(a) if a else 0.0
        g2 = (c - b) / abs(b) if b else 0.0
        return g1, g2

    # ── strategy scorers (return (score, signals, rationale)) ────────────────
    def _value(self, s: dict):
        pe = _score_lower_better(s.get("pe", 0), good=8.0, bad=30.0)
        evb = _score_lower_better(s.get("ev_ebitda", 0), good=5.0, bad=20.0)
        pfcf = _score_lower_better(s.get("price_to_fcf", 0), good=8.0, bad=35.0)
        fcfy = _score_higher_better(s.get("fcf_yield", 0), bad=0.0, good=0.10)
        signals = {"pe": round(pe, 1), "ev_ebitda": round(evb, 1),
                   "price_to_fcf": round(pfcf, 1), "fcf_yield": round(fcfy, 1)}
        score = 0.30 * pe + 0.25 * evb + 0.20 * pfcf + 0.25 * fcfy
        rationale = (f"Trades at {s.get('pe', 0):.1f}x earnings / "
                     f"{s.get('ev_ebitda', 0):.1f}x EV/EBITDA with a "
                     f"{s.get('fcf_yield', 0) * 100:.1f}% FCF yield.")
        return _clip(score), signals, rationale

    def _growth(self, s: dict):
        rg1, rg2 = self._series_deltas(s.get("revenue_3y", []))
        eg1, eg2 = self._series_deltas(s.get("eps_3y", []))
        rev_accel = _score_higher_better(rg2 - rg1, bad=-0.05, good=0.10)
        rev_level = _score_higher_better(rg2, bad=0.0, good=0.20)
        eps_accel = _score_higher_better(eg2 - eg1, bad=-0.05, good=0.15)
        margin = _score_higher_better(s.get("operating_margin", 0), bad=0.05, good=0.30)
        signals = {"revenue_acceleration": round(rev_accel, 1),
                   "revenue_level": round(rev_level, 1),
                   "earnings_acceleration": round(eps_accel, 1),
                   "margin_quality": round(margin, 1)}
        score = 0.30 * rev_accel + 0.25 * rev_level + 0.30 * eps_accel + 0.15 * margin
        rationale = (f"Revenue growth {rg2 * 100:.1f}% (was {rg1 * 100:.1f}%), "
                     f"EPS growth {eg2 * 100:.1f}% (was {eg1 * 100:.1f}%).")
        return _clip(score), signals, rationale

    def _quality(self, s: dict):
        roic = _score_higher_better(s.get("roic", 0), bad=0.05, good=0.30)
        roe = _score_higher_better(s.get("roe", 0), bad=0.05, good=0.35)
        equity = s.get("equity", 0) or 0.0
        debt = s.get("total_debt", 0) or 0.0
        d2e = (debt / equity) if equity > 0 else 5.0
        balance = _score_lower_better(d2e, good=0.2, bad=2.0)
        ebitda = s.get("ebitda", 0) or 0.0
        # interest coverage proxy: ebitda relative to a 6% cost of debt
        int_exp = max(debt * 0.06, 1e-6)
        coverage = ebitda / int_exp if int_exp else 0.0
        cov_score = _score_higher_better(coverage, bad=2.0, good=15.0)
        signals = {"roic": round(roic, 1), "roe": round(roe, 1),
                   "balance_sheet": round(balance, 1),
                   "interest_coverage": round(cov_score, 1)}
        score = 0.35 * roic + 0.25 * roe + 0.20 * balance + 0.20 * cov_score
        rationale = (f"ROIC {s.get('roic', 0) * 100:.0f}%, ROE {s.get('roe', 0) * 100:.0f}%, "
                     f"debt/equity {d2e:.1f}x.")
        return _clip(score), signals, rationale

    def _turnaround(self, s: dict):
        eps = s.get("eps_3y", []) or []
        rev = s.get("revenue_3y", []) or []
        eg1, eg2 = self._series_deltas(eps)
        # improving earnings trajectory (acceleration), bonus for negative->positive
        traj = _score_higher_better(eg2 - eg1, bad=-0.10, good=0.30)
        cross = 0.0
        if len(eps) >= 3 and eps[0] <= 0 < eps[2]:
            cross = 100.0  # crossed into profitability
        elif len(eps) >= 3 and eps[2] > eps[0]:
            cross = _score_higher_better((eps[2] - eps[0]) / (abs(eps[0]) + 1e-6),
                                         bad=0.0, good=1.0)
        rg1, rg2 = self._series_deltas(rev)
        rev_recovery = _score_higher_better(rg2 - rg1, bad=-0.10, good=0.20)
        # deleveraging proxy: lower debt/equity scores well
        equity = s.get("equity", 0) or 0.0
        d2e = (s.get("total_debt", 0) / equity) if equity > 0 else 5.0
        deleveraging = _score_lower_better(d2e, good=0.3, bad=3.0)
        signals = {"earnings_trajectory": round(traj, 1),
                   "profitability_crossover": round(cross, 1),
                   "revenue_recovery": round(rev_recovery, 1),
                   "balance_improvement": round(deleveraging, 1)}
        score = 0.35 * traj + 0.30 * cross + 0.20 * rev_recovery + 0.15 * deleveraging
        rationale = (f"Earnings improving (EPS {eps[0] if eps else 0} -> "
                     f"{eps[2] if len(eps) >= 3 else 0}); revenue trajectory recovering.")
        return _clip(score), signals, rationale

    def _compounder(self, s: dict):
        rev = s.get("revenue_3y", []) or []
        rg1, rg2 = self._series_deltas(rev)
        # consistency: both periods positive and similar magnitude
        consistency = 0.0
        if rg1 > 0 and rg2 > 0:
            consistency = _score_higher_better(min(rg1, rg2), bad=0.0, good=0.12)
        margin = _score_higher_better(s.get("operating_margin", 0), bad=0.10, good=0.30)
        gross = _score_higher_better(s.get("gross_margin", 0), bad=0.20, good=0.65)
        roic = _score_higher_better(s.get("roic", 0), bad=0.10, good=0.30)
        signals = {"growth_consistency": round(consistency, 1),
                   "operating_margin": round(margin, 1),
                   "gross_margin": round(gross, 1),
                   "returns_on_capital": round(roic, 1)}
        score = 0.30 * consistency + 0.25 * margin + 0.15 * gross + 0.30 * roic
        rationale = (f"Consistent revenue growth ({rg1 * 100:.0f}% -> {rg2 * 100:.0f}%), "
                     f"{s.get('operating_margin', 0) * 100:.0f}% operating margin, "
                     f"{s.get('roic', 0) * 100:.0f}% ROIC.")
        return _clip(score), signals, rationale

    def _hidden_gem(self, s: dict):
        coverage = _score_lower_better(max(s.get("analyst_coverage", 0), 0.5),
                                       good=2.0, bad=20.0)
        tier = self.universe.cap_tier(s.get("market_cap", 0))
        size = {"micro": 100.0, "small": 80.0, "mid": 35.0, "large": 0.0}.get(tier, 0.0)
        insider = _score_higher_better(s.get("insider_ownership", 0), bad=0.01, good=0.15)
        quality_score, _, _ = self._quality(s)
        signals = {"low_coverage": round(coverage, 1), "small_size": round(size, 1),
                   "insider_ownership": round(insider, 1),
                   "quality": round(quality_score, 1)}
        score = 0.30 * coverage + 0.25 * size + 0.20 * insider + 0.25 * quality_score
        rationale = (f"Only {s.get('analyst_coverage', 0)} analysts, {tier}-cap, "
                     f"{s.get('insider_ownership', 0) * 100:.0f}% insider ownership, "
                     f"solid quality.")
        return _clip(score), signals, rationale

    _STRATEGIES = {
        "value": ("Value", "Cheap on earnings, EV/EBITDA, FCF — discounted vs intrinsics.", "_value"),
        "growth": ("Growth", "Accelerating revenue and earnings with healthy margins.", "_growth"),
        "quality": ("Quality", "High returns on capital and a fortress balance sheet.", "_quality"),
        "turnaround": ("Turnaround", "Improving profitability, cash flow, and leverage.", "_turnaround"),
        "compounder": ("Compounder", "Durable growth + stable high margins + high returns on capital.", "_compounder"),
        "hidden_gem": ("Hidden Gem", "Under-followed small/micro caps with insider skin in the game.", "_hidden_gem"),
    }

    def strategies(self) -> list[dict]:
        return [{"id": k, "name": v[0], "description": v[1]}
                for k, v in self._STRATEGIES.items()]

    def scan(self, strategy: str, limit: int = 25) -> list[dict]:
        if strategy not in self._STRATEGIES:
            raise ValueError(f"unknown strategy: {strategy}")
        scorer = getattr(self, self._STRATEGIES[strategy][2])
        out = []
        for s in self._all():
            score, signals, rationale = scorer(s)
            out.append({
                "symbol": s["symbol"], "name": s["name"], "sector": s["sector"],
                "score": round(score, 1), "signals": signals, "rationale": rationale,
            })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[: max(0, int(limit))]
