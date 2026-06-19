"""API tests for the Phase-5 personal chief-of-staff endpoints (isolated DBs)."""
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp()
os.environ["HELIOS_TASKS_DB"] = os.path.join(_TMP, "t.db")
os.environ["HELIOS_GOALS_DB"] = os.path.join(_TMP, "g.db")
os.environ["HELIOS_SCHED_DB"] = os.path.join(_TMP, "s.db")
os.environ["HELIOS_INTEL_DB"] = os.path.join(_TMP, "i.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


class TasksGoalsRoutes(unittest.TestCase):
    def test_task_lifecycle(self):
        r = client.post("/tasks", json={"title": "Reconcile ledger", "priority": 4, "due": "2030-01-01"})
        self.assertEqual(r.status_code, 200)
        tid = r.json()["id"]
        self.assertEqual(r.json()["category"], "accounting")
        self.assertIn("tasks", client.get("/tasks").json())
        self.assertTrue(client.get("/tasks/recommend").json()["recommended"])
        self.assertEqual(client.post(f"/tasks/{tid}/complete").json()["completed"], tid)

    def test_goal_lifecycle(self):
        r = client.post("/goals", json={"title": "CPA FAR", "category": "cpa", "deadline": "2030-01-01"})
        self.assertEqual(r.status_code, 200)
        gid = r.json()["id"]
        client.post("/goals/progress", json={"id": gid, "progress": 25})
        dash = client.get("/goals").json()
        self.assertGreaterEqual(dash["count"], 1)
        self.assertIn("forecast", dash["goals"][0])


class SchedulerRoutes(unittest.TestCase):
    def test_seed_and_tick(self):
        seed = client.post("/scheduler/seed").json()
        self.assertGreaterEqual(seed["total"], 4)
        jobs = client.get("/scheduler/jobs").json()
        self.assertIn("accounting_refresh", jobs["handlers"])
        # Tick runs any due jobs (none may be due now); endpoint must succeed.
        self.assertIn("ran", client.post("/scheduler/tick").json())


class IntelRoutes(unittest.TestCase):
    EMAILS = [{"from": "Boss", "subject": "URGENT by EOD", "snippet": "please respond today", "unread": True},
              {"from": "newsletter@x.com", "subject": "digest", "snippet": "", "unread": True}]

    def test_email_briefing(self):
        b = client.post("/email/briefing", json={"emails": self.EMAILS}).json()
        self.assertEqual(b["total"], 2)
        self.assertIn("urgent", b["by_category"])

    def test_calendar_plan(self):
        r = client.post("/calendar/plan", json={"events": [
            {"title": "Call", "start": "2025-06-17T10:00:00", "end": "2025-06-17T11:00:00"}], "tasks": []})
        self.assertEqual(r.status_code, 200)
        self.assertIn("free_slots", r.json())


class CosRoutes(unittest.TestCase):
    def test_briefing_and_plan_auto(self):
        client.post("/goals", json={"title": "Ship feature", "deadline": "2030-01-01"})
        client.post("/tasks", json={"title": "Write tests", "priority": 5})
        b = client.get("/cos/briefing/auto").json()
        self.assertIn("executive_summary", b)
        self.assertIn("recommended_actions", b)
        p = client.get("/cos/plan/auto").json()
        self.assertIn("summary", p)

    def test_daily_briefing_with_context(self):
        r = client.post("/cos/daily-briefing", json={
            "events": [{"title": "Standup", "start": "2025-06-17T09:00:00", "end": "2025-06-17T09:30:00"}],
            "emails": [{"from": "x", "subject": "y", "snippet": ""}]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("confidence", r.json())


if __name__ == "__main__":
    unittest.main()
