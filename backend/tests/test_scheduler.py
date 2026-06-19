import os
import tempfile
import unittest
from datetime import datetime, timezone

from scheduler.engine import Scheduler, compute_next_run, cron_matches

UTC = timezone.utc


class NextRunTest(unittest.TestCase):
    def setUp(self):
        self.after = datetime(2025, 6, 17, 8, 0, tzinfo=UTC)  # a Tuesday

    def test_interval(self):
        self.assertEqual(compute_next_run("interval", "3600", self.after),
                         datetime(2025, 6, 17, 9, 0, tzinfo=UTC))

    def test_daily(self):
        self.assertEqual(compute_next_run("daily", "09:00", self.after),
                         datetime(2025, 6, 17, 9, 0, tzinfo=UTC))
        # After today's time → rolls to tomorrow.
        later = datetime(2025, 6, 17, 10, 0, tzinfo=UTC)
        self.assertEqual(compute_next_run("daily", "09:00", later),
                         datetime(2025, 6, 18, 9, 0, tzinfo=UTC))

    def test_weekly(self):
        # Next Monday 09:00 after Tue 2025-06-17 → 2025-06-23.
        self.assertEqual(compute_next_run("weekly", "mon 09:00", self.after),
                         datetime(2025, 6, 23, 9, 0, tzinfo=UTC))

    def test_cron(self):
        self.assertEqual(compute_next_run("cron", "*/15 * * * *", datetime(2025, 6, 17, 8, 2, tzinfo=UTC)),
                         datetime(2025, 6, 17, 8, 15, tzinfo=UTC))
        # 0 9 * * 1 = Mondays at 09:00 → next Monday.
        self.assertEqual(compute_next_run("cron", "0 9 * * 1", self.after),
                         datetime(2025, 6, 23, 9, 0, tzinfo=UTC))

    def test_cron_matches(self):
        self.assertTrue(cron_matches(datetime(2025, 6, 23, 9, 0), "0 9 * * 1"))  # Monday
        self.assertFalse(cron_matches(datetime(2025, 6, 24, 9, 0), "0 9 * * 1"))  # Tuesday


class SchedulerRunTest(unittest.TestCase):
    def setUp(self):
        self.s = Scheduler(":memory:", tz="UTC")
        self.calls = []

    def tearDown(self):
        self.s.close()

    def test_due_run_advance_audit(self):
        t0 = datetime(2025, 6, 17, 8, 0, tzinfo=UTC)
        job = self.s.add_job("ping", "noop", "interval", "60", now=t0)
        self.assertEqual(self.s.due_jobs(t0), [])  # next_run is t0+60
        t1 = datetime(2025, 6, 17, 8, 1, tzinfo=UTC)
        handlers = {"noop": lambda payload: self.calls.append(payload) or "done"}
        results = self.s.run_due(t1, handlers)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["ok"])
        self.assertEqual(len(self.calls), 1)
        # next_run advanced past t1.
        self.assertGreater(self.s.get(job["id"])["next_run"], t1.isoformat())
        self.assertEqual(len(self.s.history()), 1)

    def test_missing_handler_is_logged_not_fatal(self):
        t0 = datetime(2025, 6, 17, 8, 0, tzinfo=UTC)
        self.s.add_job("x", "ghost", "interval", "1", now=t0)
        res = self.s.run_due(datetime(2025, 6, 17, 8, 1, tzinfo=UTC), {})
        self.assertFalse(res[0]["ok"])
        self.assertIn("no handler", res[0]["detail"])

    def test_once_disables_after_run(self):
        t0 = datetime(2025, 6, 17, 8, 0, tzinfo=UTC)
        job = self.s.add_job("one", "noop", "once", "2025-06-17T08:00:00+00:00", now=t0)
        self.s.run_due(datetime(2025, 6, 17, 8, 1, tzinfo=UTC), {"noop": lambda p: "ok"})
        self.assertFalse(self.s.get(job["id"])["enabled"])


class RecoveryTest(unittest.TestCase):
    def test_jobs_persist_across_restart(self):
        path = os.path.join(tempfile.mkdtemp(), "sched.db")
        s1 = Scheduler(path, tz="UTC")
        s1.add_job("morning brief", "briefing", "daily", "07:00",
                   now=datetime(2025, 6, 17, 8, 0, tzinfo=UTC))
        s1.close()
        s2 = Scheduler(path, tz="UTC")
        jobs = s2.list()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["name"], "morning brief")
        self.assertTrue(jobs[0]["next_run"])  # recovered schedule
        s2.close()


if __name__ == "__main__":
    unittest.main()
