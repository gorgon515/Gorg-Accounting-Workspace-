import unittest

from quant import technicals as ta
from quant import fundamentals as fa
from quant import signals
from quant.market_briefing import generate_market_briefing


class TechnicalsExtTest(unittest.TestCase):
    def test_atr(self):
        closes = [float(i) for i in range(1, 31)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        self.assertAlmostEqual(ta.atr(highs, lows, closes, 14), 2.0)

    def test_relative_strength(self):
        rs = ta.relative_strength([100 * 1.01 ** i for i in range(70)],
                                  [100 * 1.005 ** i for i in range(70)], window=63)
        self.assertTrue(rs["outperforming"])
        self.assertGreater(rs["excess"], 0)

    def test_scores(self):
        rising = [float(i) for i in range(1, 60)]
        self.assertGreater(ta.momentum_score(rising), 50)
        self.assertGreaterEqual(ta.trend_score(rising), 65)

    def test_volume(self):
        v = ta.volume_analysis([100] * 10 + [200] * 10, 20)
        self.assertEqual(v["trend"], "rising")
        self.assertGreater(v["relative_volume"], 1)

    def test_analyze_extended(self):
        out = ta.analyze_extended([float(i) for i in range(1, 60)])
        self.assertIn("momentum_score", out)
        self.assertIn("trend_score", out)
        self.assertIsInstance(out["explanations"], list)


class FundamentalsTest(unittest.TestCase):
    F = {"price": 100, "eps": 5, "revenue": 1000, "net_income": 150, "equity": 600,
         "gross_profit": 600, "operating_income": 200, "market_cap": 10000, "fcf": 500,
         "total_debt": 120, "current_assets": 500, "current_liabilities": 250}

    def test_ratios(self):
        r = fa.ratios(self.F)["ratios"]
        self.assertAlmostEqual(r["pe"], 20.0)
        self.assertAlmostEqual(r["roe"], 0.25)
        self.assertAlmostEqual(r["net_margin"], 0.15)
        self.assertAlmostEqual(r["current_ratio"], 2.0)

    def test_growth(self):
        g = fa.growth({"revenue": [100, 120, 150]})
        self.assertAlmostEqual(g["revenue"]["yoy"], 0.25)
        self.assertAlmostEqual(g["revenue"]["cagr"], (150 / 100) ** 0.5 - 1, places=4)

    def test_quality(self):
        q = fa.quality_metrics(self.F)
        self.assertIsNotNone(q["quality_score"])
        self.assertTrue(0 <= q["quality_score"] <= 100)

    def test_peers(self):
        target = {"symbol": "T", "pe": 12, "roe": 0.22}
        peers = [{"pe": 20, "roe": 0.1}, {"pe": 30, "roe": 0.05}, {"pe": 18, "roe": 0.15}]
        pc = fa.peer_comparison(target, peers, ["pe", "roe"])
        self.assertIn("pe", pc["metrics"])
        self.assertEqual(pc["peers"], 3)


class SignalsTest(unittest.TestCase):
    def test_generate_signal(self):
        prices = [100 * 1.012 ** i for i in range(60)]
        bench = [100 * 1.004 ** i for i in range(60)]
        fund = {"pe": 12, "roe": 0.22, "revenue_growth": 0.25, "net_margin": 0.2, "gross_margin": 0.6}
        sig = signals.generate_signal("AAA", prices, fundamentals=fund, benchmark=bench, sector="Tech")
        self.assertEqual(sig["bias"], "bullish")
        self.assertIn("confidence", sig)
        self.assertTrue(0 <= sig["confidence"]["score"] <= 100)
        for k in ("facts", "calculations", "interpretations", "forecasts"):
            self.assertIn(k, sig["evidence"])
        self.assertTrue(sig["bull_case"])

    def test_requires_minimum_data(self):
        with self.assertRaises(ValueError):
            signals.generate_signal("X", [1, 2, 3])


class MarketBriefingTest(unittest.TestCase):
    QUOTES = [
        {"symbol": "A", "changePercent": 3.0, "sector": "Tech"},
        {"symbol": "B", "changePercent": -2.0, "sector": "Energy"},
        {"symbol": "C", "changePercent": 1.0, "sector": "Tech"},
    ]

    def test_overview_and_movers(self):
        b = generate_market_briefing(self.QUOTES)
        self.assertEqual(b["market_overview"]["advancers"], 2)
        self.assertEqual(b["market_overview"]["decliners"], 1)
        self.assertEqual(b["top_movers"]["gainers"][0]["symbol"], "A")
        self.assertEqual(b["top_movers"]["losers"][0]["symbol"], "B")
        self.assertEqual(b["sector_rotation"][0]["sector"], "Tech")
        self.assertTrue(any(o["symbol"] == "A" for o in b["opportunities"]))

    def test_portfolio_risks(self):
        b = generate_market_briefing(self.QUOTES, portfolio=[
            {"symbol": "A", "value": 60, "sector": "Tech"},
            {"symbol": "B", "value": 40, "sector": "Energy"}])
        self.assertAlmostEqual(b["portfolio_risks"]["concentration_hhi"], 0.52)


if __name__ == "__main__":
    unittest.main()
