"""Dashboard metrics. Every number is derived from recorded rows; nothing is estimated."""
from datetime import datetime, timedelta, timezone

from . import crm

INTERVIEW = {"Recruiter screening", "Initial interview", "Technical assessment", "Second-round interview",
             "Final interview", "Offer received", "Negotiation", "Accepted"}
OFFER = {"Offer received", "Negotiation", "Accepted"}


def _rate(n, d):
    return round(100 * n / d, 1) if d else None


def _reached(conn, app_id, stages):
    rows = conn.execute("SELECT ts, detail FROM events WHERE application_id=? AND kind='status' ORDER BY id",
                        (app_id,)).fetchall()
    import json
    for r in rows:
        if json.loads(r["detail"]).get("to") in stages:
            return r["ts"]
    return None


def _days(a, b):
    f = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds() / 86400


def overview(conn):
    apps = [dict(r) for r in conn.execute(
        "SELECT a.*, j.employer, j.industry, j.title, j.comp_min, j.comp_max FROM applications a "
        "JOIN jobs j ON j.id=a.job_id")]
    sub = [a for a in apps if a["date_applied"]]
    week = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    t_int, t_off, interviewed, offered = [], [], 0, 0
    for a in sub:
        ti, to = _reached(conn, a["id"], INTERVIEW), _reached(conn, a["id"], OFFER)
        if ti:
            interviewed += 1
            t_int.append(_days(a["date_applied"], ti))
        if to:
            offered += 1
            t_off.append(_days(a["date_applied"], to))
    def group(key):
        out = {}
        for a in sub:
            out[a[key] or "Unspecified"] = out.get(a[key] or "Unspecified", 0) + 1
        return out
    resume = {}
    for a in sub:
        k = str(a["resume_doc_id"])
        resume.setdefault(k, {"submitted": 0, "interviews": 0})
        resume[k]["submitted"] += 1
        resume[k]["interviews"] += 1 if _reached(conn, a["id"], INTERVIEW) else 0
    rejected = sum(a["status"] == "Rejected" for a in sub)
    return {
        "jobs_discovered": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
        "total_applications": len(sub),
        "submitted_this_week": sum(a["date_applied"] >= week for a in sub),
        "active_opportunities": sum(a["status"] not in crm.TERMINAL and a["status"] != "No response" for a in sub),
        "interview_invitations": interviewed,
        "pending_responses": sum(a["status"] in ("Application submitted", "Application received") for a in sub),
        "offers_received": offered,
        "rejection_rate": _rate(rejected, len(sub)),
        "interview_conversion_rate": _rate(interviewed, len(sub)),
        "offer_conversion_rate": _rate(offered, len(sub)),
        "by_status": {s: sum(a["status"] == s for a in apps) for s in crm.STATUSES},
        "by_industry": group("industry"), "by_employer": group("employer"),
        "avg_days_to_interview": round(sum(t_int) / len(t_int), 1) if t_int else None,
        "avg_days_to_offer": round(sum(t_off) / len(t_off), 1) if t_off else None,
        "resume_versions": resume,
        "pending_approvals": conn.execute("SELECT COUNT(*) c FROM approvals WHERE status='pending'").fetchone()["c"],
    }
