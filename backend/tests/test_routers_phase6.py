"""API tests for the accounting-platform router (isolated DB)."""
import os
import tempfile
import unittest

os.environ["HELIOS_ACCT_DB"] = os.path.join(tempfile.mkdtemp(), "acct_test.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


class PlatformRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client.post("/platform/coa/seed", params={"template": "tax_firm"})

    def test_seed_and_chart(self):
        chart = client.get("/platform/coa").json()
        self.assertTrue(len(chart["accounts"]) > 10)
        self.assertIn("tax_firm", chart["templates"])

    def test_journal_and_trial_balance(self):
        r = client.post("/platform/journal", json={
            "date": "2025-04-01", "memo": "Owner funding",
            "lines": [{"account": "1000", "debit": 5000}, {"account": "3000", "credit": 5000}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "posted")
        tb = client.get("/platform/trial-balance").json()
        self.assertTrue(tb["balanced"])

    def test_unbalanced_rejected_400(self):
        r = client.post("/platform/journal", json={
            "date": "2025-04-02", "lines": [{"account": "1000", "debit": 10}, {"account": "4000", "credit": 9}]})
        self.assertEqual(r.status_code, 400)

    def test_ar_flow_and_statements(self):
        cust = client.post("/platform/ar/customer", json={"name": "Acme"}).json()
        client.post("/platform/ar/invoice", json={"customer_id": cust["id"], "amount": 2000, "invoice_date": "2025-04-03"})
        self.assertAlmostEqual(client.get("/platform/ar/aging").json()["total"], 2000)
        bs = client.get("/platform/statements/balance-sheet").json()
        self.assertTrue(bs["balanced"])

    def test_fixed_asset_schedule(self):
        a = client.post("/platform/assets", json={"name": "Server", "acquired_on": "2025-01-01", "cost": 6000, "life_months": 12}).json()
        sched = client.get(f"/platform/assets/{a['id']}/schedule").json()
        self.assertAlmostEqual(sched["total_depreciation"], 6000)

    def test_dashboard_and_audit(self):
        ov = client.get("/platform/dashboard").json()
        self.assertIn("cash_position", ov)
        self.assertTrue(ov["balance_sheet_summary"]["balanced"])
        self.assertTrue(client.get("/platform/audit").json()["events"])


if __name__ == "__main__":
    unittest.main()
