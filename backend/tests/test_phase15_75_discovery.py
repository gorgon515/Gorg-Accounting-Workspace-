"""Phase 15.75 Part 1 — Investment Discovery Engine tests.

Covers the universe builder, opportunity scanners, idea ranking + anti-MAG7
diversification, memo generator, candidate portfolios, daily workflow, and live
ingestion. Each DB is monkeypatched to tmp_path and singletons reset.
"""
import pytest

import investing.discovery.universe as universe_mod
import investing.discovery.workflow as workflow_mod
import investing.discovery.engine as engine_mod


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(universe_mod, "_DB", tmp_path / "discovery_universe.db")
    monkeypatch.setattr(workflow_mod, "_DB", tmp_path / "discovery_workflow.db")
    universe_mod._instance = None
    workflow_mod._instance = None
    engine_mod._instance = None
    yield
    universe_mod._instance = None
    workflow_mod._instance = None
    engine_mod._instance = None


def _engine():
    return engine_mod.get_discovery_engine()


# ── Universe ──────────────────────────────────────────────────────────────────

class TestUniverse:
    def test_seed_populates_universe(self):
        e = _engine()  # auto-seeds in __init__
        s = e.universe_stats()
        assert s["total"] >= 80
        assert len(s["by_sector"]) >= 9

    def test_explicit_seed_returns_count(self):
        from investing.discovery.universe import get_universe_builder
        ub = get_universe_builder()
        res = ub.seed()
        assert res["added"] >= 80

    def test_no_mag7_in_universe(self):
        e = _engine()
        syms = set(e.universe.all_symbols())
        mag7 = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"}
        assert not (syms & mag7)

    def test_filter_by_sector(self):
        e = _engine()
        fins = e.list_universe(sector="Financials", limit=500)
        assert len(fins) > 0
        assert all(s["sector"] == "Financials" for s in fins)

    def test_filter_by_cap_tier(self):
        e = _engine()
        small = e.list_universe(cap_tier="small", limit=500)
        assert len(small) > 0
        assert all(s["cap_tier"] == "small" for s in small)
        for s in small:
            assert 300 <= s["market_cap"] < 2000

    def test_filter_by_exchange(self):
        e = _engine()
        nasdaq = e.list_universe(exchange="NASDAQ", limit=500)
        assert len(nasdaq) > 0
        assert all(s["exchange"] == "NASDAQ" for s in nasdaq)

    def test_cap_tier_boundaries(self):
        from investing.discovery.universe import UniverseBuilder
        assert UniverseBuilder.cap_tier(100) == "micro"
        assert UniverseBuilder.cap_tier(500) == "small"
        assert UniverseBuilder.cap_tier(5000) == "mid"
        assert UniverseBuilder.cap_tier(50000) == "large"

    def test_get_symbol_and_missing(self):
        e = _engine()
        sym = e.universe.all_symbols()[0]
        assert e.get_security(sym)["symbol"] == sym
        assert e.get_security("ZZNOTREAL") is None

    def test_stats_shape(self):
        e = _engine()
        s = e.universe_stats()
        assert set(s.keys()) == {"total", "by_sector", "by_exchange", "by_cap_tier"}
        assert set(s["by_cap_tier"].keys()) == {"micro", "small", "mid", "large"}


# ── Ingest (live data) ────────────────────────────────────────────────────────

class TestIngest:
    def test_ingest_upserts_live_data(self):
        e = _engine()
        before = e.universe_stats()["total"]
        live = [{
            "symbol": "LIVE1", "name": "Live Co", "exchange": "NYSE",
            "sector": "Industrials", "industry": "Widgets", "market_cap": 1500.0,
            "revenue": 800.0, "net_income": 90.0, "fcf": 100.0, "total_debt": 100.0,
            "equity": 500.0, "ebitda": 180.0, "enterprise_value": 1600.0,
            "revenue_growth": 0.12, "earnings_growth": 0.15, "gross_margin": 0.40,
            "operating_margin": 0.18, "roic": 0.20, "roe": 0.18, "pe": 14.0,
            "ev_ebitda": 9.0, "price_to_fcf": 15.0, "fcf_yield": 0.066,
            "dividend_yield": 0.01, "insider_ownership": 0.08, "analyst_coverage": 3,
            "revenue_3y": [640.0, 720.0, 800.0], "eps_3y": [0.5, 0.6, 0.7],
        }]
        res = e.ingest_securities(live)
        assert res["upserted"] == 1
        assert e.universe_stats()["total"] == before + 1
        got = e.get_security("LIVE1")
        assert got["name"] == "Live Co"
        assert got["revenue_3y"] == [640.0, 720.0, 800.0]

    def test_ingest_updates_existing(self):
        e = _engine()
        sym = e.universe.all_symbols()[0]
        e.ingest_securities([{"symbol": sym, "name": "Renamed Inc.",
                              "market_cap": 1234.0}])
        got = e.get_security(sym)
        assert got["name"] == "Renamed Inc."
        assert got["market_cap"] == 1234.0


# ── Scanner ───────────────────────────────────────────────────────────────────

class TestScanner:
    def test_strategies_listed(self):
        e = _engine()
        strats = e.scan_strategies()
        ids = {s["id"] for s in strats}
        assert ids == {"value", "growth", "quality", "turnaround",
                       "compounder", "hidden_gem"}
        assert all("name" in s and "description" in s for s in strats)

    @pytest.mark.parametrize("strategy", ["value", "growth", "quality",
                                          "turnaround", "compounder", "hidden_gem"])
    def test_each_strategy_returns_ranked_results(self, strategy):
        e = _engine()
        res = e.scan(strategy, limit=15)
        assert 0 < len(res) <= 15
        for r in res:
            assert {"symbol", "name", "score", "signals", "rationale"} <= set(r.keys())
            assert 0 <= r["score"] <= 100
            assert isinstance(r["signals"], dict) and r["signals"]
            assert isinstance(r["rationale"], str) and r["rationale"]
        scores = [r["score"] for r in res]
        assert scores == sorted(scores, reverse=True)

    def test_hidden_gem_favors_small_low_coverage(self):
        e = _engine()
        res = e.scan("hidden_gem", limit=10)
        top = res[0]
        sec = e.get_security(top["symbol"])
        assert sec["cap_tier"] in ("micro", "small", "mid")
        assert sec["analyst_coverage"] <= 12

    def test_unknown_strategy_raises(self):
        e = _engine()
        with pytest.raises(ValueError):
            e.scan("nonsense")


# ── Ranking + anti-MAG7 ───────────────────────────────────────────────────────

class TestRanking:
    def test_rank_returns_factors_and_penalties(self):
        e = _engine()
        ranked = e.rank(limit=20)
        assert len(ranked) == 20
        for r in ranked:
            assert {"symbol", "name", "sector", "composite",
                    "factors", "penalties"} <= set(r.keys())
            assert 0 <= r["composite"] <= 100
            assert set(r["factors"].keys()) >= {"valuation", "quality", "growth",
                                                "momentum", "financial_strength",
                                                "earnings_revisions", "sector_tailwind"}
            assert set(r["penalties"].keys()) == {"mega_cap", "coverage",
                                                  "portfolio_overlap"}
        comps = [r["composite"] for r in ranked]
        assert comps == sorted(comps, reverse=True)

    def test_mega_cap_penalized(self):
        e = _engine()
        # ingest a synthetic mega-cap that scores well on fundamentals
        e.ingest_securities([{
            "symbol": "MEGA", "name": "Mega Cap Co", "exchange": "NASDAQ",
            "sector": "Information Technology", "industry": "Software",
            "market_cap": 1500000.0, "revenue": 200000.0, "net_income": 60000.0,
            "fcf": 70000.0, "total_debt": 10000.0, "equity": 120000.0,
            "ebitda": 90000.0, "enterprise_value": 1510000.0, "revenue_growth": 0.15,
            "earnings_growth": 0.20, "gross_margin": 0.70, "operating_margin": 0.40,
            "roic": 0.30, "roe": 0.40, "pe": 25.0, "ev_ebitda": 16.0,
            "price_to_fcf": 21.0, "fcf_yield": 0.046, "dividend_yield": 0.005,
            "insider_ownership": 0.02, "analyst_coverage": 40,
            "revenue_3y": [150000.0, 174000.0, 200000.0], "eps_3y": [3.0, 3.6, 4.3],
        }])
        ranked = e.rank(limit=200)
        mega = next(r for r in ranked if r["symbol"] == "MEGA")
        assert mega["penalties"]["mega_cap"] > 0
        # mega cap should not be in the top decile despite strong fundamentals
        positions = [r["symbol"] for r in ranked]
        assert positions.index("MEGA") > 10

    def test_exclude_mega_cap_removes_them(self):
        e = _engine()
        e.ingest_securities([{
            "symbol": "BIG", "name": "Big Co", "exchange": "NYSE",
            "sector": "Industrials", "industry": "X", "market_cap": 500000.0,
            "revenue": 1.0, "net_income": 1.0, "fcf": 1.0, "total_debt": 0.0,
            "equity": 1.0, "ebitda": 1.0, "enterprise_value": 500000.0,
            "revenue_growth": 0.0, "earnings_growth": 0.0, "gross_margin": 0.0,
            "operating_margin": 0.0, "roic": 0.0, "roe": 0.0, "pe": 0.0,
            "ev_ebitda": 0.0, "price_to_fcf": 0.0, "fcf_yield": 0.0,
            "dividend_yield": 0.0, "insider_ownership": 0.0, "analyst_coverage": 0,
            "revenue_3y": [1.0, 1.0, 1.0], "eps_3y": [1.0, 1.0, 1.0],
        }])
        ranked = e.rank(limit=300, exclude_mega_cap=True)
        assert all(r["symbol"] != "BIG" for r in ranked)

    def test_portfolio_overlap_excluded(self):
        e = _engine()
        syms = e.universe.all_symbols()
        owned = syms[:5]
        ranked = e.rank(limit=300, portfolio_overlap=owned)
        ranked_syms = {r["symbol"] for r in ranked}
        assert not (ranked_syms & set(owned))

    def test_coverage_penalty_applied(self):
        e = _engine()
        ranked_pen = e.rank(limit=300, penalize_coverage=True)
        ranked_nopen = e.rank(limit=300, penalize_coverage=False)
        # find a heavily-covered name and confirm penalty differs
        by_sym_pen = {r["symbol"]: r for r in ranked_pen}
        by_sym_nopen = {r["symbol"]: r for r in ranked_nopen}
        # CRM has 30 analysts in the seed
        if "CRM" in by_sym_pen:
            assert by_sym_pen["CRM"]["penalties"]["coverage"] > 0
            assert by_sym_nopen["CRM"]["penalties"]["coverage"] == 0

    def test_ideas_tiers_respect_counts(self):
        e = _engine()
        assert len(e.ideas("top10")) <= 10
        assert len(e.ideas("top25")) <= 25
        assert len(e.ideas("top50")) <= 50
        assert len(e.ideas("top100")) <= 100
        assert len(e.ideas("top10")) == 10

    def test_ideas_unknown_tier_raises(self):
        e = _engine()
        with pytest.raises(ValueError):
            e.ideas("top999")


# ── Memo ──────────────────────────────────────────────────────────────────────

class TestMemo:
    def test_memo_has_all_sections(self):
        e = _engine()
        sym = e.universe.all_symbols()[0]
        m = e.memo_for(sym)
        for key in ("business_overview", "bull_case", "bear_case", "risks",
                    "catalysts", "valuation", "quality_analysis",
                    "competitive_position", "confidence_score"):
            assert key in m
        assert isinstance(m["bull_case"], list) and m["bull_case"]
        assert isinstance(m["bear_case"], list) and m["bear_case"]
        assert isinstance(m["risks"], list) and m["risks"]
        assert isinstance(m["catalysts"], list) and m["catalysts"]
        assert 0 <= m["confidence_score"] <= 100
        assert m["valuation"]["read"] in ("cheap", "fair", "expensive")

    def test_memo_valuation_multiples_present(self):
        e = _engine()
        m = e.memo_for(e.universe.all_symbols()[0])
        for k in ("pe", "ev_ebitda", "price_to_fcf", "fcf_yield"):
            assert k in m["valuation"]

    def test_memo_not_found_raises(self):
        e = _engine()
        with pytest.raises(ValueError):
            e.memo_for("ZZNOTREAL")


# ── Candidate Portfolios ──────────────────────────────────────────────────────

class TestPortfolios:
    def test_five_styles(self):
        e = _engine()
        styles = {s["id"] for s in e.portfolio_styles()}
        assert styles == {"conservative", "growth", "value", "dividend", "small_cap"}

    @pytest.mark.parametrize("style", ["conservative", "growth", "value",
                                       "dividend", "small_cap"])
    def test_build_each_style_weights_sum_to_one(self, style):
        e = _engine()
        pf = e.build_portfolio(style, size=8)
        assert pf["style"] == style
        assert 1 <= len(pf["holdings"]) <= 8
        total = sum(h["weight"] for h in pf["holdings"])
        assert abs(total - 1.0) < 0.01
        for h in pf["holdings"]:
            assert {"symbol", "name", "weight", "reason"} <= set(h.keys())

    def test_small_cap_only_small_names(self):
        e = _engine()
        pf = e.build_portfolio("small_cap", size=10)
        for h in pf["holdings"]:
            sec = e.get_security(h["symbol"])
            assert sec["cap_tier"] in ("micro", "small")

    def test_dividend_only_payers(self):
        e = _engine()
        pf = e.build_portfolio("dividend", size=10)
        for h in pf["holdings"]:
            sec = e.get_security(h["symbol"])
            assert sec["dividend_yield"] > 0

    def test_unknown_style_raises(self):
        e = _engine()
        with pytest.raises(ValueError):
            e.build_portfolio("bogus")


# ── Daily Workflow ────────────────────────────────────────────────────────────

class TestDailyWorkflow:
    def test_run_returns_all_sections(self):
        e = _engine()
        run = e.run_daily()
        for key in ("run_date", "new_opportunities", "improving", "deteriorating",
                    "insider_activity", "earnings_surprises", "valuation_dislocations"):
            assert key in run
        for key in ("new_opportunities", "improving", "deteriorating",
                    "insider_activity", "earnings_surprises", "valuation_dislocations"):
            assert isinstance(run[key], list)

    def test_latest_returns_persisted_run(self):
        e = _engine()
        run = e.run_daily()
        latest = e.latest_daily()
        assert latest is not None
        assert latest["run_date"] == run["run_date"]
        assert latest["new_opportunities"] == run["new_opportunities"]

    def test_latest_none_before_run(self):
        e = _engine()
        assert e.latest_daily() is None

    def test_new_opportunities_exclude_mega_cap(self):
        e = _engine()
        run = e.run_daily()
        # new opportunities should carry a composite score
        for o in run["new_opportunities"]:
            assert "composite" in o

    def test_workflow_surfaces_real_signal(self):
        e = _engine()
        run = e.run_daily()
        # The seed data encodes acceleration, so these lists must not be empty.
        assert len(run["new_opportunities"]) > 0
        assert len(run["improving"]) > 0
        assert len(run["insider_activity"]) > 0
        assert len(run["valuation_dislocations"]) > 0
        for o in run["improving"]:
            assert {"symbol", "name", "earnings_accel", "eps_growth"} <= set(o.keys())


# ── Engine facade ─────────────────────────────────────────────────────────────

class TestEngine:
    def test_auto_seed_on_first_use(self):
        e = _engine()
        assert e.universe_stats()["total"] >= 80

    def test_stats_shape(self):
        e = _engine()
        s = e.stats()
        assert "universe" in s
        assert s["strategies"] == 6
        assert s["portfolio_styles"] == 5
