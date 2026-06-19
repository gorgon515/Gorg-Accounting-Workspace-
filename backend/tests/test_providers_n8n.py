import unittest

from app.services.providers import FMPProvider, AlphaVantageProvider, SECFilingsProvider
from app.services.market_data import MarketData, DataUnavailable
from n8n.client import N8NClient
from n8n import generator


class ProviderNormalizeTest(unittest.TestCase):
    def test_fmp_quote(self):
        raw = [{"symbol": "AAPL", "price": 224.1, "change": 1.8, "changesPercentage": 0.81}]
        q = FMPProvider.normalize_quote(raw)
        self.assertEqual(q["symbol"], "AAPL")
        self.assertEqual(q["price"], 224.1)
        self.assertEqual(q["source"], "fmp")

    def test_alpha_vantage_quote(self):
        raw = {"Global Quote": {"01. symbol": "MSFT", "05. price": "410.50",
                                "09. change": "2.10", "10. change percent": "0.51%"}}
        q = AlphaVantageProvider.normalize_quote(raw)
        self.assertEqual(q["symbol"], "MSFT")
        self.assertAlmostEqual(q["price"], 410.5)
        self.assertAlmostEqual(q["change_percent"], 0.51)

    def test_alpha_vantage_history(self):
        raw = {"Meta Data": {"2. Symbol": "IBM"},
               "Time Series (Daily)": {"2025-01-02": {"4. close": "200.0"},
                                       "2025-01-03": {"4. close": "202.5"}}}
        h = AlphaVantageProvider.normalize_history(raw)
        self.assertEqual(h["prices"], [200.0, 202.5])  # chronological

    def test_sec_filings(self):
        raw = {"name": "Apple Inc.", "cik": 320193,
               "filings": {"recent": {"form": ["10-K", "8-K"],
                                      "filingDate": ["2024-11-01", "2024-10-15"],
                                      "accessionNumber": ["a1", "a2"],
                                      "primaryDocument": ["aapl-10k.htm", "aapl-8k.htm"]}}}
        f = SECFilingsProvider.normalize_filings(raw, limit=5)
        self.assertEqual(f["entity"], "Apple Inc.")
        self.assertEqual(len(f["filings"]), 2)
        self.assertEqual(f["filings"][0]["form"], "10-K")

    def test_missing_keys_raise(self):
        with self.assertRaises(DataUnavailable):
            AlphaVantageProvider.normalize_quote({"Global Quote": {}})


class FreshnessTest(unittest.TestCase):
    def test_stale_detection(self):
        md = MarketData(quote_ttl=30, history_ttl=900)
        # Never fetched → considered stale.
        self.assertTrue(md.is_stale("q:AAPL"))
        # Simulate a recent refresh.
        md._mark("q:AAPL")
        self.assertFalse(md.is_stale("q:AAPL"))
        fr = md.freshness()
        self.assertIn("q:AAPL", fr)
        self.assertFalse(fr["q:AAPL"]["stale"])


class N8NClientTest(unittest.TestCase):
    def test_url_and_headers(self):
        c = N8NClient(base_url="http://localhost:5678/", api_key="secret")
        self.assertEqual(c.url("workflows"), "http://localhost:5678/api/v1/workflows")
        self.assertEqual(c.headers["X-N8N-API-KEY"], "secret")
        self.assertTrue(c.configured)

    def test_status_unconfigured(self):
        c = N8NClient(base_url="http://localhost:5678", api_key="")
        st = c.status()
        self.assertFalse(st["connected"])
        self.assertIn("reason", st)


class WorkflowGeneratorTest(unittest.TestCase):
    def test_accounting_briefing_workflow(self):
        wf = generator.accounting_briefing_workflow(email_to="cpa@firm.com")
        self.assertEqual(len(wf["nodes"]), 4)
        types = [n["type"] for n in wf["nodes"]]
        self.assertEqual(types[0], "n8n-nodes-base.scheduleTrigger")
        self.assertIn("n8n-nodes-base.httpRequest", types)
        self.assertIn("n8n-nodes-base.emailSend", types)
        # Connections form a linear pipeline across all nodes.
        self.assertEqual(len(wf["connections"]), 3)
        # The HTTP node targets the HELIOS briefing endpoint.
        http = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")
        self.assertIn("/accounting/briefing", http["parameters"]["url"])

    def test_from_spec(self):
        wf = generator.from_spec({"name": "Test", "collect_url": "http://x/data",
                                  "email_to": "a@b.com", "schedule": "0 9 * * 1"})
        self.assertEqual(wf["name"], "Test")
        self.assertTrue(any(n["type"] == "n8n-nodes-base.httpRequest" for n in wf["nodes"]))
        self.assertEqual(wf["active"], False)


if __name__ == "__main__":
    unittest.main()
