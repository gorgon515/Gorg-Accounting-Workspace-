"""Phase 14 — quant lab, factors, alt-data, thesis, earnings, macro, agents."""
import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SINGLETONS = ["quant_lab.lab", "quant_lab.factors", "altdata.platform",
               "thesis.engine", "earnings.engine", "macro.engine",
               "financial_hub.store", "backtesting.engine", "knowledge.engine"]


def _reset():
    for m in _SINGLETONS:
        if m in sys.modules and hasattr(sys.modules[m], "_instance"):
            sys.modules[m]._instance = None
    import quant_agents.agents as qa
    qa._instances = {}
    for vm in ("vector_memory.store", "embeddings.pipeline", "rag.platform"):
        if vm in sys.modules and hasattr(sys.modules[vm], "_instances"):
            sys.modules[vm]._instances = {}


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset()
    yield
    _reset()


def _seed_prices(symbols, n=120, seed=3):
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    rng = np.random.default_rng(seed)
    for k, sym in enumerate(symbols):
        px = 100.0
        bars = []
        for i in range(n):
            px *= (1 + rng.normal(0.0006 + k * 0.0002, 0.013))
            bars.append({"date": f"2023-{(i//28)+1:02d}-{(i%28)+1:02d}", "close": round(px, 2), "volume": 1000})
        hub.store_prices(sym, bars, source="test")
    return hub


# ── Quant Lab ────────────────────────────────────────────────────────────────

def test_create_strategy_and_version():
    from quant_lab.lab import get_quant_lab
    lab = get_quant_lab()
    s = lab.create_strategy("Momentum", "12-1 momentum", definition={"kind": "momentum"})
    assert s["id"] and s["version"] == 1
    updated = lab.update_strategy(s["id"], {"kind": "momentum", "window": 90}, note="tune")
    assert updated["version"] == 2
    versions = lab.strategy_versions(s["id"])
    assert len(versions) == 2


def test_generate_signal():
    from quant_lab.lab import get_quant_lab
    _seed_prices(["AAA"])
    lab = get_quant_lab()
    sig = lab.generate_signal("AAA", {"kind": "sma_cross", "fast": 10, "slow": 30})
    assert "signals" in sig
    assert len(sig["signals"]) == len(sig["asset_returns"])


def test_run_experiment():
    from quant_lab.lab import get_quant_lab
    _seed_prices(["AAA"])
    lab = get_quant_lab()
    exp = lab.run_experiment("exp1", "AAA", {"kind": "momentum", "window": 30})
    assert exp["id"]
    assert "metrics" in exp
    assert "sharpe" in exp["metrics"]


def test_hypothesis_lifecycle():
    from quant_lab.lab import get_quant_lab
    lab = get_quant_lab()
    h = lab.create_hypothesis("Low-vol outperforms", "anomaly")
    assert h["status"] == "open"
    resolved = lab.resolve_hypothesis(h["id"], "Confirmed in-sample", "confirmed")
    assert resolved["status"] == "confirmed"


def test_notebook():
    from quant_lab.lab import get_quant_lab
    lab = get_quant_lab()
    nb = lab.create_notebook("Research log", "notes")
    assert nb["id"]
    assert any(n["title"] == "Research log" for n in lab.list_notebooks())


# ── Factor Library ───────────────────────────────────────────────────────────

def test_factor_library_list():
    from quant_lab.factors import get_factor_library
    lib = get_factor_library().library()
    names = {f["name"] for f in lib}
    assert {"value", "quality", "momentum", "growth", "volatility", "size"} <= names


def test_factor_score_symbol():
    from quant_lab.factors import get_factor_library
    _seed_prices(["AAA"])
    sc = get_factor_library().score_symbol("AAA")
    assert "momentum" in sc and "volatility" in sc


def test_factor_rank():
    from quant_lab.factors import get_factor_library
    _seed_prices(["AAA", "BBB", "CCC"])
    ranked = get_factor_library().rank(["AAA", "BBB", "CCC"], "momentum")
    assert len(ranked) >= 1
    assert ranked[0]["rank"] == 1


def test_factor_combine():
    from quant_lab.factors import get_factor_library
    _seed_prices(["AAA", "BBB"])
    combo = get_factor_library().combine(["AAA", "BBB"], {"momentum": 0.5, "volatility": 0.5})
    assert all("composite_score" in c for c in combo)


def test_factor_persistence_and_snapshot():
    from quant_lab.factors import get_factor_library
    _seed_prices(["AAA"])
    lib = get_factor_library()
    lib.snapshot(["AAA"])
    lib.snapshot(["AAA"])
    p = lib.persistence("AAA", "momentum")
    assert p["n_observations"] >= 2


def test_custom_factor():
    from quant_lab.factors import get_factor_library
    lib = get_factor_library()
    cf = lib.create_custom("MyBlend", "value+quality", {"value": 0.5, "quality": 0.5})
    assert cf["id"]
    assert any(c["name"] == "MyBlend" for c in lib.list_custom())


# ── Alternative Data ─────────────────────────────────────────────────────────

def test_altdata_ingest_and_signals():
    from altdata.platform import get_altdata_platform
    p = get_altdata_platform()
    obs = [{"symbol": "AAA", "value": v, "observed_at": f"2024-01-{i+1:02d}"}
           for i, v in enumerate([100, 102, 101, 150])]  # spike at end
    res = p.ingest("short_interest", obs)
    assert res["stored"] == 4
    change = p.detect_changes("short_interest", "AAA", threshold=0.1)
    assert change["change_detected"]
    signals = p.generate_signals("short_interest")
    assert isinstance(signals, list)


def test_altdata_unknown_dataset():
    from altdata.platform import get_altdata_platform
    res = get_altdata_platform().ingest("nonsense", [])
    assert "error" in res


def test_altdata_datasets():
    from altdata.platform import get_altdata_platform
    ds = get_altdata_platform().datasets()
    ids = {d["id"] for d in ds}
    assert "insider_activity" in ids and "congressional_trades" in ids


# ── Thesis Engine ────────────────────────────────────────────────────────────

def test_thesis_lifecycle():
    from thesis.engine import get_thesis_engine
    te = get_thesis_engine()
    t = te.create("Long AAA", symbol="AAA", expected_return=0.2, confidence=0.7,
                  evidence=["strong moat"], risks=["valuation"], catalysts=["new product"])
    assert t["id"]
    te.add_review(t["id"], "still on track", confidence=0.75)
    reviews = te.reviews(t["id"])
    assert len(reviews) == 1
    closed = te.close_outcome(t["id"], "correct", realized_return=0.18)
    assert closed["status"] == "closed"
    assert closed["realized_return"] == 0.18


def test_thesis_update():
    from thesis.engine import get_thesis_engine
    te = get_thesis_engine()
    t = te.create("Short BBB", symbol="BBB", direction="short")
    upd = te.update(t["id"], {"confidence": 0.9, "risks": ["short squeeze"]})
    assert upd["confidence"] == 0.9
    assert "short squeeze" in upd["risks"]


# ── Earnings Intelligence ────────────────────────────────────────────────────

def test_earnings_surprise_and_scorecard():
    from earnings.engine import get_earnings_engine
    ee = get_earnings_engine()
    ev = ee.add_event("AAA", period="Q1", eps_estimate=1.0, eps_actual=1.15,
                      revenue_estimate=100, revenue_actual=108,
                      guidance="raised guidance, strong record growth")
    surp = ee.surprise(ev["id"])
    assert surp["eps_beat"] is True
    card = ee.scorecard(ev["id"])
    assert card["grade"] in ("A", "B")
    assert card["score"] > 50


def test_earnings_sentiment():
    from earnings.engine import get_earnings_engine
    ee = get_earnings_engine()
    pos = ee.analyze_sentiment("strong record growth, raised guidance, robust momentum")
    neg = ee.analyze_sentiment("weak results, lowered guidance, declining margins, headwinds")
    assert pos["sentiment"] == "positive"
    assert neg["sentiment"] == "negative"


def test_earnings_revision_trend():
    from earnings.engine import get_earnings_engine
    ee = get_earnings_engine()
    ee.add_revision("AAA", "eps", 1.0, 1.1)
    ee.add_revision("AAA", "eps", 1.1, 1.2)
    trend = ee.revision_trend("AAA")
    assert trend["net_direction"] == "up"


# ── Macro Intelligence ───────────────────────────────────────────────────────

def _seed_macro():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.store_economic("UNRATE", "Unemployment", [{"date": "2024-01-01", "value": "3.7"},
                                                  {"date": "2023-10-01", "value": "3.9"}])
    hub.store_economic("FEDFUNDS", "Fed", [{"date": "2024-01-01", "value": "5.33"},
                                           {"date": "2023-10-01", "value": "5.50"}])
    hub.store_economic("CPIAUCSL", "CPI", [{"date": "2024-01-01", "value": "300"},
                                           {"date": "2023-10-01", "value": "299"}])
    hub.store_economic("GS10", "10y", [{"date": "2024-01-01", "value": "4.0"}])
    hub.store_economic("GS2", "2y", [{"date": "2024-01-01", "value": "4.5"}])
    return hub


def test_macro_indicators():
    _seed_macro()
    from macro.engine import get_macro_engine
    ind = get_macro_engine().indicators()
    assert "unemployment" in ind
    assert "fed_funds" in ind


def test_macro_yield_curve_inversion():
    _seed_macro()
    from macro.engine import get_macro_engine
    curve = get_macro_engine().yield_curve()
    assert curve["available"] is True
    assert curve["inverted_10y_2y"] is True
    assert curve["signal"] == "recession_warning"


def test_macro_regime_classification():
    _seed_macro()
    from macro.engine import get_macro_engine
    reg = get_macro_engine().classify_regime()
    assert reg["regime"] in ("goldilocks", "reflation", "stagflation", "deflation")
    assert 0 <= reg["risk_score"] <= 1
    assert reg["stance"] in ("risk_on", "risk_off", "neutral")
    assert reg["outlook"]


# ── Investment Agents ────────────────────────────────────────────────────────

def test_macro_strategist_agent():
    _seed_macro()
    from quant_agents.agents import get_quant_agent
    agent = get_quant_agent("macro_strategist")
    result = agent.run()
    assert result.agent_id == "agent_macro_strategist"
    assert result.error is None
    assert len(result.findings) >= 1


def test_portfolio_manager_agent():
    _seed_prices(["AAA", "BBB", "CCC"])
    from portfolio.engine import get_portfolio_engine
    get_portfolio_engine().construct("PM Test", ["AAA", "BBB", "CCC"], method="equal_weight")
    from quant_agents.agents import get_quant_agent
    result = get_quant_agent("portfolio_manager").run()
    assert result.agent_id == "agent_portfolio_manager"
    assert result.error is None


def test_risk_officer_agent():
    _seed_prices(["AAA", "BBB"])
    from portfolio.engine import get_portfolio_engine
    get_portfolio_engine().construct("RO Test", ["AAA", "BBB"], method="equal_weight")
    from quant_agents.agents import get_quant_agent
    result = get_quant_agent("risk_officer").run()
    assert result.agent_id == "agent_risk_officer"
    assert result.error is None


def test_all_quant_agents_run():
    from quant_agents.agents import get_quant_agent, list_quant_agents
    for a in list_quant_agents():
        result = get_quant_agent(a["id"]).run()
        assert result.error is None, f"{a['id']} errored: {result.error}"


def test_list_quant_agents():
    from quant_agents.agents import list_quant_agents
    agents = list_quant_agents()
    ids = {a["id"] for a in agents}
    assert {"portfolio_manager", "quant_research", "risk_officer",
            "macro_strategist", "earnings_analyst", "factor_research"} == ids
