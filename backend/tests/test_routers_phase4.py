"""API-level tests for the Phase-4 routers via FastAPI TestClient.

Uses an isolated in-memory-ish intel DB (temp file) so the accounting-intel
endpoints don't touch the real store, and exercises only offline-capable paths
(explicit prices/quotes), so no network is required.
"""
import os
import tempfile
import unittest

# Point the intel store at a throwaway DB before the app imports it.
_TMP = tempfile.mkdtemp()
os.environ["HELIOS_INTEL_DB"] = os.path.join(_TMP, "intel_test.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
RISING = [100 * 1.012 ** i for i in range(60)]


class AccountingIntelRoutes(unittest.TestCase):
    def test_briefing_generates(self):
        r = client.get("/accounting/briefing")
        self.assertEqual(r.status_code, 200)
        self.assertIn("executive_summary", r.json())
        self.assertIn("confidence", r.json())

    def test_graph(self):
        r = client.get("/accounting/graph")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["nodes"])

    def test_checklist_and_memo(self):
        self.assertEqual(client.post("/accounting/checklist", json={"topic": "606"}).status_code, 200)
        memo = client.post("/accounting/memo/full",
                           json={"facts": "Annual prepaid SaaS.", "issue": "Timing?", "topic": "606"})
        self.assertEqual(memo.status_code, 200)
        self.assertIn("ASC 606", memo.json()["references"])

    def test_intel_feed_empty_ok(self):
        r = client.get("/accounting/intel")
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())


class QuantResearchRoutes(unittest.TestCase):
    def test_fundamentals(self):
        r = client.post("/quant/fundamentals",
                        json={"symbol": "AAA", "fundamentals": {"price": 100, "eps": 5, "equity": 600, "net_income": 150}})
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.json()["ratios"]["pe"], 20.0)

    def test_signal(self):
        r = client.post("/quant/signal", json={"symbol": "AAA", "prices": RISING,
                                                "benchmark_prices": [100 * 1.004 ** i for i in range(60)],
                                                "fundamentals": {"pe": 12, "roe": 0.22}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["bias"], "bullish")

    def test_market_briefing(self):
        r = client.post("/market/briefing", json={"quotes": [
            {"symbol": "A", "changePercent": 2.0, "sector": "Tech"},
            {"symbol": "B", "changePercent": -1.0, "sector": "Energy"}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["market_overview"]["advancers"], 1)


class N8NRoutes(unittest.TestCase):
    def test_status_unconfigured(self):
        r = client.get("/n8n/status")
        self.assertEqual(r.status_code, 200)
        self.assertIn("connected", r.json())

    def test_generate_accounting_workflow(self):
        r = client.post("/n8n/generate", json={"name": "x", "kind": "accounting_briefing", "email_to": "a@b.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["nodes"]), 4)


if __name__ == "__main__":
    unittest.main()
