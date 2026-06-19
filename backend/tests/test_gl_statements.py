import unittest

from accounting_platform import db, coa, gl, statements


class GLStatementsTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        coa.seed_template(self.conn, "general_small_business")
        # A simple, real set of opening transactions (all in one open period).
        gl.create_entry(self.conn, "2025-03-01",
                        [{"account": "1000", "debit": 10000}, {"account": "3000", "credit": 10000}],
                        memo="Owner investment")
        gl.create_entry(self.conn, "2025-03-05",
                        [{"account": "1000", "debit": 5000}, {"account": "4000", "credit": 5000}],
                        memo="Service revenue")
        gl.create_entry(self.conn, "2025-03-10",
                        [{"account": "5100", "debit": 2000}, {"account": "1000", "credit": 2000}],
                        memo="Rent")
        gl.create_entry(self.conn, "2025-03-12",
                        [{"account": "1500", "debit": 3000}, {"account": "1000", "credit": 3000}],
                        memo="Buy equipment")
        gl.create_entry(self.conn, "2025-03-15",
                        [{"account": "1000", "debit": 4000}, {"account": "2500", "credit": 4000}],
                        memo="Bank loan")

    def tearDown(self):
        self.conn.close()

    def test_unbalanced_rejected(self):
        with self.assertRaises(ValueError):
            gl.create_entry(self.conn, "2025-03-20",
                            [{"account": "1000", "debit": 100}, {"account": "4000", "credit": 90}])

    def test_trial_balance_balances(self):
        tb = gl.trial_balance(self.conn, "2025-03-31")
        self.assertTrue(tb["balanced"])
        self.assertAlmostEqual(tb["total_debit"], tb["total_credit"])

    def test_account_balance_signs(self):
        cash = coa.by_number(self.conn, "1000")
        self.assertAlmostEqual(gl.account_balance(self.conn, cash["id"], "2025-03-31")["balance"], 14000)

    def test_income_statement(self):
        inc = statements.income_statement(self.conn, "2025-03-01", "2025-03-31")
        self.assertAlmostEqual(inc["total_revenue"], 5000)
        self.assertAlmostEqual(inc["total_expenses"], 2000)
        self.assertAlmostEqual(inc["net_income"], 3000)

    def test_balance_sheet_identity(self):
        bs = statements.balance_sheet(self.conn, "2025-03-31")
        self.assertTrue(bs["balanced"])
        self.assertAlmostEqual(bs["total_assets"], 17000)          # 14000 cash + 3000 equipment
        self.assertAlmostEqual(bs["total_liabilities"], 4000)      # bank loan
        self.assertAlmostEqual(bs["total_equity"], 13000)          # 10000 owner + 3000 net income
        self.assertAlmostEqual(bs["total_assets"], bs["total_liabilities"] + bs["total_equity"])

    def test_cash_flow_reconciles(self):
        cf = statements.cash_flow(self.conn, "2025-03-01", "2025-03-31")
        self.assertTrue(cf["reconciles"])
        self.assertAlmostEqual(cf["operating_activities"], 3000)
        self.assertAlmostEqual(cf["investing_activities"], -3000)
        self.assertAlmostEqual(cf["financing_activities"], 14000)
        self.assertAlmostEqual(cf["net_change_in_cash"], 14000)
        self.assertAlmostEqual(cf["ending_cash"], 14000)

    def test_period_close_blocks_posting(self):
        db.close_period(self.conn, 2025, 3)
        with self.assertRaises(ValueError):
            gl.create_entry(self.conn, "2025-03-25",
                            [{"account": "1000", "debit": 10}, {"account": "4000", "credit": 10}])

    def test_reversal(self):
        e = gl.create_entry(self.conn, "2025-03-18",
                            [{"account": "5200", "debit": 50}, {"account": "1000", "credit": 50}], memo="Oops")
        rev = gl.reverse_entry(self.conn, e["id"], "2025-03-19")
        self.assertEqual(rev["entry_type"], "reversing")
        # Office expense nets to zero after reversal.
        office = coa.by_number(self.conn, "5200")
        self.assertAlmostEqual(gl.account_balance(self.conn, office["id"])["balance"], 0)


if __name__ == "__main__":
    unittest.main()
