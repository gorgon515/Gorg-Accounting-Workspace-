import unittest

from app.services import accounting_research as research


class AccountingResearchTest(unittest.TestCase):
    def test_explain_by_number_and_alias(self):
        self.assertEqual(research.explain_asc("606")["asc"], "ASC 606")
        self.assertEqual(research.explain_asc("revenue")["asc"], "ASC 606")
        self.assertEqual(research.explain_asc("ASC 842")["asc"], "ASC 842")
        self.assertEqual(len(research.explain_asc("606")["framework"]), 5)

    def test_unknown_topic_raises(self):
        with self.assertRaises(ValueError):
            research.explain_asc("999")

    def test_memo_structure(self):
        memo = research.generate_memo(
            issue="When should the upfront SaaS fee be recognized?",
            facts="Customer prepays a 12-month subscription; service delivered over the year.",
            topic="606",
        )
        for key in ("issue", "facts", "guidance", "analysis", "conclusion",
                    "disclosure_impact", "cpa_exam_impact", "citations"):
            self.assertIn(key, memo)
        self.assertEqual(memo["citations"], ["ASC 606"])
        self.assertIn("ASC 606", memo["guidance"]["citation"])

    def test_memo_requires_inputs(self):
        with self.assertRaises(ValueError):
            research.generate_memo(issue="", facts="x", topic="606")
        with self.assertRaises(ValueError):
            research.generate_memo(issue="x", facts="y", topic="unknown-topic")

    def test_topics_listing(self):
        topics = research.list_topics()
        self.assertTrue(any(t["asc"] == "ASC 606" for t in topics))


if __name__ == "__main__":
    unittest.main()
