"""Submission gate: decides whether an application may be auto-submitted, needs the user's approval, or must be
finished by hand. This is the single place autonomy is granted."""
import re
from datetime import datetime, timedelta, timezone

from . import crm, profile

# Form questions that always go to the user, regardless of automation settings.
SENSITIVE = [
    ("legal_declaration", r"certify|attest|declare|under penalty|legally binding|i agree|acknowledge that|terms and conditions|arbitration"),
    ("background_check", r"background (check|investigation|screen)|credit check|drug (test|screen)|consumer report|fcra"),
    ("work_eligibility", r"authori[sz]ed to work|work authori[sz]ation|sponsorship|visa|citizen|right to work|eligib"),
    ("compensation_commitment", r"salary (expectation|requirement)|desired (salary|compensation|pay)|expected (salary|compensation)|start date|notice period"),
    ("sensitive_personal", r"social security|\bssn\b|date of birth|\bdob\b|gender|race|ethnic|veteran|disab|sexual orientation|criminal|convict|felony|passport|driver'?s licen[sc]e|bank"),
    ("restrictive_covenant", r"non-?compete|non-?solicit|restrictive covenant"),
]
BLOCKERS = r"captcha|recaptcha|hcaptcha|verify (you are|you're) human|identity verification|two-factor|2fa|one-time (code|password)"


def classify_question(text):
    t = (text or "").lower()
    return [name for name, pat in SENSITIVE if re.search(pat, t)]


def applications_this_week(conn):
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return conn.execute("SELECT COUNT(*) c FROM applications WHERE date_applied>=?", (since,)).fetchone()["c"]


def gate(conn, app_id, questions=None, page_text=""):
    """questions: [{'question': str, 'answer': str|None, 'source': 'profile'|None}]
    Returns {'mode': 'auto'|'approval'|'manual'|'blocked', 'reasons': [...], 'approval_items': [...]}"""
    st, app = profile.settings(conn), crm.get_application(conn, app_id)
    job = crm.get_job(conn, app["job_id"])
    blocked, approval = [], []

    for k, ok in st["approvals"].items():
        if not ok:
            blocked.append(f"{k} not approved by user")
    if app["date_applied"]:
        blocked.append("already submitted (duplicate)")
    if job["closed_at"]:
        blocked.append("posting closed")
    if job["score"] is None:
        blocked.append("not scored")
    elif job["score"] < st["min_score_to_apply"]:
        blocked.append(f"score {job['score']} below threshold {st['min_score_to_apply']}")
    if (job.get("score_detail") or {}).get("excluded"):
        blocked.append("excluded by your rules: " + job["score_detail"]["excluded"])
    if (job.get("score_detail") or {}).get("provisional"):
        blocked.append("score is provisional (unrated categories)")
    if not app["resume_doc_id"] and not conn.execute(
            "SELECT 1 FROM documents WHERE application_id=? AND kind='tailored_resume'", (app_id,)).fetchone():
        blocked.append("no tailored resume prepared")
    bad = conn.execute("SELECT name FROM documents WHERE application_id=? AND fact_check LIKE '%\"ok\": false%'",
                       (app_id,)).fetchall()
    if bad:
        blocked.append("fact-check failed: " + ", ".join(r["name"] for r in bad))
    if applications_this_week(conn) >= st["weekly_application_limit"]:
        blocked.append("weekly application limit reached")
    if not st["allow_multiple_per_employer"]:
        dup = conn.execute("SELECT COUNT(*) c FROM applications a JOIN jobs j ON j.id=a.job_id "
                           "WHERE j.employer=? AND a.date_applied IS NOT NULL AND a.id<>? "
                           "AND a.status NOT IN ('Rejected','Withdrawn')", (job["employer"], app_id)).fetchone()["c"]
        if dup:
            blocked.append("active application already exists at this employer")
    if blocked:
        return {"mode": "blocked", "reasons": blocked, "approval_items": []}

    if re.search(BLOCKERS, (page_text or "").lower()):
        return {"mode": "manual", "reasons": ["portal requires CAPTCHA / identity verification; never bypassed"],
                "approval_items": []}

    floor = profile.get(conn).get("compensation", {}).get("min_base")
    if floor and job["comp_max"] is not None and job["comp_max"] < floor:
        approval.append({"kind": "compensation_commitment", "question": "Posted pay is below your approved minimum"})
    for q in questions or []:
        kinds = classify_question(q.get("question"))
        if kinds:
            approval.append({"kind": kinds[0], "question": q["question"]})
        elif not q.get("answer") or q.get("source") != "profile":
            approval.append({"kind": "unverified_answer", "question": q["question"]})
    if approval:
        return {"mode": "approval", "reasons": ["contains items reserved for the user"], "approval_items": approval}
    if not st["automation"]["auto_submit"]:
        return {"mode": "approval", "reasons": ["auto-submit is switched off in settings"], "approval_items": []}
    return {"mode": "auto", "reasons": ["within approved rules"], "approval_items": []}
