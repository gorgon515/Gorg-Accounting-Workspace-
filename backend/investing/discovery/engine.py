"""Discovery Engine facade.

Composes the universe builder, opportunity scanners, idea ranker, memo
generator, candidate builder, and daily workflow behind one object. Auto-seeds
the universe from the static snapshot on first use if it is empty. Exposes the
pass-through methods consumed by the discovery router.
"""
from __future__ import annotations
from typing import Optional

from .universe import UniverseBuilder
from .scanner import OpportunityScanner
from .ranking import IdeaRanker
from .memo import MemoGenerator
from .portfolios import CandidateBuilder
from .workflow import DailyWorkflow


class DiscoveryEngine:
    def __init__(self):
        self.universe = UniverseBuilder()
        # Auto-seed on first use if the universe is empty.
        if self.universe.stats().get("total", 0) == 0:
            self.universe.seed()
        self.scanner = OpportunityScanner(self.universe)
        self.ranker = IdeaRanker(self.universe, self.scanner)
        self.memo = MemoGenerator(self.universe, self.scanner)
        self.candidates = CandidateBuilder(self.universe, self.scanner)
        self.workflow = DailyWorkflow(self.universe, self.scanner, self.ranker)

    # ── universe ─────────────────────────────────────────────────────────────
    def universe_stats(self) -> dict:
        return self.universe.stats()

    def list_universe(self, sector: Optional[str] = None, cap_tier: Optional[str] = None,
                      exchange: Optional[str] = None, limit: int = 200) -> list[dict]:
        return self.universe.list(sector=sector, cap_tier=cap_tier,
                                  exchange=exchange, limit=limit)

    def get_security(self, symbol: str) -> Optional[dict]:
        return self.universe.get(symbol)

    def seed(self) -> dict:
        return self.universe.seed()

    def ingest_securities(self, securities: list[dict]) -> dict:
        return self.universe.ingest(securities)

    # ── scanning ─────────────────────────────────────────────────────────────
    def scan_strategies(self) -> list[dict]:
        return self.scanner.strategies()

    def scan(self, strategy: str, limit: int = 25) -> list[dict]:
        return self.scanner.scan(strategy, limit=limit)

    # ── ranking ──────────────────────────────────────────────────────────────
    def rank(self, limit: int = 100, exclude_mega_cap: bool = False,
             penalize_coverage: bool = True,
             portfolio_overlap: Optional[list[str]] = None) -> list[dict]:
        return self.ranker.rank(limit=limit, exclude_mega_cap=exclude_mega_cap,
                                penalize_coverage=penalize_coverage,
                                portfolio_overlap=portfolio_overlap)

    def ideas(self, tier: str = "top25") -> list[dict]:
        return self.ranker.ideas(tier)

    # ── memo ─────────────────────────────────────────────────────────────────
    def memo_for(self, symbol: str) -> dict:
        return self.memo.generate(symbol)

    # ── candidate portfolios ─────────────────────────────────────────────────
    def portfolio_styles(self) -> list[dict]:
        return self.candidates.styles()

    def build_portfolio(self, style: str, size: int = 10) -> dict:
        return self.candidates.build(style, size=size)

    # ── daily workflow ───────────────────────────────────────────────────────
    def run_daily(self) -> dict:
        return self.workflow.run()

    def latest_daily(self) -> Optional[dict]:
        return self.workflow.latest()

    # ── stats ────────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        us = self.universe.stats()
        latest = self.workflow.latest()
        return {
            "universe": us,
            "strategies": len(self.scanner.strategies()),
            "portfolio_styles": len(self.candidates.styles()),
            "last_daily_run": latest.get("run_date") if latest else None,
        }


_instance: Optional[DiscoveryEngine] = None


def get_discovery_engine() -> DiscoveryEngine:
    global _instance
    if _instance is None:
        _instance = DiscoveryEngine()
    return _instance
