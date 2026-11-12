"""Career Profile: encrypted, sectioned, user-editable, explicitly approved."""
from . import db

SECTIONS = ["identity", "career_interests", "employment_preferences", "compensation", "qualifications",
            "personal_preferences", "application_preferences"]

DEFAULT_SETTINGS = {
    "weights": {"career_alignment": 25, "qualifications": 20, "compensation": 15, "advancement": 15,
                "working_conditions": 10, "location": 5, "benefits": 5, "reputation": 5},
    "min_score_to_apply": 80,
    "min_score_to_keep": 60,
    "weekly_application_limit": 10,
    "allow_multiple_per_employer": False,
    "automation": {"auto_submit": False, "auto_send_routine_email": False, "calendar_write": False,
                   "email_read": False},
    "followup": {"confirm_within_hours": 24, "no_response_business_days": 7, "post_interview_business_days": 5,
                 "max_followups_per_application": 2},
    "approvals": {"profile": False, "master_documents": False, "submission_rules": False},
    "watchlist": [],
}


def settings(conn) -> dict:
    out = {}
    for k, v in DEFAULT_SETTINGS.items():
        cur = db.get_setting(conn, k, None)
        out[k] = {**v, **cur} if isinstance(v, dict) and isinstance(cur, dict) else (v if cur is None else cur)
    return out


def get(conn) -> dict:
    return {r["section"]: db.decrypt(r["value"]) for r in conn.execute("SELECT * FROM profile")}


def set_section(conn, section, value: dict, actor="user"):
    if section not in SECTIONS:
        raise ValueError(f"unknown profile section {section!r}; valid: {SECTIONS}")
    conn.execute("INSERT INTO profile(section,value,updated_at) VALUES(?,?,?) "
                 "ON CONFLICT(section) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                 (section, db.encrypt(value), db.now()))
    # Any edit invalidates the prior approval: the user must re-approve what the agent acts on.
    appr = settings(conn)["approvals"]
    if appr["profile"]:
        appr["profile"] = False
        db.set_setting(conn, "approvals", appr, actor="system")
    db.audit(conn, "profile.update", section, {"fields": sorted(value)}, actor)


def missing_sections(conn):
    have = get(conn)
    return [s for s in SECTIONS if not have.get(s)]


def approve(conn, what, actor="user"):
    appr = settings(conn)["approvals"]
    if what not in appr:
        raise ValueError(f"unknown approval {what!r}")
    if what == "profile" and missing_sections(conn):
        raise ValueError(f"profile incomplete, missing: {missing_sections(conn)}")
    appr[what] = True
    db.set_setting(conn, "approvals", appr, actor)
