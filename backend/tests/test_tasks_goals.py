import unittest
from datetime import date, timedelta

from tasks.engine import TaskStore, priority_score, deadline_urgency, categorize
from goals.engine import GoalStore, forecast


class TaskEngineTest(unittest.TestCase):
    def setUp(self):
        self.s = TaskStore(":memory:")

    def tearDown(self):
        self.s.close()

    def test_crud_and_categorize(self):
        t = self.s.create("Reconcile bank ledger", priority=4)
        self.assertEqual(t["category"], "accounting")
        self.assertEqual(t["status"], "open")
        self.s.update(t["id"], priority=5)
        self.assertEqual(self.s.get(t["id"])["priority"], 5)
        self.s.delete(t["id"])
        self.assertIsNone(self.s.get(t["id"]))

    def test_scoring(self):
        today = date(2025, 6, 17)
        self.assertEqual(deadline_urgency(None), 0.2)
        self.assertEqual(deadline_urgency("2025-06-10", today), 1.0)  # overdue
        hi = priority_score({"priority": 5, "due": "2025-06-17"}, today)
        lo = priority_score({"priority": 1, "due": None}, today)
        self.assertGreater(hi, lo)

    def test_recurrence_spawns_next(self):
        t = self.s.create("Weekly review", recurrence="weekly", due="2025-06-17")
        r = self.s.complete(t["id"])
        self.assertIsNotNone(r["next"])
        self.assertEqual(r["next"]["due"][:10], "2025-06-24")

    def test_dependencies_block_recommend(self):
        a = self.s.create("Design", priority=5)
        b = self.s.create("Build", priority=5, depends_on=[a["id"]])
        recs = self.s.recommend()
        titles = [t["title"] for t in recs]
        self.assertIn("Design", titles)
        self.assertNotIn("Build", titles)  # blocked by incomplete dependency
        self.s.complete(a["id"])
        self.assertIn("Build", [t["title"] for t in self.s.recommend()])

    def test_stats(self):
        self.s.create("Overdue", due="2000-01-01")
        st = self.s.stats()
        self.assertGreaterEqual(st["overdue"], 1)


class GoalEngineTest(unittest.TestCase):
    def setUp(self):
        self.s = GoalStore(":memory:")

    def tearDown(self):
        self.s.close()

    def test_crud_progress_milestones(self):
        g = self.s.create("Read 12 books", category="reading", target=12, unit="books")
        self.s.update_progress(g["id"], 3)
        self.s.add_milestone(g["id"], "Finish book 4")
        g = self.s.get(g["id"])
        self.assertEqual(g["progress"], 3)
        self.assertEqual(len(g["milestones"]), 1)

    def test_forecast_behind(self):
        today = date(2025, 6, 17)
        goal = {"target": 100, "progress": 20, "unit": "%",
                "deadline": (today + timedelta(days=45)).isoformat(),
                "created_at": (today - timedelta(days=15)).isoformat()}
        f = forecast(goal, today)
        self.assertEqual(f["status"], "behind")
        self.assertEqual(f["days_remaining"], 45)
        self.assertAlmostEqual(f["required_pace_per_day"], (100 - 20) / 45, places=2)

    def test_forecast_complete_and_no_deadline(self):
        self.assertEqual(forecast({"target": 10, "progress": 10})["status"], "complete")
        self.assertEqual(forecast({"target": 10, "progress": 2})["status"], "no_deadline")

    def test_dashboard(self):
        today = date(2025, 6, 17)
        self.s.create("CPA FAR", category="cpa", target=100,
                      deadline=(today + timedelta(days=10)).isoformat())
        d = self.s.dashboard(today)
        self.assertEqual(d["count"], 1)
        self.assertIn("forecast", d["goals"][0])


if __name__ == "__main__":
    unittest.main()
