import unittest

from app.services import technicals as ta


class TechnicalsTest(unittest.TestCase):
    def test_sma(self):
        self.assertAlmostEqual(ta.sma([1, 2, 3, 4, 5], 5), 3.0)
        self.assertAlmostEqual(ta.sma([2, 4, 6], 2), 5.0)

    def test_ema_constant_series(self):
        self.assertAlmostEqual(ta.ema([5] * 10, 3), 5.0)

    def test_rsi_bounds(self):
        self.assertAlmostEqual(ta.rsi(list(range(1, 30)), 14), 100.0)      # all gains
        self.assertAlmostEqual(ta.rsi(list(range(30, 1, -1)), 14), 0.0)    # all losses

    def test_macd_structure_and_sign(self):
        rising = [float(i) for i in range(1, 80)]
        m = ta.macd(rising)
        self.assertEqual(set(m), {"macd", "signal", "histogram"})
        self.assertGreater(m["macd"], 0)  # fast EMA above slow EMA on an uptrend

    def test_bollinger_ordering(self):
        b = ta.bollinger([float(i) for i in range(1, 41)], 20, 2)
        self.assertGreater(b["upper"], b["middle"])
        self.assertGreater(b["middle"], b["lower"])
        const = ta.bollinger([7.0] * 25, 20, 2)
        self.assertEqual(const["upper"], const["lower"])
        self.assertAlmostEqual(const["percent_b"], 0.5)

    def test_momentum(self):
        self.assertAlmostEqual(ta.momentum([10] * 20 + [12], 20), 0.2)

    def test_volatility_constant_is_zero(self):
        self.assertEqual(ta.volatility([3.0] * 10), 0.0)

    def test_max_drawdown(self):
        self.assertAlmostEqual(ta.max_drawdown([10, 12, 6, 9])["max_drawdown"], 0.5)

    def test_analyze_smoke(self):
        out = ta.analyze([float(i) for i in range(1, 61)])
        self.assertEqual(out["trend"], "up")
        self.assertIn("rsi14", out)
        self.assertIsInstance(out["signals"], list)

    def test_insufficient_data_raises(self):
        with self.assertRaises(ValueError):
            ta.sma([1, 2], 5)


if __name__ == "__main__":
    unittest.main()
