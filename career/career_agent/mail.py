"""Employer email triage. Messages are fetched by the orchestrating agent (Gmail connector) and passed in as
{'id', 'from', 'subject', 'body', 'date'}. This module classifies them, links them to applications, logs them and
updates statuses when the evidence is reliable. It never sends anything."""
import re

from . import crm, db

CATEGORIES = [  # order matters: first match wins
    ("rejection", r"unfortunately|not (be )?(moving|proceeding) forward|(pursue|move forward with) other candidates|"
                  r"decided not to|position has been filled|we regret|not been selected|will not be moving"),
    ("offer", r"pleased to (offer|extend)|offer of employment|offer letter|formal offer"),
    ("assessment", r"assessment|online test|hirevue|pymetrics|aptitude test|skills test|case study exercise"),
    ("interview", r"interview|phone screen|schedule (a|some) (call|time)|your availability|like to (meet|speak) with you|"
                  r"set up a (call|time)"),
    ("document_request", r"please (provide|send|upload|submit)|transcript|additional (information|documents)|"
                         r"references"),
    ("confirmation", r"application (has been |was |is )?(received|submitted|sent)|thank(s| you) for (applying|your application|"
                     r"your interest)|we('ve| have) received your application|indeed application:|you applied"),
    ("recruiter_outreach", r"recruiter|came across your (profile|resume)|your background|exciting opportunity|"
                           r"are you open to"),
]
JOB_SIGNAL = re.compile(r"appl(y|ied|ication)|position|role|interview|recruit|candidate|resume|hiring|career|offer", re.I)
STRIP = re.compile(r"\b(llp|llc|inc|p\.?c\.?|pllc|cpa|cpas|corp|co|group|the|and|&)\b|[^a-z0-9 ]")


def classify(msg):
    text = f"{msg.get('subject', '')}\n{msg.get('body', '')}".lower()
    for name, pat in CATEGORIES:
        if re.search(pat, text):
            return name
    return "other" if JOB_SIGNAL.search(text) else "not_job_related"


def _core(name):
    return re.sub(r"\s+", " ", STRIP.sub(" ", (name or "").lower())).strip()


def match_application(conn, msg):
    """Link by employer name in sender, subject or body. Returns the best application row or None."""
    text = _core(f"{msg.get('from', '')} {msg.get('subject', '')} {msg.get('body', '')[:3000]}")
    best = None
    for r in conn.execute("SELECT a.id, a.status, a.date_applied, a.resume_doc_id, j.employer, j.title FROM applications a "
                          "JOIN jobs j ON j.id=a.job_id"):
        core = _core(r["employer"])
        if len(core) >= 4 and core in text:
            score = len(core) + (20 if _core(r["title"]) in text else 0) + (5 if r["date_applied"] else 0)
            if not best or score > best[0]:
                best = (score, dict(r))
    return best[1] if best else None


def process(conn, messages):
    """Classify, log and act on a batch. Returns a per-message report; duplicates are skipped."""
    report = []
    for m in messages:
        kind = classify(m)
        if kind == "not_job_related":
            continue
        app = match_application(conn, m)
        aid = app["id"] if app else None
        cid = crm.add_communication(conn, "in", "email", m.get("from"), m.get("subject"), m.get("body", ""), kind, aid,
                                    external_id=f"gmail:{m['id']}", ts=m.get("date"))
        if cid is None:
            continue
        entry = {"id": m["id"], "subject": m.get("subject"), "classification": kind, "application_id": aid,
                 "action": "logged"}
        if app:
            entry["action"] = _act(conn, app, kind, m)
        elif kind in ("interview", "offer", "recruiter_outreach", "assessment", "document_request"):
            crm.request_approval(conn, "unmatched_email", f"{kind.replace('_', ' ')}: {m.get('subject')}", None,
                                 {"gmail_id": m["id"], "from": m.get("from")})
            entry["action"] = "queued for your review (no matching application)"
        report.append(entry)
    return report


def _act(conn, app, kind, m):
    aid, ev = app["id"], f"gmail:{m['id']}"
    if kind == "confirmation":
        if not app["date_applied"]:
            doc = app["resume_doc_id"] or (conn.execute(
                "SELECT id FROM documents WHERE application_id=? AND kind='tailored_resume' ORDER BY id DESC LIMIT 1",
                (aid,)).fetchone() or {"id": None})["id"]
            if not doc:
                return "confirmation seen but no resume on record; not marked submitted"
            cover = conn.execute("SELECT id FROM documents WHERE application_id=? AND kind='cover_letter' "
                                 "ORDER BY id DESC LIMIT 1", (aid,)).fetchone()
            crm.mark_submitted(conn, aid, m.get("subject") or "confirmation email", ev, doc, cover["id"] if cover else None)
        crm.set_status(conn, aid, "Application received", note=ev)
        crm.set_next_action(conn, aid, None)
        return "marked submitted and received"
    if not app["date_applied"]:
        crm.request_approval(conn, "unmatched_email", f"{kind}: {m.get('subject')} (application not recorded as "
                             f"submitted)", aid, {"gmail_id": m["id"]})
        return "queued for your review (application not recorded as submitted)"
    if kind == "rejection":
        crm.set_status(conn, aid, "Rejected", note=ev)
        crm.set_next_action(conn, aid, None)
        return "status set to Rejected"
    if kind == "offer":
        crm.set_status(conn, aid, "Offer received", note=ev)
        crm.set_next_action(conn, aid, "Offer received: compensation and benefits analysis; do not reply without approval")
        return "status set to Offer received"
    if kind == "interview":
        if crm.STATUSES.index(app["status"]) < crm.STATUSES.index("Recruiter screening"):
            crm.set_status(conn, aid, "Recruiter screening", note=ev)
        crm.set_next_action(conn, aid, "Interview request: confirm a time, then prep package")
        crm.request_approval(conn, "interview_invitation", f"Interview request: {m.get('subject')}", aid,
                             {"gmail_id": m["id"]})
        return "interview request queued for you"
    if kind == "assessment":
        crm.set_status(conn, aid, "Technical assessment", note=ev)
        crm.set_next_action(conn, aid, "Assessment invitation: complete it yourself")
        return "status set to Technical assessment"
    crm.set_next_action(conn, aid, f"{kind.replace('_', ' ')}: {m.get('subject')}")
    return "next action set"
