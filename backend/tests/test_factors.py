import unittest

from app.services import factors


class FactorsTest(unittest.TestCase):
    GREAT = {
        "pe": 8, "peg": 0.8, "pb": 1.0, "ps": 1.0, "fcf_yield": 0.08,
        "roe": 0.25, "roic": 0.20, "gross_margin": 0.60, "net_margin": 0.25,
        "debt_to_equity": 0.2, "current_ratio": 2.5,
        "revenue_growth": 0.30, "earnings_growth": 0.30, "fcf_growth": 0.25,
    }
    POOR = {
        "pe": 40, "peg": 3.0, "pb": 8.0, "ps": 12.0, "fcf_yield": 0.0,
        "roe": 0.0, "roic": 0.0, "gross_margin": 0.10, "net_margin": 0.0,
        "debt_to_equity": 2.5, "current_ratio": 0.8,
        "revenue_growth": -0.05, "earnings_growth": -0.10, "fcf_growth": -0.10,
    }

    def test_value_extremes(self):
        self.assertEqual(factors.value_score(self.GREAT)[0], 100.0)
        self.assertEqual(factors.value_score(self.POOR)[0], 0.0)

    def test_composite_ordering_and_bounds(self):
        good = factors.score("AAA", self.GREAT)["composite"]
        bad = factors.score("BBB", self.POOR)["composite"]
        self.assertGreater(good, bad)
        self.assertTrue(0 <= bad <= good <= 100)

    def test_partial_coverage(self):
        out = factors.score("CCC", {"pe": 10})
        self.assertEqual(out["coverage"]["factors_scored"], 1)  # only value has data
        self.assertEqual(out["factors"]["growth"]["score"], None)

    def test_momentum_needs_prices(self):
        self.assertEqual(factors.momentum_score(None)[0], None)
        up = factors.momentum_score([float(i) for i in range(1, 300)])[0]
        self.assertGreater(up, 50)  # strong uptrend scores above neutral

    def test_rating_labels(self):
        self.assertEqual(factors.rate(90), "strong")
        self.assertEqual(factors.rate(None), "n/a")
        self.assertEqual(factors.rate(10), "poor")


if __name__ == "__main__":
    unittest.main()
