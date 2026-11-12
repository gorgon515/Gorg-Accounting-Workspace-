import os
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import test_core as t
from career_agent import crm, db, formfill, mail, profile

FIX = Path(__file__).parent / "fixtures" / "form.html"
SENSITIVE = ('<fieldset><legend>Are you legally authorized to work in the United States?</legend>'
             '<label><input type="radio" name="auth" value="y" required>Yes</label>'
             '<label><input type="radio" name="auth" value="n">No</label></fieldset>')
PROF = dict(t.PROFILE, identity={"legal_name": "Test Q User", "email": "t@example.com", "phone": "555-0100",
                                 "linkedin": "https://linkedin.com/in/t", "city": "Town, NY"})
PROF["qualifications"] = dict(t.PROFILE["qualifications"], education=["B.S. Accounting, Long Island University, May 2026"],
                              gpa_overall=3.1, gpa_accounting=3.65)


def fields(*extra):
    base = [("First Name", "text", True), ("Last Name", "text", True), ("Email", "email", True),
            ("Resume/CV", "file", True), ("Accounting GPA", "text", False), ("Cumulative GPA", "text", False),
            ("How did you hear about us?", "text", False)]
    return [{"idx": i, "label": l, "type": ty, "required": r} for i, (l, ty, r) in enumerate(base + list(extra))]


class TestPlan(unittest.TestCase):
    def test_fills_only_profile_facts(self):
        p = formfill.plan(fields(), PROF, "/r.pdf")
        got = {f["idx"]: f["value"] for f in p["fills"]}
        self.assertEqual(got, {0: "Test", 1: "User", 2: "t@example.com", 3: "/r.pdf", 4: 3.65, 5: 3.1})
        self.assertEqual(p["skipped"], ["How did you hear about us?"])

    def test_sensitive_and_unknown_required_are_not_filled(self):
        p = formfill.plan(fields(("Are you authorized to work in the US?", "radio", True),
                                 ("Desired salary", "text", False), ("Years with CCH Axcess", "text", True)), PROF, "/r")
        un = [q["question"] for q in p["questions"] if q["answer"] is None]
        self.assertEqual(un, ["Are you authorized to work in the US?", "Desired salary", "Years with CCH Axcess"])
        self.assertNotIn(7, [f["idx"] for f in p["fills"]])

    def test_user_approved_answer_is_used(self):
        q = "Are you authorized to work in the US?"
        p = formfill.plan(fields((q, "radio", True)), PROF, "/r", approved_answers={q: "Yes"})
        self.assertIn({"idx": 7, "value": "Yes"}, p["fills"])


class TestMail(t.Base):
    def setUp(self):
        super().setUp()
        self.jid, self.app, self.doc = self.ready()

    def msg(self, i, subject, body="", frm="hr@acme.example"):
        return {"id": i, "from": frm, "subject": subject, "body": body, "date": "2026-11-12T10:00:00Z"}

    def test_classify(self):
        for s, k in [("Thank you for applying to Acme", "confirmation"), ("Interview availability", "interview"),
                     ("Update", "rejection"), ("Your offer letter", "offer"), ("Lunch?", "not_job_related")]:
            body = "Unfortunately we will not be moving forward" if s == "Update" else ""
            self.assertEqual(mail.classify(self.msg("x", s, body)), k, s)

    def test_confirmation_marks_submitted_then_rejection(self):
        r = mail.process(self.c, [self.msg("m1", "Thank you for applying to Acme", "Senior Accountant")])
        self.assertEqual(r[0]["action"], "marked submitted and received")
        a = crm.get_application(self.c, self.app)
        self.assertEqual((a["status"], a["resume_doc_id"]), ("Application received", self.doc))
        self.assertEqual(mail.process(self.c, [self.msg("m1", "Thank you for applying to Acme")]), [])
        mail.process(self.c, [self.msg("m2", "Acme application update", "Unfortunately we chose other candidates")])
        self.assertEqual(crm.get_application(self.c, self.app)["status"], "Rejected")

    def test_interview_without_submission_goes_to_user(self):
        r = mail.process(self.c, [self.msg("m3", "Acme interview availability")])
        self.assertIn("queued", r[0]["action"])
        self.assertEqual(crm.get_application(self.c, self.app)["status"], "Qualified")

    def test_unmatched_recruiter_mail_is_queued(self):
        r = mail.process(self.c, [self.msg("m4", "Exciting opportunity", "I came across your resume", "x@other.example")])
        self.assertIsNone(r[0]["application_id"])
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM approvals WHERE kind='unmatched_email'").fetchone()[0], 1)


@unittest.skipUnless(shutil.which("node"), "node not available")
class TestBrowser(t.Base):
    def setUp(self):
        super().setUp()
        profile.set_section(self.c, "identity", PROF["identity"])
        profile.set_section(self.c, "qualifications", PROF["qualifications"])
        self.jid, self.app, self.doc = self.ready()
        self.tmp = tempfile.mkdtemp()
        self.pdf = os.path.join(self.tmp, "r.pdf")
        open(self.pdf, "wb").write(b"%PDF-1.4 test")
        test = self

        class H(BaseHTTPRequestHandler):
            posted = []

            def log_message(self, *a):
                pass

            def do_GET(self):
                extra = {"/clean": "", "/sensitive": SENSITIVE, "/captcha": '<iframe src="https://www.google.com/recaptcha/x"></iframe>'}
                body = FIX.read_text().replace("__EXTRA__", extra.get(self.path, "")).encode()
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)

            def do_POST(self):
                H.posted.append(self.rfile.read(int(self.headers["Content-Length"])))
                body = b"<html><body><h1>Thank you for applying</h1><p>Application received. Ref ACME-777</p></body></html>"
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)
        self.H = H
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        super().tearDown()

    def go(self, path, **kw):
        return formfill.run(self.c, self.app, self.base + path, self.pdf, out_dir=self.tmp, resume_doc_id=self.doc, **kw)

    def test_auto_submit_records_portal_confirmation(self):
        db.set_setting(self.c, "automation", {"auto_submit": True})
        r = self.go("/clean", submit=True)
        self.assertEqual(r["outcome"], "submitted", r)
        a = crm.get_application(self.c, self.app)
        self.assertEqual(a["status"], "Application submitted")
        self.assertIn("ACME-777", a["confirmation"])
        self.assertIn(b"t@example.com", self.H.posted[0])
        self.assertIn(b"%PDF-1.4 test", self.H.posted[0])

    def test_no_submit_without_auto_permission(self):
        r = self.go("/clean", submit=True)
        self.assertEqual((r["outcome"], self.H.posted), ("needs_approval", []))
        self.assertIsNone(crm.get_application(self.c, self.app)["date_applied"])

    def test_sensitive_question_pauses(self):
        db.set_setting(self.c, "automation", {"auto_submit": True})
        r = self.go("/sensitive", submit=True)
        self.assertEqual((r["outcome"], self.H.posted), ("needs_approval", []))
        self.assertEqual(r["gate"]["approval_items"][0]["kind"], "work_eligibility")

    def test_captcha_is_manual(self):
        db.set_setting(self.c, "automation", {"auto_submit": True})
        self.assertEqual(self.go("/captcha", submit=True)["outcome"], "manual")


if __name__ == "__main__":
    unittest.main()
