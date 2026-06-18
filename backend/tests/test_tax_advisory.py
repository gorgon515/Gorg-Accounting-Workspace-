import unittest

from tax_research import engine as tax
from tax_research.organizer import TaxOrganizer
from workpapers import engine as wp
from advisory import fs_analysis, due_diligence
import global_search
from accounting_platform import db, coa, ar, ap, gl
from document_intelligence import pipeline
from document_intelligence.store import DocStore


class TaxResearchTest(unittest.TestCase):
    def test_research_and_hierarchy(self):
        r = tax.research("home office")
        self.assertEqual(r["authorities"][0]["cite"], "IRC §280A")  # statute ranks first
        self.assertGreaterEqual(r["authorities"][0]["weight"], r["authorities"][-1]["weight"])
        self.assertTrue(r["planning_opportunities"])

    def test_resolve_by_keyword(self):
        self.assertEqual(tax.research("199A deduction")["topic"], "qbi")
        with self.assertRaises(ValueError):
            tax.research("how do I cook pasta")

    def test_memo(self):
        memo = tax.generate_memo("Client works from a dedicated home office.",
                                 "Is the home office deductible?", "home office")
        for k in ("facts", "issues", "authorities", "analysis", "alternatives",
                  "conclusion", "recommendations", "references"):
            self.assertIn(k, memo)
        self.assertIn("IRC §280A", memo["references"])


class TaxOrganizerTest(unittest.TestCase):
    def test_organizer(self):
        org = TaxOrganizer(":memory:")
        c = org.add_client("Jane Doe", entity_type="individual", tax_year=2024)
        self.assertTrue(len(c["documents"]) > 5)
        missing = org.missing_documents(c["id"])
        self.assertEqual(len(missing), len(c["documents"]))
        org.mark_received(missing[0]["id"])
        self.assertEqual(len(org.missing_documents(c["id"])), len(missing) - 1)
        self.assertEqual(org.dashboard()["count"], 1)
        org.close()


class WorkpapersAdvisoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        coa.seed_template(self.conn, "general_small_business")
        cust = ar.add_customer(self.conn, "BigCo")
        inv = ar.add_invoice(self.conn, cust["id"], 10000, "2025-02-01")
        ar.record_payment(self.conn, inv["id"], 6000, "2025-03-01")
        v = ap.add_vendor(self.conn, "Supplier")
        ap.add_bill(self.conn, v["id"], 3000, "2025-02-15", "5100")
        gl.create_entry(self.conn, "2025-01-05",
                        [{"account": "1000", "debit": 5000}, {"account": "3000", "credit": 5000}], memo="Owner")

    def tearDown(self):
        self.conn.close()

    def test_workpapers(self):
        tbwp = wp.trial_balance_workpaper(self.conn, "2025-12-31")
        self.assertTrue(tbwp["tie_out"])
        lead = wp.lead_schedule(self.conn, "asset", "2025-12-31")
        self.assertAlmostEqual(lead["subtotal"], 15000)  # 11000 cash + 4000 AR
        taxwp = wp.tax_workpaper(self.conn, 2025)
        self.assertAlmostEqual(taxwp["book_net_income"], 7000)
        store = wp.WorkpaperStore(self.conn)
        saved = store.save(tbwp)
        self.assertEqual(saved["version"], 1)

    def test_fs_analysis(self):
        a = fs_analysis.analyze(self.conn, "2025-12-31", 2025)
        self.assertAlmostEqual(a["ratios"]["liquidity"]["current_ratio"], 5.0)
        self.assertIn("executive", a["summaries"])

    def test_due_diligence(self):
        r = due_diligence.report(self.conn, 2025)
        self.assertAlmostEqual(r["customer_concentration"]["top_share"], 1.0)
        self.assertTrue(any("concentration" in risk.lower() for risk in r["risks"]))


class GlobalSearchTest(unittest.TestCase):
    def test_rank_and_search(self):
        ranked = global_search.rank_items("invoice acme", [
            {"source": "document", "title": "Acme invoice", "text": "invoice from acme corp", "ref": "doc:1"},
            {"source": "task", "title": "call dentist", "text": "dentist appointment", "ref": "task:1"}])
        self.assertEqual(ranked[0]["ref"], "doc:1")

        conn = db.connect(":memory:")
        coa.seed_template(conn, "general_small_business")
        gl.create_entry(conn, "2025-03-01",
                        [{"account": "1000", "debit": 100}, {"account": "4000", "credit": 100}], memo="Acme deposit")
        store = DocStore(":memory:")
        store.save(pipeline.process_text("INVOICE\nInvoice Number: INV-1\nTotal: $100.00\nAcme Corp", "inv.txt"))
        res = global_search.search_all("acme", doc_store=store, acct_conn=conn)
        self.assertGreater(res["count"], 0)
        self.assertIn("document", res["by_source"])
        conn.close()
        store.close()


if __name__ == "__main__":
    unittest.main()
