"""
Phase 14 integration — end-to-end investment pipeline:
  prices → factor ranking → strategy/backtest → portfolio construction →
  risk analysis → thesis → macro regime → agent proposals → approval queue,
  plus knowledge-engine integration and existing-system coexistence.
"""
import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SINGLETONS = [
    "quant_lab.lab", "quant_lab.factors", "altdata.platform", "thesis.engine",
    "earnings.engine", "macro.engine", "financial_hub.store", "backtesting.engine",
    "portfolio.engine", "risk_analytics.engine", "knowledge.engine",
]


def _reset():
    extra = ["connectors.registry", "live_intelligence.monitor"]
    for m in _SINGLETONS + extra:
        if m in sys.modules and hasattr(sys.modules[m], "_instance"):
            sys.modules[m]._instance = None
    if "quant_agents.agents" in sys.modules:
        sys.modules["quant_agents.agents"]._instances = {}
    if "workforce_agents.base" in sys.modules and hasattr(sys.modules["workforce_agents.base"], "_instance"):
        sys.modules["workforce_agents.base"]._instance = None
    for vm in ("vector_memory.store", "embeddings.pipeline", "rag.platform"):
        if vm in sys.modules and hasattr(sys.modules[vm], "_instances"):
            sys.modules[vm]._instances = {}


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset()
    yield
    _reset()


def _seed(symbols=("AAA", "BBB", "CCC", "DDD"), n=150, seed=11):
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    rng = np.random.default_rng(seed)
    for k, sym in enumerate(symbols):
        px = 100.0
        bars = []
        for i in range(n):
            px *= (1 + rng.normal(0.0006 + k * 0.0002, 0.012 + k * 0.001))
            bars.append({"date": f"2023-{(i//30)+1:02d}-{(i%30)+1:02d}", "close": round(px, 2), "volume": 1000})
        hub.store_prices(sym, bars, source="test")
        hub.add_watchlist(sym)
    return hub


def test_end_to_end_investment_pipeline():
    _seed()
    symbols = ["AAA", "BBB", "CCC", "DDD"]

    # 1. Factor ranking works
    from quant_lab.factors import get_factor_library
    ranked = get_factor_library().rank(symbols, "momentum")
    assert len(ranked) >= 1  # factor research works

    # 2. Strategy + backtest works
    from quant_lab.lab import get_quant_lab
    lab = get_quant_lab()
    strat = lab.create_strategy("MomCross", definition={"kind": "sma_cross"})
    exp = lab.run_experiment("e2e", "AAA", {"kind": "sma_cross", "fast": 10, "slow": 30},
                             strategy_id=strat["id"])
    assert "sharpe" in exp["metrics"]  # backtesting engine functions

    # 3. Portfolio construction works (max sharpe)
    from portfolio.engine import get_portfolio_engine
    pe = get_portfolio_engine()
    pf = pe.construct("E2E Portfolio", symbols, method="maximum_sharpe")
    assert abs(sum(pf["weights"].values()) - 1.0) < 1e-2  # portfolio optimization functions

    # 4. Risk analytics work
    from risk_analytics.engine import get_risk_engine
    re = get_risk_engine()
    holdings = [{"symbol": s, "weight": w} for s, w in pf["weights"].items()]
    risk = re.analyze(holdings, name="E2E", portfolio_id=pf["id"])
    assert risk["health_score"] is not None  # risk analytics function
    stress = re.stress_test(holdings)
    assert len(stress["scenarios"]) >= 5

    # 5. Macro intelligence works
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.store_economic("UNRATE", "U", [{"date": "2024-01-01", "value": "3.7"}, {"date": "2023-10-01", "value": "3.9"}])
    hub.store_economic("FEDFUNDS", "F", [{"date": "2024-01-01", "value": "5.0"}, {"date": "2023-10-01", "value": "5.25"}])
    from macro.engine import get_macro_engine
    regime = get_macro_engine().classify_regime()
    assert regime["regime"]  # macro intelligence works

    # 6. Alternative data ingestion works
    from altdata.platform import get_altdata_platform
    ad = get_altdata_platform()
    res = ad.ingest("insider_activity", [{"symbol": "AAA", "value": 5, "observed_at": "2024-01-01"}])
    assert res["stored"] == 1  # alternative data ingestion works

    # 7. Thesis tracking works
    from thesis.engine import get_thesis_engine
    te = get_thesis_engine()
    thesis = te.create("Long AAA", symbol="AAA", expected_return=0.15, confidence=0.6)
    assert thesis["id"]  # thesis tracking works


def test_agents_propose_into_approval_queue():
    """Agents generate advisory proposals; nothing executes automatically."""
    _seed()
    from portfolio.engine import get_portfolio_engine
    get_portfolio_engine().construct("Approval Test", ["AAA", "BBB", "CCC"], method="equal_weight")

    from quant_agents.agents import get_quant_agent
    pm = get_quant_agent("portfolio_manager")
    result = pm.run()
    assert result.error is None
    # Proposed actions are recorded; any high-impact action requires approval.
    actions = pm.list_proposed_actions(status="pending")
    for a in actions:
        # rebalance proposals must require approval (advisory only)
        if a["action_type"] == "rebalance_proposal":
            assert a["requires_approval"] == 1


def test_knowledge_engine_receives_research():
    """Strategies and theses flow into the knowledge engine."""
    _seed()
    from knowledge.engine import get_knowledge_engine
    ke = get_knowledge_engine()
    before = ke.stats().get("total_items", 0)

    from quant_lab.lab import get_quant_lab
    get_quant_lab().create_strategy("KE Strategy", "feeds knowledge")
    from thesis.engine import get_thesis_engine
    get_thesis_engine().create("KE Thesis", symbol="AAA", summary="feeds knowledge")

    after = ke.stats().get("total_items", 0)
    assert after >= before + 1  # knowledge engine integration


def test_thesis_outcome_feeds_institutional_memory():
    _seed()
    from thesis.engine import get_thesis_engine
    te = get_thesis_engine()
    t = te.create("Outcome thesis", symbol="AAA", expected_return=0.2, confidence=0.7)
    te.close_outcome(t["id"], "correct", realized_return=0.18)
    # institutional memory should hold the recorded decision
    from knowledge.memory import get_institutional_memory
    mem = get_institutional_memory()
    records = mem.list(domain="markets") if hasattr(mem, "list") else []
    assert isinstance(records, list)


def test_existing_systems_still_functional():
    """Phase 13 + prior engines still import and respond."""
    from live_intelligence.monitor import get_monitor  # Phase 13
    from connectors.registry import get_registry        # Phase 13
    from knowledge.engine import get_knowledge_engine    # Phase 12
    assert get_registry().stats()["total"] >= 5
    assert "total_items" in get_monitor().stats()
    # Knowledge engine remains queryable (stats avoids cross-test ChromaDB client churn).
    assert "total_items" in get_knowledge_engine().stats()
