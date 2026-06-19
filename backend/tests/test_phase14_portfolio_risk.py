"""Phase 14 — portfolio optimization & risk analytics tests."""
import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SINGLETONS = ["portfolio.engine", "risk_analytics.engine", "financial_hub.store",
               "quant_lab.factors"]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for m in _SINGLETONS:
        if m in sys.modules and hasattr(sys.modules[m], "_instance"):
            sys.modules[m]._instance = None


def _returns_matrix(n_assets=4, n_periods=120, seed=1):
    rng = np.random.default_rng(seed)
    return rng.normal(0.0005, 0.012, (n_assets, n_periods))


def _seed_prices(symbols, n=120, seed=3):
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    rng = np.random.default_rng(seed)
    for k, sym in enumerate(symbols):
        px = 100.0
        bars = []
        for i in range(n):
            px *= (1 + rng.normal(0.0005 + k * 0.0001, 0.013))
            bars.append({"date": f"2023-{(i//28)+1:02d}-{(i%28)+1:02d}", "close": round(px, 2), "volume": 1000})
        hub.store_prices(sym, bars, source="test")
    return hub


# ── optimization methods ─────────────────────────────────────────────────────

def test_equal_weight():
    from portfolio.optimize import equal_weight
    w = equal_weight(4)
    assert np.allclose(w, 0.25)
    assert abs(w.sum() - 1.0) < 1e-9


def test_minimum_variance_sums_to_one():
    from portfolio.optimize import minimum_variance
    w = minimum_variance(_returns_matrix())
    assert abs(w.sum() - 1.0) < 1e-6
    assert all(x >= -1e-9 for x in w)


def test_maximum_sharpe():
    from portfolio.optimize import maximum_sharpe
    w = maximum_sharpe(_returns_matrix())
    assert abs(w.sum() - 1.0) < 1e-6


def test_risk_parity_balances_risk():
    from portfolio.optimize import risk_parity
    r = _returns_matrix()
    w = risk_parity(r)
    assert abs(w.sum() - 1.0) < 1e-6
    cov = np.cov(r, ddof=1) * 252
    mrc = cov @ w
    rc = w * mrc
    rc = rc / rc.sum()
    # risk contributions should be reasonably balanced
    assert rc.std() < 0.15


def test_hierarchical_risk_parity():
    from portfolio.optimize import hierarchical_risk_parity
    w = hierarchical_risk_parity(_returns_matrix())
    assert abs(w.sum() - 1.0) < 1e-6
    assert all(x >= 0 for x in w)


def test_black_litterman():
    from portfolio.optimize import black_litterman
    r = _returns_matrix()
    w = black_litterman(r, market_weights=[0.25, 0.25, 0.25, 0.25])
    assert abs(w.sum() - 1.0) < 1e-6


def test_black_litterman_with_views():
    from portfolio.optimize import black_litterman
    r = _returns_matrix()
    views = {"P": [[1, 0, 0, 0]], "Q": [0.10], "omega_scale": 1.0}
    w = black_litterman(r, market_weights=[0.25] * 4, views=views)
    assert abs(w.sum() - 1.0) < 1e-6


def test_apply_constraints_max_weight():
    from portfolio.optimize import apply_constraints
    w = np.array([0.7, 0.2, 0.1])
    capped = apply_constraints(w, max_weight=0.4)
    assert capped.max() <= 0.4 + 1e-9
    assert abs(capped.sum() - 1.0) < 1e-9


def test_optimize_dispatch():
    from portfolio.optimize import optimize
    r = _returns_matrix()
    for method in ("equal_weight", "minimum_variance", "maximum_sharpe",
                   "risk_parity", "hierarchical_risk_parity"):
        w = optimize(method, r)
        assert abs(w.sum() - 1.0) < 1e-6


def test_optimize_unknown_raises():
    from portfolio.optimize import optimize
    with pytest.raises(ValueError):
        optimize("nonsense", _returns_matrix())


# ── portfolio engine ─────────────────────────────────────────────────────────

def test_construct_portfolio():
    from portfolio.engine import get_portfolio_engine
    _seed_prices(["AAA", "BBB", "CCC"])
    pe = get_portfolio_engine()
    pf = pe.construct("Test", ["AAA", "BBB", "CCC"], method="maximum_sharpe")
    assert pf["id"]
    assert abs(sum(pf["weights"].values()) - 1.0) < 1e-3
    assert "sharpe" in pf["stats"]


def test_construct_no_prices_falls_back():
    from portfolio.engine import get_portfolio_engine
    pe = get_portfolio_engine()
    pf = pe.construct("Empty", ["ZZZ", "YYY"], method="maximum_sharpe")
    assert abs(sum(pf["weights"].values()) - 1.0) < 1e-3


def test_rebalance_proposal():
    from portfolio.engine import get_portfolio_engine
    _seed_prices(["AAA", "BBB", "CCC"])
    pe = get_portfolio_engine()
    pf = pe.construct("Rebal", ["AAA", "BBB", "CCC"], method="equal_weight")
    prop = pe.propose_rebalance(pf["id"])
    assert "trades" in prop
    assert prop["status"] == "pending"


def test_portfolio_constraints():
    from portfolio.engine import get_portfolio_engine
    _seed_prices(["AAA", "BBB", "CCC", "DDD"])
    pe = get_portfolio_engine()
    pf = pe.construct("Capped", ["AAA", "BBB", "CCC", "DDD"], method="maximum_sharpe",
                      constraints={"max_weight": 0.4})
    assert max(pf["weights"].values()) <= 0.41


def test_portfolio_methods_list():
    from portfolio.engine import get_portfolio_engine
    methods = get_portfolio_engine().methods()
    ids = {m["id"] for m in methods}
    assert {"equal_weight", "risk_parity", "black_litterman"} <= ids


# ── risk analytics ───────────────────────────────────────────────────────────

def test_risk_analyze():
    from risk_analytics.engine import get_risk_engine
    _seed_prices(["AAA", "BBB", "CCC"])
    re = get_risk_engine()
    holdings = [{"symbol": "AAA", "weight": 0.5}, {"symbol": "BBB", "weight": 0.3},
                {"symbol": "CCC", "weight": 0.2}]
    rep = re.analyze(holdings, name="test")
    assert "var" in rep
    assert "expected_shortfall" in rep
    assert rep["health_score"] is not None
    assert 0 <= rep["health_score"] <= 100


def test_risk_concentration():
    from risk_analytics.engine import get_risk_engine
    re = get_risk_engine()
    w = np.array([0.6, 0.3, 0.1])
    conc = re.concentration(w, ["A", "B", "C"])
    assert conc["herfindahl"] == pytest.approx(0.46, abs=0.01)
    assert conc["max_position"]["symbol"] == "A"


def test_stress_test():
    from risk_analytics.engine import get_risk_engine
    _seed_prices(["AAA", "BBB"])
    re = get_risk_engine()
    holdings = [{"symbol": "AAA", "weight": 0.6}, {"symbol": "BBB", "weight": 0.4}]
    st = re.stress_test(holdings)
    assert len(st["scenarios"]) >= 5
    crisis = [s for s in st["scenarios"] if s["scenario_id"] == "2008_financial_crisis"][0]
    assert crisis["portfolio_pnl"] < 0


def test_scenario_analysis():
    from risk_analytics.engine import get_risk_engine
    _seed_prices(["AAA", "BBB"])
    re = get_risk_engine()
    holdings = [{"symbol": "AAA", "weight": 0.6}, {"symbol": "BBB", "weight": 0.4}]
    sc = re.scenario_analysis(holdings, {"market": -0.10})
    assert sc["portfolio_pnl"] == pytest.approx(-0.10, abs=0.01)


def test_correlation_analysis():
    from risk_analytics.engine import get_risk_engine
    re = get_risk_engine()
    matrix = _returns_matrix(3, 120)
    ca = re.correlation_analysis(matrix, ["A", "B", "C"])
    assert "avg_correlation" in ca
    assert ca["max_pair"] is not None


def test_scenarios_seeded():
    from risk_analytics.engine import get_risk_engine
    scen = get_risk_engine().scenarios()
    assert len(scen) >= 5
