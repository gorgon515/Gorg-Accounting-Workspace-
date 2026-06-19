"""API tests for the Phase-7 workbench router (shares the platform DB via conftest)."""
import unittest

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class WorkbenchRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client.post("/platform/coa/seed", params={"template": "general_small_business"})
        # Give the books some data for workpapers/analysis.
        cust = client.post("/platform/ar/customer", json={"name": "Workbench Co"}).json()
        client.post("/platform/ar/invoice", json={"customer_id": cust["id"], "amount": 8000, "invoice_date": "2025-02-01"})

    def test_ocr_status_honest(self):
        st = client.get("/workbench/docs/ocr-status").json()
        self.assertIn("tesseract", st)  # truthfully reports availability

    def test_process_document(self):
        r = client.post("/workbench/docs/process", json={
            "text": "INVOICE\nInvoice Number: INV-9\nTotal Amount Due: $500.00", "filename": "inv.txt", "save": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["doc_type"], "invoice")
        self.assertAlmostEqual(r.json()["fields"]["total"], 500.0)

    def test_tax_research_and_memo(self):
        r = client.post("/workbench/tax/research", json={"query": "home office"})
        self.assertEqual(r.json()["authorities"][0]["cite"], "IRC §280A")
        memo = client.post("/workbench/tax/memo", json={"facts": "f", "issues": "i", "topic": "home office"})
        self.assertIn("IRC §280A", memo.json()["references"])

    def test_tax_organizer(self):
        c = client.post("/workbench/tax/organizer/client", json={"name": "Org Client", "entity_type": "individual"}).json()
        self.assertTrue(len(c["documents"]) > 5)
        self.assertGreaterEqual(client.get("/workbench/tax/organizer/dashboard").json()["count"], 1)

    def test_workpapers(self):
        tb = client.get("/workbench/workpapers/trial-balance").json()
        self.assertTrue(tb["tie_out"])
        lead = client.get("/workbench/workpapers/lead/asset").json()
        self.assertIn("rows", lead)

    def test_advisory(self):
        a = client.get("/workbench/advisory/analysis", params={"as_of": "2025-12-31"}).json()
        self.assertIn("ratios", a)
        dd = client.get("/workbench/advisory/due-diligence", params={"year": 2025}).json()
        self.assertIn("risks", dd)

    def test_global_search(self):
        res = client.get("/workbench/search", params={"q": "invoice"}).json()
        self.assertGreaterEqual(res["count"], 1)


if __name__ == "__main__":
    unittest.main()
