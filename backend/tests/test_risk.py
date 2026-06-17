import unittest

from app.services import risk


class RiskTest(unittest.TestCase):
    def test_correlation_identical_and_inverse(self):
        a = [0.01, -0.02, 0.03, -0.01, 0.02]
        self.assertAlmostEqual(risk.correlation(a, a), 1.0)
        self.assertAlmostEqual(risk.correlation(a, [-x for x in a]), -1.0)

    def test_beta_of_market_vs_itself(self):
        m = [0.01, -0.02, 0.03, -0.01, 0.02]
        self.assertAlmostEqual(risk.beta(m, m), 1.0)

    def test_sharpe_sign_and_zero_variance(self):
        self.assertGreater(risk.sharpe([0.02, 0.01, 0.015, 0.005, 0.02]), 0)
        self.assertIsNone(risk.sharpe([0.01, 0.01, 0.01]))  # zero variance → undefined

    def test_value_at_risk_positive_loss(self):
        var = risk.value_at_risk([-0.05, -0.03, 0.01, 0.02, 0.03, -0.10], 0.95)
        self.assertGreater(var, 0)

    def test_summarize_returns(self):
        prices = [100, 102, 101, 105, 103, 108, 107, 110]
        out = risk.summarize_returns(prices, benchmark_prices=prices)
        self.assertIn("annualized_volatility", out)
        self.assertAlmostEqual(out["correlation_vs_benchmark"], 1.0)
        self.assertAlmostEqual(out["beta_vs_benchmark"], 1.0)

    def test_portfolio_report(self):
        holdings = [
            {"symbol": "AAA", "weight": 1, "sector": "Tech", "prices": [10, 11, 10, 12]},
            {"symbol": "BBB", "weight": 1, "sector": "Energy", "prices": [20, 19, 21, 22]},
        ]
        rep = risk.portfolio_report(holdings)
        self.assertAlmostEqual(rep["concentration_hhi"], 0.5)
        self.assertAlmostEqual(rep["effective_positions"], 2.0)
        self.assertAlmostEqual(sum(rep["sector_exposure"].values()), 1.0, places=3)

    def test_empty_portfolio_raises(self):
        with self.assertRaises(ValueError):
            risk.portfolio_report([])


if __name__ == "__main__":
    unittest.main()
