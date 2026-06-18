"""API tests for the Phase-8 execution / automation operating system."""
import unittest

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class ExecutionRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client.post("/platform/coa/seed", params={"template": "general_small_business"})

    def test_propose_approve_execute(self):
        a = client.post("/exec/propose", json={"type": "create_journal_entry", "payload": {
            "date": "2025-04-01", "memo": "API JE",
            "lines": [{"account": "1000", "debit": 250}, {"account": "4000", "credit": 250}]}}).json()
        self.assertEqual(a["status"], "proposed")
        self.assertEqual(a["tier"], 2)
        # Cannot execute before approval.
        self.assertEqual(client.post(f"/exec/{a['id']}/execute").status_code, 400)
        client.post(f"/exec/{a['id']}/approve", json={})
        done = client.post(f"/exec/{a['id']}/execute").json()
        self.assertEqual(done["status"], "executed")

    def test_tier4_requires_confirm(self):
        a = client.post("/exec/propose", json={"type": "broker_action", "payload": {"symbol": "AAPL"}}).json()
        self.assertEqual(a["tier"], 4)
        client.post(f"/exec/{a['id']}/approve", json={})  # no confirm
        # Still proposed (approve without confirm 400s) → execute must 400.
        self.assertEqual(client.post(f"/exec/{a['id']}/execute").status_code, 400)
        client.post(f"/exec/{a['id']}/approve", json={"confirm": True})
        done = client.post(f"/exec/{a['id']}/execute").json()
        self.assertTrue(done["result"]["prepared"])

    def test_document_automation(self):
        r = client.post("/exec/automation/document", json={
            "text": "RECEIPT\nTotal: $30.00\nThank you for your purchase", "filename": "r.txt"}).json()
        self.assertEqual(r["proposed_action"]["status"], "proposed")
        self.assertEqual(r["proposed_action"]["type"], "create_journal_entry")

    def test_close_flow(self):
        client.post("/close/start", params={"period": "2025-04"})
        client.post("/close/update", json={"period": "2025-04", "key": "journal_entries", "status": "done"})
        self.assertGreaterEqual(client.get("/close/dashboard").json()["count"], 1)
        pkg = client.get("/close/2025-04/package").json()
        self.assertTrue(pkg["trial_balance"]["balanced"])

    def test_outcomes_and_ops(self):
        rec = client.post("/outcomes/recommendation", json={"agent": "advisory", "summary": "x", "confidence": 0.7}).json()
        client.post("/outcomes/outcome", json={"recommendation_id": rec["id"], "success": True})
        self.assertGreaterEqual(client.get("/outcomes/metrics").json()["recommendations"], 1)
        self.assertIn("clients", client.get("/ops/firm").json())
        self.assertIn("approval_queue", client.get("/ops/portfolio").json())

    def test_workflow_builder(self):
        plan = client.post("/workflow/build", json={"kind": "month_end_close", "email_to": "c@firm.com"}).json()
        self.assertTrue(plan["execution_plan"])
        self.assertTrue(plan["approvals_required"])


if __name__ == "__main__":
    unittest.main()
