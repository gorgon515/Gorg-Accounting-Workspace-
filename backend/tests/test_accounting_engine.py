import unittest

from accounting.briefing.generator import generate_briefing
from accounting import knowledge_graph as kg
from accounting import research

# Representative stored-item dicts (as IntelStore.query would return).
ITEMS = [
    {"id": "a1", "source": "FASB", "doc_type": "Accounting Standards Update",
     "title": "ASU 2025-03 Revenue (ASC 606) for software", "url": "u1",
     "published": "2025-02-10", "effective_date": "2025-12-15",
     "asc_codes": ["606"], "asu_number": "2025-03", "first_seen": "2025-06-17T00:00:00"},
    {"id": "a2", "source": "FASB", "doc_type": "Exposure Draft",
     "title": "Exposure Draft on Leases (ASC 842) real estate", "url": "u2",
     "published": "2025-05-01", "effective_date": None,
     "asc_codes": ["842"], "asu_number": None, "first_seen": "2025-06-17T00:00:00"},
    {"id": "a3", "source": "SEC", "doc_type": "SEC Release",
     "title": "SEC enforcement action over restatement and material weakness", "url": "u3",
     "published": "2025-06-01", "effective_date": None, "asc_codes": [],
     "asu_number": None, "first_seen": "2025-06-17T00:00:00"},
]


class BriefingTest(unittest.TestCase):
    def setUp(self):
        self.b = generate_briefing(ITEMS, new_ids=["a1", "a2"], today="2025-06-17")

    def test_structure(self):
        for key in ("executive_summary", "new_developments", "key_changes",
                    "upcoming_effective_dates", "affected_industries", "cpa_impact",
                    "emerging_risks", "action_items", "confidence"):
            self.assertIn(key, self.b)

    def test_content(self):
        self.assertEqual(len(self.b["new_developments"]), 2)
        # ASU sorts ahead of exposure draft / SEC release in key changes.
        self.assertEqual(self.b["key_changes"][0]["doc_type"], "Accounting Standards Update")
        self.assertIn("Software & technology", self.b["affected_industries"])
        self.assertIn("Real estate", self.b["affected_industries"])
        # The future effective date surfaces.
        self.assertEqual(self.b["upcoming_effective_dates"][0]["effective_date"], "2025-12-15")
        # CPA impact maps ASC 606 → FAR.
        self.assertTrue(any("606" in c["asc"] for c in self.b["cpa_impact"]))
        # Emerging-risk detection from "restatement"/"material weakness".
        self.assertTrue(self.b["emerging_risks"])
        self.assertTrue(self.b["action_items"])

    def test_confidence(self):
        self.assertEqual(self.b["confidence"]["level"], "Medium")  # 2 sources, 0 errors
        empty = generate_briefing([], today="2025-06-17")
        self.assertEqual(empty["confidence"]["level"], "None")


class KnowledgeGraphTest(unittest.TestCase):
    def test_build(self):
        g = kg.build_graph()
        kinds = {n["kind"] for n in g["nodes"]}
        self.assertTrue({"asc", "fs_area", "industries", "disclosures", "audit", "tax", "exam"} <= kinds)
        self.assertTrue(any(e["rel"] == "requires" for e in g["edges"]))

    def test_attach_asu(self):
        g = kg.build_graph(ITEMS)
        self.assertTrue(any(n["kind"] == "asu" for n in g["nodes"]))
        self.assertTrue(any(e["rel"] == "amends" for e in g["edges"]))

    def test_subgraph(self):
        sg = kg.subgraph_for_asc("606")
        self.assertTrue(sg["nodes"])
        self.assertTrue(all(isinstance(e["rel"], str) for e in sg["edges"]))


class ResearchTest(unittest.TestCase):
    def test_checklist(self):
        cl = research.implementation_checklist("606")
        self.assertEqual(cl["asc"], "ASC 606")
        self.assertTrue(len(cl["checklist"]) >= 8)
        self.assertTrue(cl["policy_choices"])

    def test_technical_memo(self):
        memo = research.technical_memo(
            facts="Customer prepays an annual SaaS subscription delivered over 12 months.",
            issue="When is revenue recognized?", topic="606")
        for key in ("facts", "issue", "relevant_guidance", "analysis", "alternatives",
                    "conclusion", "references"):
            self.assertIn(key, memo)
        self.assertIn("ASC 606", memo["references"])
        self.assertTrue(memo["alternatives"])

    def test_memo_requires_inputs_and_known_topic(self):
        with self.assertRaises(ValueError):
            research.technical_memo(facts="", issue="x", topic="606")
        with self.assertRaises(ValueError):
            research.technical_memo(facts="f", issue="i", topic="unknown")

    def test_summarize_asu(self):
        s = research.summarize_asu("2025-03", "Revenue update", ["606"])
        self.assertEqual(s["amends"][0]["asc"], "ASC 606")


if __name__ == "__main__":
    unittest.main()
