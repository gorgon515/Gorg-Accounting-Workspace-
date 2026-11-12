"""Follow-up engine: computes what is due. It proposes; sending is gated elsewhere."""
from datetime import datetime, timedelta, timezone

from . import crm, profile

FMT = "%Y-%m-%dT%H:%M:%SZ"


def business_days_between(start: datetime, end: datetime) -> int:
    days, d = 0, start.date()
    while d < end.date():
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def due_actions(conn, now=None):
    now = now or datetime.now(timezone.utc)
    rules = profile.settings(conn)["followup"]
    out = []
    for a in conn.execute("SELECT a.*, j.employer, j.title FROM applications a JOIN jobs j ON j.id=a.job_id"):
        if a["status"] in crm.TERMINAL or not a["date_applied"]:
            continue
        applied = datetime.strptime(a["date_applied"], FMT).replace(tzinfo=timezone.utc)
        base = {"application_id": a["id"], "employer": a["employer"], "title": a["title"], "status": a["status"]}
        sent = conn.execute("SELECT COUNT(*) c FROM communications WHERE application_id=? AND direction='out' "
                            "AND classification='follow_up'", (a["id"],)).fetchone()["c"]
        inbound = conn.execute("SELECT MAX(ts) t FROM communications WHERE application_id=? AND direction='in'",
                               (a["id"],)).fetchone()["t"]
        if a["status"] == "Application submitted" and (now - applied) >= timedelta(hours=rules["confirm_within_hours"]) \
                and not inbound:
            out.append({**base, "action": "verify_confirmation",
                        "why": f"no confirmation email {rules['confirm_within_hours']}h after submission"})
        if a["status"] in ("Application submitted", "Application received") and not inbound \
                and business_days_between(applied, now) >= rules["no_response_business_days"] \
                and sent < rules["max_followups_per_application"]:
            out.append({**base, "action": "consider_follow_up",
                        "why": f"{business_days_between(applied, now)} business days without a response"})
        for iv in conn.execute("SELECT * FROM interviews WHERE application_id=?", (a["id"],)):
            if not iv["scheduled_at"]:
                continue
            when = datetime.strptime(iv["scheduled_at"], FMT).replace(tzinfo=timezone.utc)
            if when > now and not iv["prep_doc_id"]:
                out.append({**base, "action": "prepare_interview", "why": f"{iv['stage']} on {iv['scheduled_at']}"})
            if when <= now and not iv["feedback"]:
                out.append({**base, "action": "collect_feedback_and_thank_you", "why": f"{iv['stage']} completed"})
            if when <= now and business_days_between(when, now) >= rules["post_interview_business_days"] \
                    and (not inbound or inbound < iv["scheduled_at"]) and sent < rules["max_followups_per_application"]:
                out.append({**base, "action": "post_interview_follow_up", "why": "no response since interview"})
        if a["status"] == "Offer received":
            out.append({**base, "action": "analyze_offer", "why": "offer needs compensation and benefits analysis"})
    return out
