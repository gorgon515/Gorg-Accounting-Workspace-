import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

_tmp = tempfile.mkdtemp()
os.environ["CAREER_KEY_FILE"] = os.path.join(_tmp, "key")
os.environ["CAREER_DATA_DIR"] = _tmp

from career_agent import analytics, crm, db, discovery, documents, followup, profile, rules, scoring  # noqa: E402

PROFILE = {
    "identity": {"name": "Test User"},
    "career_interests": {"target_titles": ["Senior Accountant"], "industries": ["technology"],
                         "avoid_industries": ["tobacco"]},
    "employment_preferences": {"locations": ["New York"], "arrangements": ["hybrid", "remote"]},
    "compensation": {"min_base": 90000, "ideal_base": 110000},
    "qualifications": {"skills": ["GAAP", "Excel", "NetSuite"], "certifications": ["CPA"], "years_experience": 4},
    "personal_preferences": {"culture": "x"},
    "application_preferences": {"mode": "quality"},
}
JOB = {"source": "test", "employer": "Acme", "title": "Senior Accountant", "location": "New York, NY",
       "arrangement": "hybrid", "url": "https://acme.example/jobs/1", "description": "Close the books.",
       "industry": "Technology", "comp_min": 100000, "comp_max": 120000, "mandatory": ["CPA", "GAAP"],
       "preferred": ["NetSuite", "SOX"]}
RATED = {"advancement": 85, "benefits": 80, "reputation": 80}


class Base(unittest.TestCase):
    def setUp(self):
        self.c = db.connect(":memory:")
        for s, v in PROFILE.items():
            profile.set_section(self.c, s, v)

    def tearDown(self):
        self.c.close()

    def ready(self):
        jid, _ = crm.upsert_job(self.c, dict(JOB))
        crm.evaluate(self.c, jid, RATED)
        app = crm.application_for_job(self.c, jid)
        aid = documents.add_achievement(self.c, "Cut monthly close from 10 to 6 days", verified=True)
        documents.add_skill(self.c, "GAAP", verified=True)
        doc, fc = documents.save_tailored(self.c, "tailored_resume", "acme", {
            "bullets": [{"text": "Reduced monthly close from 10 to 6 days", "achievement_ids": [aid]}],
            "skills": ["GAAP"]}, app["id"])
        self.assertTrue(fc["ok"])
        for w in ("profile", "master_documents", "submission_rules"):
            profile.approve(self.c, w)
        return jid, app["id"], doc


class TestScoring(Base):
    def test_strong_match_and_preferred_gap_not_fatal(self):
        r = scoring.score_job(JOB, PROFILE, profile.DEFAULT_SETTINGS["weights"], RATED)
        self.assertGreaterEqual(r["score"], 85)
        self.assertEqual(r["flags"]["preferred_missing"], ["SOX"])
        self.assertFalse(r["provisional"])

    def test_unrated_is_provisional_not_padded(self):
        r = scoring.score_job(JOB, PROFILE, profile.DEFAULT_SETTINGS["weights"])
        self.assertTrue(r["provisional"])
        self.assertEqual(sorted(r["unrated"]), ["advancement", "benefits", "reputation"])

    def test_below_minimum_pay_and_avoided_industry(self):
        low = dict(JOB, comp_min=50000, comp_max=60000, industry="Tobacco")
        r = scoring.score_job(low, PROFILE, profile.DEFAULT_SETTINGS["weights"], RATED)
        self.assertEqual(r["categories"]["compensation"], 0)
        self.assertEqual(r["categories"]["career_alignment"], 0)

    def test_mandatory_miss_hurts_more_than_preferred(self):
        a = scoring.qualifications(dict(JOB, mandatory=["CPA", "CFA"], preferred=[]), PROFILE)[0]
        b = scoring.qualifications(dict(JOB, mandatory=["CPA"], preferred=["CFA"]), PROFILE)[0]
        self.assertLess(a, b)

    def test_classes(self):
        self.assertEqual(scoring.classify(92), "Exceptional match")
        self.assertEqual(scoring.classify(59.9), "Below threshold")


class TestCRM(Base):
    def test_dedupe_and_change_detection(self):
        a, r1 = crm.upsert_job(self.c, dict(JOB))
        b, r2 = crm.upsert_job(self.c, dict(JOB, url="https://indeed.example/x", source="indeed"))
        c, r3 = crm.upsert_job(self.c, dict(JOB, description="New duties."))
        self.assertEqual((a, r1, r2, r3), (b, "new", "unchanged", "updated"))
        self.assertEqual(a, c)

    def test_distinct_requisitions_same_board(self):
        a, _ = crm.upsert_job(self.c, dict(JOB, source_id="1"))
        b, r = crm.upsert_job(self.c, dict(JOB, source_id="2", description="Other team."))
        self.assertNotEqual(a, b)
        self.assertEqual(crm.upsert_job(self.c, dict(JOB, source_id="2", description="Other team.")), (b, "unchanged"))

    def test_rejects_unverifiable(self):
        self.assertEqual(crm.upsert_job(self.c, dict(JOB, url="http://x"))[1], "rejected:unverifiable url")
        self.assertEqual(crm.upsert_job(self.c, dict(JOB, employer=""))[1], "rejected:missing employer")

    def test_submission_requires_confirmation(self):
        jid, app, doc = self.ready()
        with self.assertRaises(ValueError):
            crm.set_status(self.c, app, "Application submitted")
        with self.assertRaises(ValueError):
            crm.mark_submitted(self.c, app, "", "", doc)
        with self.assertRaises(ValueError):
            crm.set_status(self.c, app, "Initial interview")
        crm.mark_submitted(self.c, app, "REQ-123 received", "https://acme.example/thanks", doc)
        self.assertEqual(crm.get_application(self.c, app)["status"], "Application submitted")
        crm.set_status(self.c, app, "Initial interview")

    def test_closed_posting(self):
        jid, _ = crm.upsert_job(self.c, dict(JOB))
        self.assertEqual(crm.close_missing(self.c, "test", "Acme", set()), [jid])
        self.assertIsNotNone(crm.get_job(self.c, jid)["closed_at"])


class TestGate(Base):
    def test_blocked_until_approved(self):
        jid, _ = crm.upsert_job(self.c, dict(JOB))
        crm.evaluate(self.c, jid, RATED)
        g = rules.gate(self.c, crm.application_for_job(self.c, jid)["id"])
        self.assertEqual(g["mode"], "blocked")
        self.assertIn("profile not approved by user", g["reasons"])

    def test_auto_only_when_enabled_and_clean(self):
        _, app, _ = self.ready()
        self.assertEqual(rules.gate(self.c, app)["mode"], "approval")
        db.set_setting(self.c, "automation", {"auto_submit": True})
        ok = [{"question": "LinkedIn profile URL", "answer": "x", "source": "profile"}]
        self.assertEqual(rules.gate(self.c, app, ok)["mode"], "auto")

    def test_sensitive_and_unverified_questions_pause(self):
        _, app, _ = self.ready()
        db.set_setting(self.c, "automation", {"auto_submit": True})
        for q, kind in [("Are you legally authorized to work in the US?", "work_eligibility"),
                        ("I consent to a background check", "background_check"),
                        ("What are your salary expectations?", "compensation_commitment"),
                        ("I certify the above is true", "legal_declaration"),
                        ("Gender", "sensitive_personal")]:
            g = rules.gate(self.c, app, [{"question": q, "answer": "yes", "source": "profile"}])
            self.assertEqual((g["mode"], g["approval_items"][0]["kind"]), ("approval", kind), q)
        g = rules.gate(self.c, app, [{"question": "Favourite ERP?", "answer": None}])
        self.assertEqual(g["approval_items"][0]["kind"], "unverified_answer")

    def test_experience_rule_excludes(self):
        profile.set_section(self.c, "application_preferences", {"experience_required_roles": "exclude roles"})
        q = dict(PROFILE["qualifications"], years_experience=0)
        profile.set_section(self.c, "qualifications", q)
        jid, _ = crm.upsert_job(self.c, dict(JOB, years_required=3))
        r = crm.evaluate(self.c, jid, RATED)
        self.assertEqual(r["classification"], "Excluded")
        self.assertEqual(crm.application_for_job(self.c, jid)["status"], "Evaluated")

    def test_captcha_is_manual(self):
        _, app, _ = self.ready()
        db.set_setting(self.c, "automation", {"auto_submit": True})
        self.assertEqual(rules.gate(self.c, app, page_text="Please complete the reCAPTCHA")["mode"], "manual")

    def test_duplicate_and_profile_edit_revoke(self):
        _, app, doc = self.ready()
        crm.mark_submitted(self.c, app, "ok", "url", doc)
        self.assertIn("already submitted (duplicate)", rules.gate(self.c, app)["reasons"])
        profile.set_section(self.c, "compensation", {"min_base": 95000})
        self.assertFalse(profile.settings(self.c)["approvals"]["profile"])


class TestDocuments(Base):
    def test_fact_check_blocks_fabrication(self):
        aid = documents.add_achievement(self.c, "Managed AP for 3 entities", verified=True)
        un = documents.add_achievement(self.c, "Led team of 5", verified=False)
        fc = documents.fact_check(self.c, {"bullets": [
            {"text": "Managed AP for 12 entities, saving $2M", "achievement_ids": [aid]},
            {"text": "Led team of 5", "achievement_ids": [un]},
            {"text": "Invented thing", "achievement_ids": []}], "skills": ["Tableau"]})
        self.assertFalse(fc["ok"])
        self.assertEqual(len(fc["issues"]), 5)

    def test_versions_and_encryption(self):
        a = documents.save(self.c, "master_resume", "master", {"text": "SECRETNAME v1"})
        b = documents.save(self.c, "master_resume", "master", {"text": "v2"})
        self.assertEqual((documents.get(self.c, b)["version"], documents.get(self.c, b)["parent_id"]), (2, a))
        raw = self.c.execute("SELECT content FROM documents WHERE id=?", (a,)).fetchone()[0]
        self.assertNotIn(b"SECRETNAME", bytes(raw))


class TestFollowupAnalyticsAudit(Base):
    def test_followups_and_metrics(self):
        _, app, doc = self.ready()
        crm.mark_submitted(self.c, app, "ok", "url", doc)
        later = datetime.now(timezone.utc) + timedelta(days=14)
        acts = {a["action"] for a in followup.due_actions(self.c, later)}
        self.assertEqual(acts, {"verify_confirmation", "consider_follow_up"})
        crm.add_communication(self.c, "in", "email", "hr@acme", "Thanks", "body", "confirmation", app, "m1")
        self.assertIsNone(crm.add_communication(self.c, "in", "email", "hr@acme", "Thanks", "body", None, app, "m1"))
        self.assertEqual(followup.due_actions(self.c, later), [])
        crm.set_status(self.c, app, "Initial interview")
        o = analytics.overview(self.c)
        self.assertEqual((o["total_applications"], o["interview_conversion_rate"]), (1, 100.0))

    def test_business_days(self):
        mon = datetime(2026, 11, 9, tzinfo=timezone.utc)
        self.assertEqual(followup.business_days_between(mon, mon + timedelta(days=7)), 5)

    def test_audit_chain_detects_tampering(self):
        self.assertTrue(db.verify_audit(self.c))
        self.c.execute("UPDATE audit SET action='x' WHERE id=1")
        self.assertFalse(db.verify_audit(self.c))

    def test_export_import_roundtrip(self):
        _, app, doc = self.ready()
        snap = db.export_all(self.c)
        c2 = db.connect(":memory:")
        db.import_all(c2, snap)
        self.assertEqual(profile.get(c2), profile.get(self.c))
        self.assertEqual(documents.get(c2, doc)["content"], documents.get(self.c, doc)["content"])
        self.assertTrue(db.verify_audit(c2))
        with self.assertRaises(ValueError):
            db.import_all(c2, snap)
        c2.close()

    def test_discovery_failure_is_reported_not_faked(self):
        rep = discovery.run_watchlist(self.c, [{"ats": "nope", "token": "t", "employer": "E"}])
        self.assertFalse(rep[0]["ok"])


if __name__ == "__main__":
    unittest.main()
