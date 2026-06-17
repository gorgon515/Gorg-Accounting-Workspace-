import unittest
from datetime import date

from email_intel import engine as mail
from calendar_intel import engine as cal

EMAILS = [
    {"from": "Boss <boss@co.com>", "subject": "URGENT: report needed by EOD",
     "snippet": "Please send the Q2 report by end of day. Can you confirm?",
     "body": "Please send the Q2 report by end of day.", "unread": True},
    {"from": "newsletter@news.com", "subject": "Weekly digest", "snippet": "news", "body": "", "unread": True},
    {"from": "Client <c@client.com>", "subject": "Invoice #44 amount due",
     "snippet": "balance due $500", "body": "", "unread": True},
    {"from": "Sam <sam@x.com>", "subject": "Meeting next week",
     "snippet": "Can we schedule a call? let's meet", "body": "", "unread": False},
]


class EmailIntelTest(unittest.TestCase):
    def test_categorize(self):
        self.assertEqual(mail.categorize(EMAILS[0]), "urgent")
        self.assertEqual(mail.categorize(EMAILS[1]), "archived")
        self.assertEqual(mail.categorize(EMAILS[2]), "accounting")
        self.assertEqual(mail.categorize(EMAILS[3]), "follow_up")

    def test_detectors(self):
        self.assertTrue(mail.is_meeting_request(EMAILS[3]))
        self.assertTrue(mail.is_invoice(EMAILS[2]))
        self.assertIn("end of day", [d.lower() for d in mail.extract_deadlines(EMAILS[0])])
        self.assertTrue(mail.extract_tasks(EMAILS[0]))

    def test_priority_and_draft(self):
        self.assertGreater(mail.priority_score(EMAILS[0]), mail.priority_score(EMAILS[1]))
        self.assertIn("options", mail.draft_reply(EMAILS[3]))  # meeting reply offers times

    def test_inbox_briefing(self):
        b = mail.inbox_briefing(EMAILS)
        self.assertEqual(b["total"], 4)
        self.assertEqual(b["top"][0]["from"], "Boss <boss@co.com>")  # highest score
        self.assertTrue(b["suggested_actions"])
        self.assertIn("urgent", b["by_category"])


class CalendarIntelTest(unittest.TestCase):
    DAY = date(2025, 6, 17)
    EVENTS = [
        {"title": "Standup", "start": "2025-06-17T09:00:00", "end": "2025-06-17T09:30:00", "location": "Office"},
        {"title": "Client call", "start": "2025-06-17T10:00:00", "end": "2025-06-17T11:00:00", "location": "Zoom"},
        {"title": "Overlap", "start": "2025-06-17T10:30:00", "end": "2025-06-17T11:30:00"},
    ]

    def test_conflicts(self):
        c = cal.detect_conflicts(self.EVENTS)
        self.assertEqual(len(c), 1)
        self.assertEqual({c[0]["a"], c[0]["b"]}, {"Client call", "Overlap"})

    def test_free_and_focus(self):
        slots = cal.free_slots(self.EVENTS, self.DAY)
        # 09:30–10:00 (30m) and 11:30–18:00 (390m)
        self.assertTrue(any(s["minutes"] == 30 for s in slots))
        focus = cal.focus_blocks(slots)
        self.assertEqual(len(focus), 1)
        self.assertEqual(focus[0]["minutes"], 390)

    def test_time_blocks(self):
        tasks = [{"id": "t1", "title": "Deep work", "score": 90}, {"id": "t2", "title": "Email", "score": 40}]
        blocks = cal.suggest_time_blocks(tasks, cal.free_slots(self.EVENTS, self.DAY))
        self.assertEqual(blocks[0]["task"], "Deep work")

    def test_travel_buffer(self):
        tight = [
            {"title": "A", "start": "2025-06-17T09:00:00", "end": "2025-06-17T09:50:00", "location": "Office"},
            {"title": "B", "start": "2025-06-17T10:00:00", "end": "2025-06-17T11:00:00", "location": "Downtown"},
        ]
        w = cal.travel_buffers(tight, buffer_min=30)
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["gap_minutes"], 10)

    def test_meeting_prep_and_plan(self):
        prep = cal.meeting_prep(self.EVENTS[1])
        self.assertTrue(prep["checklist"])
        plan = cal.daily_plan(self.EVENTS, [], self.DAY)
        self.assertEqual(plan["date"], "2025-06-17")
        self.assertTrue(plan["conflicts"])


if __name__ == "__main__":
    unittest.main()
