"""API-level tests via FastAPI TestClient. Stays offline by passing explicit
price series rather than symbols, so no network is required."""
import unittest

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
RISING = [float(i) for i in range(1, 70)]


class ApiTest(unittest.TestCase):
    def test_health(self):
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_analyze_with_prices(self):
        r = client.post("/quant/analyze", json={"prices": RISING})
        self.assertEqual(r.status_code, 200)
        self.assertIn("rsi14", r.json())

    def test_analyze_requires_input(self):
        r = client.post("/quant/analyze", json={})
        self.assertEqual(r.status_code, 422)  # pydantic validation

    def test_factors(self):
        r = client.post("/quant/factors", json={"symbol": "AAA", "fundamentals": {"pe": 10, "roe": 0.2}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["symbol"], "AAA")

    def test_risk_with_prices(self):
        r = client.post("/quant/risk", json={"prices": RISING, "benchmark_prices": RISING})
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.json()["correlation_vs_benchmark"], 1.0)

    def test_portfolio(self):
        r = client.post("/quant/portfolio", json={"holdings": [
            {"symbol": "AAA", "weight": 1, "sector": "Tech"},
            {"symbol": "BBB", "weight": 1, "sector": "Energy"},
        ]})
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.json()["concentration_hhi"], 0.5)

    def test_accounting_asc_and_404(self):
        self.assertEqual(client.get("/accounting/asc/606").status_code, 200)
        self.assertEqual(client.get("/accounting/asc/zzz").status_code, 400)

    def test_memo(self):
        r = client.post("/accounting/memo", json={
            "issue": "Revenue timing?", "facts": "Annual prepaid SaaS.", "topic": "606"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["citations"], ["ASC 606"])


if __name__ == "__main__":
    unittest.main()
