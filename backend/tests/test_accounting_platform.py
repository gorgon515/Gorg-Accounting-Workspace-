import unittest

from accounting_platform import (
    db, coa, gl, ap, ar, fixed_assets, bank_rec, clients, documents, importers, dashboard,
)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        coa.seed_template(self.conn, "general_small_business")

    def tearDown(self):
        self.conn.close()


class APTest(Base):
    def test_bill_payment_aging_1099(self):
        v = ap.add_vendor(self.conn, "Acme Supplies", is_1099=True, tin="12-3456789")
        bill = ap.add_bill(self.conn, v["id"], 1000, "2025-03-01", "5400", due_date="2025-03-31")
        # Bill posts Dr expense / Cr AP.
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "2000")["id"])["balance"], 1000)
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "5400")["id"])["balance"], 1000)
        ap.pay_bill(self.conn, bill["id"], 800, "2025-03-15")
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "2000")["id"])["balance"], 200)
        aging = ap.aging(self.conn, "2025-04-15")
        self.assertAlmostEqual(aging["total"], 200)
        t = ap.vendor_1099_totals(self.conn, 2025)
        self.assertAlmostEqual(t["vendors"][0]["total_paid"], 800)
        self.assertTrue(t["vendors"][0]["reportable"])


class ARTest(Base):
    def test_invoice_payment_aging(self):
        c = ar.add_customer(self.conn, "Big Client")
        inv = ar.add_invoice(self.conn, c["id"], 5000, "2025-03-01", due_date="2025-03-31")
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "1200")["id"])["balance"], 5000)
        self.assertAlmostEqual(ar.aging(self.conn, "2025-04-15")["total"], 5000)
        ar.record_payment(self.conn, inv["id"], 5000, "2025-03-20")
        self.assertEqual(ar.get_invoice(self.conn, inv["id"])["status"], "paid")
        self.assertAlmostEqual(ar.aging(self.conn)["total"], 0)


class FixedAssetTest(Base):
    def test_straight_line(self):
        sched = fixed_assets.straight_line(12000, 0, 12)
        self.assertEqual(len(sched), 12)
        self.assertAlmostEqual(sum(sched), 12000)

    def test_double_declining(self):
        sched = fixed_assets.double_declining(10000, 1000, 5)
        self.assertAlmostEqual(sum(sched), 9000, places=2)  # depreciable base
        # Book value never drops below salvage.
        book = 10000
        for d in sched:
            book -= d
            self.assertGreaterEqual(round(book, 2), 1000 - 0.01)

    def test_uop_rate(self):
        self.assertAlmostEqual(fixed_assets.units_of_production_rate(11000, 1000, 10000), 1.0)

    def test_post_depreciation(self):
        a = fixed_assets.add_asset(self.conn, "Laptop", "2025-01-01", 1200, 12)
        sched = fixed_assets.depreciation_schedule(self.conn, a["id"])
        self.assertAlmostEqual(sched["total_depreciation"], 1200)
        fixed_assets.post_depreciation(self.conn, a["id"], 100, "2025-01-31")
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "5300")["id"])["balance"], 100)
        # Accumulated depreciation (contra-asset) reduces assets.
        self.assertAlmostEqual(gl.account_balance(self.conn, coa.by_number(self.conn, "1510")["id"])["balance"], -100)


class BankRecTest(Base):
    def test_parse_csv(self):
        rows = bank_rec.parse_csv("date,amount,description\n2025-03-05,500.00,Client deposit\n")
        self.assertEqual(rows[0]["amount"], 500.0)

    def test_parse_ofx(self):
        ofx = "<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20250305120000<TRNAMT>500.00<FITID>abc<NAME>Deposit</STMTTRN>"
        rows = bank_rec.parse_ofx(ofx)
        self.assertEqual(rows[0]["amount"], 500.0)
        self.assertEqual(rows[0]["date"], "2025-03-05")
        self.assertEqual(rows[0]["fitid"], "abc")

    def test_match_and_reconcile(self):
        cash = coa.by_number(self.conn, "1000")["id"]
        gl.create_entry(self.conn, "2025-03-05",
                        [{"account": "1000", "debit": 500}, {"account": "4000", "credit": 500}], memo="Deposit")
        bank_rec.import_transactions(self.conn, cash, [{"date": "2025-03-05", "amount": 500.0, "description": "Deposit", "fitid": "x1"}])
        self.assertEqual(bank_rec.auto_match(self.conn, cash)["matched"], 1)
        rep = bank_rec.reconciliation_report(self.conn, cash, "2025-03-31")
        self.assertAlmostEqual(rep["book_balance"], 500)
        self.assertAlmostEqual(rep["bank_balance"], 500)
        self.assertTrue(rep["reconciled"])


class ImportersClientsDocsTest(Base):
    def test_import_journal_csv(self):
        csv_text = "ref,date,account,debit,credit,memo\nE1,2025-03-02,1000,250,,Cash\nE1,2025-03-02,4000,,250,Rev\n"
        res = importers.import_journal_csv(self.conn, csv_text)
        self.assertEqual(res["entries_created"], 1)
        self.assertFalse(res["errors"])

    def test_clients_and_deadlines(self):
        c = clients.add_client(self.conn, "Tax Client LLC", kind="tax")
        from datetime import date, timedelta
        clients.add_engagement(self.conn, c["id"], "2024 1040", due_date=(date.today() + timedelta(days=5)).isoformat())
        self.assertEqual(len(clients.upcoming_deadlines(self.conn, days=30)), 1)

    def test_documents(self):
        d = documents.add_document(self.conn, "Q1 Bank Statement", doc_type="bank_statement", tags=["2025", "q1"])
        v2 = documents.new_version(self.conn, d["id"], path="/docs/q1_v2.pdf")
        self.assertEqual(v2["version"], 2)
        self.assertEqual(len(documents.search(self.conn, tag="q1")), 2)


class AuditDashboardTest(Base):
    def test_audit_records_actions(self):
        gl.create_entry(self.conn, "2025-03-01",
                        [{"account": "1000", "debit": 100}, {"account": "4000", "credit": 100}], memo="x")
        log = db.audit_log(self.conn)
        actions = {e["action"] for e in log}
        self.assertTrue({"create", "post"} <= actions)
        # Posting an entry recorded an old→new status transition.
        post_event = next(e for e in log if e["action"] == "post")
        self.assertEqual(post_event["new_value"]["status"], "posted")

    def test_dashboard_live(self):
        c = ar.add_customer(self.conn, "C")
        ar.add_invoice(self.conn, c["id"], 1000, "2025-03-01")
        ov = dashboard.overview(self.conn, "2025-03-31")
        for key in ("cash_position", "receivables", "payables", "profitability",
                    "balance_sheet_summary", "recent_entries", "alerts"):
            self.assertIn(key, ov)
        self.assertAlmostEqual(ov["receivables"]["total"], 1000)
        self.assertTrue(ov["balance_sheet_summary"]["balanced"])


if __name__ == "__main__":
    unittest.main()
