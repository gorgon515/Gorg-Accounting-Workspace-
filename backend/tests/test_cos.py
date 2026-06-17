import unittest
from datetime import date, datetime, timedelta, timezone

from cos import daily_briefing, evening_review, planner

TODAY = date.today()


def _evt(title, h0, h1, day=TODAY, loc=""):
    return {"title": title, "start": f"{day}T{h0:02d}:00:00", "end": f"{day}T{h1:02d}:00:00", "location": loc}


class DailyBriefingTest(unittest.TestCase):
    def test_generate(self):
        ctx = {
            "events": [_evt("Client call", 10, 11)],
            "emails": [
                {"from": "Boss", "subject": "URGENT thing by EOD", "snippet": "please respond today", "unread": True},
                {"from": "x", "subject": "fyi", "snippet": "", "unread": False},
            ],
            "tasks": [
                {"id": "t1", "title": "File sales tax", "priority": 5, "due": (TODAY - timedelta(days=2)).isoformat(), "status": "open"},
                {"id": "t2", "title": "Draft memo", "priority": 3, "due": (TODAY + timedelta(days=5)).isoformat(), "status": "open"},
            ],
            "goals": [
                {"title": "CPA FAR", "category": "cpa", "target": 100, "progress": 20, "unit": "%",
                 "deadline": (TODAY + timedelta(days=45)).isoformat(),
                 "created_at": (TODAY - timedelta(days=15)).isoformat()},
            ],
        }
        b = daily_briefing.generate(ctx, TODAY)
        for key in ("executive_summary", "todays_priorities", "schedule", "important_emails",
                    "upcoming_deadlines", "potential_conflicts", "energy_allocation",
                    "risks", "opportunities", "recommended_actions", "confidence"):
            self.assertIn(key, b)
        self.assertTrue(b["todays_priorities"])
        self.assertEqual(b["todays_priorities"][0]["title"], "File sales tax")  # overdue + high priority first
        self.assertTrue(any("overdue" in r.lower() for r in b["risks"]))
        self.assertEqual(b["confidence"]["level"], "High")  # calendar+email+tasks+goals


class EveningReviewTest(unittest.TestCase):
    def test_generate(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        ctx = {
            "tasks": [
                {"id": "t1", "title": "Done thing", "status": "done", "completed_at": now_iso},
                {"id": "t2", "title": "Missed thing", "status": "open", "due": (TODAY - timedelta(days=1)).isoformat()},
            ],
            "events": [_evt("Standup", 9, 10), _evt("Tomorrow mtg", 9, 10, day=TODAY + timedelta(days=1))],
            "emails": [{"from": "x", "subject": "y", "snippet": ""}],
        }
        r = evening_review.generate(ctx, TODAY)
        self.assertEqual(len(r["completed_work"]), 1)
        self.assertGreaterEqual(len(r["missed_tasks"]), 1)
        self.assertEqual(r["productivity_score"], 50.0)
        self.assertEqual(len(r["tomorrow_preparation"]["events"]), 1)


class PlannerTest(unittest.TestCase):
    def test_cpa_in_45_days(self):
        goals = [{"title": "CPA FAR", "category": "cpa", "target": 100, "progress": 20, "unit": "%",
                  "deadline": (TODAY + timedelta(days=45)).isoformat(),
                  "created_at": (TODAY - timedelta(days=15)).isoformat()}]
        tasks = [{"id": "t1", "title": "CPA study chapter 5", "category": "study", "status": "open", "priority": 3},
                 {"id": "t2", "title": "Email client", "category": "email", "status": "open", "priority": 2}]
        events = [_evt("Client call", 10, 11)]
        plan = planner.plan_day(goals, tasks, events, TODAY)
        self.assertTrue(plan["goal_recommendations"])
        self.assertEqual(plan["goal_recommendations"][0]["goal"], "CPA FAR")
        self.assertTrue(plan["calendar_blocks"])  # scheduled into a free focus block
        self.assertTrue(any("CPA study" in p["task"] for p in plan["priority_adjustments"]))


if __name__ == "__main__":
    unittest.main()
