"""Phase 14 — performance metrics & backtesting engine tests."""
import math
import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SINGLETONS = ["backtesting.engine"]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for m in _SINGLETONS:
        if m in sys.modules and hasattr(sys.modules[m], "_instance"):
            sys.modules[m]._instance = None


# ── metrics ──────────────────────────────────────────────────────────────────

def test_cagr_positive():
    from backtesting.metrics import cagr
    rets = [0.01] * 252  # ~1%/day for a year
    c = cagr(rets)
    assert c is not None and c > 0


def test_sharpe_known():
    from backtesting.metrics import sharpe
    rng = np.random.default_rng(1)
    rets = list(rng.normal(0.0008, 0.01, 252))
    s = sharpe(rets)
    assert s is not None


def test_sortino_uses_downside():
    from backtesting.metrics import sortino, sharpe
    rets = [0.01, -0.02, 0.015, -0.01, 0.02, 0.005] * 10
    assert sortino(rets) is not None


def test_max_drawdown_negative():
    from backtesting.metrics import max_drawdown
    rets = [0.1, -0.5, 0.1, 0.1]
    mdd = max_drawdown(rets)
    assert mdd < 0


def test_calmar():
    from backtesting.metrics import calmar
    rng = np.random.default_rng(2)
    rets = list(rng.normal(0.001, 0.01, 252))
    assert calmar(rets) is not None


def test_beta_of_self_is_one():
    from backtesting.metrics import beta
    rng = np.random.default_rng(3)
    m = list(rng.normal(0, 0.01, 100))
    b = beta(m, m)
    assert abs(b - 1.0) < 1e-6


def test_alpha_zero_for_market():
    from backtesting.metrics import alpha
    rng = np.random.default_rng(4)
    m = list(rng.normal(0.0005, 0.01, 200))
    a = alpha(m, m)
    assert abs(a) < 1e-6


def test_information_ratio():
    from backtesting.metrics import information_ratio
    rng = np.random.default_rng(5)
    r = list(rng.normal(0.001, 0.01, 200))
    b = list(rng.normal(0.0005, 0.01, 200))
    assert information_ratio(r, b) is not None


def test_hit_rate_bounds():
    from backtesting.metrics import hit_rate
    assert hit_rate([1, -1, 1, 1]) == 0.75


def test_profit_factor():
    from backtesting.metrics import profit_factor
    assert profit_factor([0.1, -0.05, 0.1]) == pytest.approx(4.0)


def test_value_at_risk_and_es():
    from backtesting.metrics import value_at_risk, expected_shortfall
    rng = np.random.default_rng(6)
    rets = list(rng.normal(0, 0.02, 1000))
    var = value_at_risk(rets, 0.95)
    es = expected_shortfall(rets, 0.95)
    assert var is not None and es is not None
    assert es <= var  # ES is deeper in the tail


def test_full_report_keys():
    from backtesting.metrics import full_report
    rng = np.random.default_rng(8)
    rets = list(rng.normal(0.001, 0.01, 252))
    bench = list(rng.normal(0.0005, 0.01, 252))
    rep = full_report(rets, bench)
    for k in ("cagr", "sharpe", "sortino", "calmar", "max_drawdown", "alpha",
              "beta", "information_ratio", "treynor", "hit_rate", "profit_factor"):
        assert k in rep


def test_metrics_short_series_returns_none():
    from backtesting.metrics import sharpe, cagr
    assert sharpe([0.01]) is None
    assert cagr([]) is None


# ── backtesting engine ───────────────────────────────────────────────────────

def test_simulate_basic():
    from backtesting.engine import simulate
    rng = np.random.default_rng(10)
    rets = list(rng.normal(0.001, 0.01, 100))
    sig = [1.0] * 100
    out = simulate(sig, rets)
    assert "metrics" in out
    assert len(out["equity_curve"]) == 100
    assert out["final_equity"] > 0


def test_costs_reduce_returns():
    from backtesting.engine import simulate, CostModel
    rng = np.random.default_rng(11)
    rets = list(rng.normal(0.001, 0.01, 100))
    sig = [1.0 if i % 2 == 0 else 0.0 for i in range(100)]  # high turnover
    cheap = simulate(sig, rets, CostModel(0, 0))
    pricey = simulate(sig, rets, CostModel(5, 20))
    assert pricey["final_equity"] < cheap["final_equity"]


def test_walk_forward():
    from backtesting.engine import walk_forward
    rng = np.random.default_rng(12)
    rets = list(rng.normal(0.001, 0.01, 200))
    sig = [1.0] * 200
    wf = walk_forward(sig, rets, n_splits=4)
    assert len(wf["folds"]) == 4
    assert "mean_oos_sharpe" in wf


def test_monte_carlo():
    from backtesting.engine import monte_carlo
    rng = np.random.default_rng(13)
    rets = list(rng.normal(0.001, 0.01, 100))
    mc = monte_carlo(rets, n_sims=300)
    assert mc["n_sims"] == 300
    assert 0.0 <= mc["terminal_return"]["prob_loss"] <= 1.0


def test_sensitivity():
    from backtesting.engine import sensitivity_analysis
    rng = np.random.default_rng(14)
    rets = list(rng.normal(0.001, 0.01, 100))
    sig = [1.0] * 100
    s = sensitivity_analysis(sig, rets)
    assert len(s["results"]) == 5


def test_position_sizing_vol_target():
    from backtesting.engine import position_sizing
    rng = np.random.default_rng(15)
    rets = list(rng.normal(0, 0.02, 100))
    w = position_sizing([1.0] * 100, target_vol=0.10, asset_returns=rets)
    assert all(-1.0 <= x <= 1.0 for x in w)


def test_backtester_persist_and_list():
    from backtesting.engine import get_backtester
    bt = get_backtester()
    rng = np.random.default_rng(16)
    rets = list(rng.normal(0.001, 0.01, 100))
    res = bt.run("persist test", [1.0] * 100, rets, strategy_id="s1")
    assert res["id"]
    runs = bt.list_runs(strategy_id="s1")
    assert len(runs) >= 1
    fetched = bt.get_run(res["id"])
    assert fetched["name"] == "persist test"


def test_benchmark_compare():
    from backtesting.engine import benchmark_compare
    rng = np.random.default_rng(17)
    strat = list(rng.normal(0.001, 0.01, 100))
    bench = list(rng.normal(0.0005, 0.01, 100))
    cmp = benchmark_compare(strat, bench)
    assert "strategy" in cmp and "benchmark" in cmp and "excess_return" in cmp
