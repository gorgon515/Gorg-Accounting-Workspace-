import unittest

from accounting_platform import db, coa, gl
from execution.engine import ExecutionEngine
from execution import automation
from operations.close import CloseStore, close_package
from outcomes.engine import OutcomeStore
from document_intelligence import pipeline


def _acct():
    conn = db.connect(":memory:")
    coa.seed_template(conn, "general_small_business")
    return conn


class ApprovalExecutionTest(unittest.TestCase):
    def setUp(self):
        self.acct = _acct()
        self.eng = ExecutionEngine(":memory:", context={"acct_conn": self.acct})

    def tearDown(self):
        self.eng.close()
        self.acct.close()

    def test_tier2_requires_approval_before_execution(self):
        a = self.eng.propose("create_journal_entry", {
            "date": "2025-03-01", "memo": "Test",
            "lines": [{"account": "1000", "debit": 100}, {"account": "4000", "credit": 100}]})
        self.assertEqual(a["tier"], 2)
        self.assertEqual(a["status"], "proposed")
        with self.assertRaises(ValueError):
            self.eng.execute(a["id"])  # not approved yet
        self.eng.approve(a["id"])
        done = self.eng.execute(a["id"])
        self.assertEqual(done["status"], "executed")
        # The entry actually posted to the GL.
        self.assertAlmostEqual(gl.account_balance(self.acct, coa.by_number(self.acct, "1000")["id"])["balance"], 100)

    def test_rollback_reverses_gl(self):
        a = self.eng.propose("create_journal_entry", {
            "date": "2025-03-02", "memo": "Reversible",
            "lines": [{"account": "5200", "debit": 50}, {"account": "1000", "credit": 50}]})
        self.eng.approve(a["id"]); self.eng.execute(a["id"])
        self.eng.rollback(a["id"])
        self.assertEqual(self.eng.get(a["id"])["status"], "rolled_back")
        self.assertAlmostEqual(gl.account_balance(self.acct, coa.by_number(self.acct, "5200")["id"])["balance"], 0)

    def test_tier1_auto_execute(self):
        a = self.eng.propose("create_task", {"title": "Follow up"}, auto=True)
        self.assertEqual(a["tier"], 1)
        self.assertEqual(a["status"], "executed")

    def test_tier4_never_auto_and_requires_confirm(self):
        a = self.eng.propose("broker_action", {"symbol": "AAPL", "side": "buy", "qty": 10})
        self.assertEqual(a["tier"], 4)
        # Cannot auto-execute even if asked.
        b = self.eng.propose("tax_filing", {"form": "1120"}, auto=True)
        self.assertEqual(b["status"], "proposed")  # auto ignored for tier 4
        with self.assertRaises(ValueError):
            self.eng.approve(a["id"])  # needs confirm=True
        self.eng.approve(a["id"], confirm=True)
        done = self.eng.execute(a["id"])
        # Executed = PREPARED only; HELIOS never performs the external action.
        self.assertTrue(done["result"]["prepared"])
        self.assertEqual(done["result"]["status"], "awaiting_external_submission")

    def test_reject_and_failure(self):
        a = self.eng.propose("create_journal_entry", {
            "date": "2025-03-03", "lines": [{"account": "1000", "debit": 10}, {"account": "4000", "credit": 9}]})
        self.eng.approve(a["id"])
        failed = self.eng.execute(a["id"])  # unbalanced → executor raises
        self.assertEqual(failed["status"], "failed")
        self.assertIn("balanced", failed["error"])
        r = self.eng.propose("create_note", {"note": "x"})
        self.assertEqual(self.eng.reject(r["id"], "not needed")["status"], "rejected")

    def test_audit_and_queue(self):
        a = self.eng.propose("create_ar_invoice", {"customer_id": 1, "amount": 100, "invoice_date": "2025-03-01"})
        events = [e["event"] for e in a["audit"]]
        self.assertIn("proposed", events)
        self.assertIn("create_ar_invoice", [p["type"] for p in self.eng.queue_summary()["pending_approval"]])


class DocumentAutomationTest(unittest.TestCase):
    def test_receipt_to_draft_entry(self):
        acct = _acct()
        eng = ExecutionEngine(":memory:", context={"acct_conn": acct})
        result = pipeline.process_text("RECEIPT\nStore Mart\nSubtotal: $40.00\nTotal: $42.50\n"
                                       "Thank you for your purchase", "receipt.txt")
        action = automation.propose_from_document(eng, result)
        self.assertEqual(action["type"], "create_journal_entry")
        self.assertEqual(action["status"], "proposed")  # awaits approval
        eng.approve(action["id"]); done = eng.execute(action["id"])
        self.assertEqual(done["status"], "executed")
        eng.close(); acct.close()


class CloseTest(unittest.TestCase):
    def test_close_checklist_and_package(self):
        store = CloseStore(":memory:")
        p = store.start("2025-03")
        self.assertEqual(p["progress"], 0)
        for item in p["checklist"]:
            store.update_item("2025-03", item["key"], "done")
        self.assertTrue(store.get("2025-03")["ready_to_close"])
        acct = _acct()
        gl.create_entry(acct, "2025-03-10", [{"account": "1000", "debit": 500}, {"account": "4000", "credit": 500}])
        pkg = close_package(acct, "2025-03")
        self.assertTrue(pkg["trial_balance"]["balanced"])
        self.assertTrue(pkg["balance_sheet"]["balanced"])
        store.close_db(); acct.close()


class OutcomesTest(unittest.TestCase):
    def test_tracking_and_learning(self):
        store = OutcomeStore(":memory:")
        r1 = store.record_recommendation("quant", "Buy idea", confidence=0.9)
        store.record_outcome(r1["id"], success=False)
        r2 = store.record_recommendation("quant", "Hold idea", confidence=0.6)
        store.record_outcome(r2["id"], success=True, satisfaction=5)
        m = store.metrics()
        self.assertEqual(m["recommendations"], 2)
        self.assertAlmostEqual(m["overall_accuracy"], 0.5)
        quant = next(a for a in m["by_agent"] if a["agent"] == "quant")
        self.assertIsNotNone(quant["suggested_confidence_adjustment"])  # calibration feedback
        store.close()


if __name__ == "__main__":
    unittest.main()
