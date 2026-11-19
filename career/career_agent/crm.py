"""Jobs, applications, the 17-stage pipeline, communications and interviews."""
import hashlib
import json
import re

from . import db, profile, scoring

STATUSES = ["Identified", "Evaluated", "Qualified", "Application prepared", "Application submitted",
            "Application received", "Recruiter screening", "Initial interview", "Technical assessment",
            "Second-round interview", "Final interview", "Offer received", "Negotiation", "Accepted", "Rejected",
            "Withdrawn", "No response"]
TERMINAL = {"Accepted", "Rejected", "Withdrawn"}
SUBMITTED_IDX = STATUSES.index("Application submitted")
JOB_FIELDS = ["source", "source_id", "employer", "title", "location", "arrangement", "url", "description",
              "industry", "comp_min", "comp_max", "comp_currency", "years_required"]


def fingerprint(employer, title, location):
    key = "|".join(re.sub(r"[^a-z0-9]+", " ", (x or "").lower()).strip() for x in (employer, title, location))
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def _job(row):
    d = dict(row)
    for k in ("mandatory", "preferred", "score_detail"):
        d[k] = json.loads(d[k]) if d.get(k) else ([] if k != "score_detail" else None)
    return d


def get_job(conn, job_id):
    r = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not r:
        raise KeyError(f"job {job_id} not found")
    return _job(r)


def upsert_job(conn, job: dict):
    """Insert a posting or refresh an existing one. Returns (job_id, 'new'|'updated'|'unchanged'|'rejected:<why>')."""
    for req in ("source", "employer", "title", "url"):
        if not job.get(req):
            return None, f"rejected:missing {req}"
    if not re.match(r"^https://", job["url"]):
        return None, "rejected:unverifiable url"
    fp = fingerprint(job["employer"], job["title"], job.get("location"))
    dh = hashlib.sha256((job.get("description") or "").encode()).hexdigest()
    ts = db.now()
    ex = conn.execute("SELECT id, desc_hash, source, source_id FROM jobs WHERE fingerprint=?", (fp,)).fetchone()
    sid = job.get("source_id")
    if ex and sid and ex["source"] == job["source"] and ex["source_id"] and ex["source_id"] != str(sid):
        # Same employer, title and location but a different requisition on the same board: a distinct posting.
        fp = f"{fp}:{sid}"
        ex = conn.execute("SELECT id, desc_hash, source, source_id FROM jobs WHERE fingerprint=?", (fp,)).fetchone()
    if ex:
        changed = bool(job.get("description")) and ex["desc_hash"] != dh
        if changed:
            conn.execute("UPDATE jobs SET description=?, desc_hash=?, mandatory=?, preferred=?, last_seen_at=?, "
                         "closed_at=NULL WHERE id=?",
                         (job["description"], dh, json.dumps(job.get("mandatory") or []),
                          json.dumps(job.get("preferred") or []), ts, ex["id"]))
            db.audit(conn, "job.description_changed", f"job:{ex['id']}")
        else:
            conn.execute("UPDATE jobs SET last_seen_at=?, closed_at=NULL WHERE id=?", (ts, ex["id"]))
        conn.commit()
        return ex["id"], "updated" if changed else "unchanged"
    cur = conn.execute(
        f"INSERT INTO jobs({','.join(JOB_FIELDS)},mandatory,preferred,discovered_at,last_seen_at,desc_hash,"
        f"fingerprint,verified) VALUES({','.join('?' * len(JOB_FIELDS))},?,?,?,?,?,?,?)",
        [job.get(f) for f in JOB_FIELDS] + [json.dumps(job.get("mandatory") or []),
                                            json.dumps(job.get("preferred") or []), ts, ts, dh, fp,
                                            1 if job.get("verified") else 0])
    jid = cur.lastrowid
    conn.execute("INSERT INTO applications(job_id,status,created_at,updated_at) VALUES(?,?,?,?)",
                 (jid, "Identified", ts, ts))
    aid = conn.execute("SELECT id FROM applications WHERE job_id=?", (jid,)).fetchone()["id"]
    conn.execute("INSERT INTO events(application_id,ts,kind,detail) VALUES(?,?,?,?)",
                 (aid, ts, "status", json.dumps({"to": "Identified"})))
    db.audit(conn, "job.discovered", f"job:{jid}", {"employer": job["employer"], "title": job["title"],
                                                     "source": job["source"]})
    return jid, "new"


def close_missing(conn, source, employer, seen_ids):
    """Mark postings from one source/employer that vanished from its feed as closed."""
    rows = conn.execute("SELECT id FROM jobs WHERE source=? AND employer=? AND closed_at IS NULL",
                        (source, employer)).fetchall()
    closed = [r["id"] for r in rows if r["id"] not in seen_ids]
    for jid in closed:
        conn.execute("UPDATE jobs SET closed_at=? WHERE id=?", (db.now(), jid))
        db.audit(conn, "job.closed", f"job:{jid}")
    conn.commit()
    return closed


def evaluate(conn, job_id, rated=None):
    job, st = get_job(conn, job_id), profile.settings(conn)
    res = scoring.score_job(job, profile.get(conn), st["weights"], rated)
    prof = profile.get(conn)
    ap = prof.get("application_preferences", {})
    have = max(prof.get("qualifications", {}).get("years_experience") or 0, ap.get("max_years_required") or 0)
    if (job.get("years_required") or 0) > have and str(
            prof.get("application_preferences", {}).get("experience_required_roles", "")).startswith("exclude"):
        res["excluded"] = f"requires {job['years_required']:g}+ years of experience"
        res["classification"] = "Excluded"
    conn.execute("UPDATE jobs SET score=?, score_detail=?, classification=? WHERE id=?",
                 (res["score"], json.dumps(res), res["classification"], job_id))
    app = application_for_job(conn, job_id)
    if app["status"] in ("Identified", "Evaluated", "Qualified"):
        ok = res["score"] >= st["min_score_to_apply"] and not res["provisional"] and not job["closed_at"] \
            and not res.get("excluded")
        set_status(conn, app["id"], "Qualified" if ok else "Evaluated", note="scored", _force=True)
    conn.commit()
    return res


def application_for_job(conn, job_id):
    return dict(conn.execute("SELECT * FROM applications WHERE job_id=?", (job_id,)).fetchone())


def get_application(conn, app_id):
    r = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    if not r:
        raise KeyError(f"application {app_id} not found")
    return dict(r)


def set_status(conn, app_id, status, note=None, actor="agent", _force=False):
    if status not in STATUSES:
        raise ValueError(f"invalid status {status!r}")
    app = get_application(conn, app_id)
    if status == "Application submitted" and not _force:
        raise ValueError("use mark_submitted(): a submission needs portal confirmation evidence")
    if STATUSES.index(status) > SUBMITTED_IDX and status not in ("Withdrawn",) and not app["date_applied"]:
        raise ValueError(f"cannot move to {status!r}: application was never confirmed as submitted")
    if app["status"] == status:
        return
    ts = db.now()
    outcome = status if status in TERMINAL or status == "No response" else None
    conn.execute("UPDATE applications SET status=?, updated_at=?, outcome=COALESCE(?, outcome) WHERE id=?",
                 (status, ts, outcome, app_id))
    conn.execute("INSERT INTO events(application_id,ts,kind,detail) VALUES(?,?,?,?)",
                 (app_id, ts, "status", json.dumps({"from": app["status"], "to": status, "note": note})))
    db.audit(conn, "application.status", f"application:{app_id}", {"from": app["status"], "to": status,
                                                                   "note": note}, actor)


def mark_submitted(conn, app_id, confirmation, evidence, resume_doc_id, cover_doc_id=None, actor="agent"):
    """Only path to 'Application submitted'. `confirmation` is the portal's own confirmation text or number and
    `evidence` says where it was observed (confirmation page URL, screenshot path, or email id)."""
    if not (confirmation and str(confirmation).strip() and evidence and str(evidence).strip()):
        raise ValueError("refusing to record a submission without employer-portal confirmation and evidence")
    if not resume_doc_id:
        raise ValueError("a submission must record the exact resume document that was sent")
    ts = db.now()
    conn.execute("UPDATE applications SET date_applied=?, confirmation=?, resume_doc_id=?, cover_doc_id=? WHERE id=?",
                 (ts, json.dumps({"confirmation": confirmation, "evidence": evidence}), resume_doc_id, cover_doc_id,
                  app_id))
    set_status(conn, app_id, "Application submitted", note=str(confirmation)[:200], actor=actor, _force=True)


def set_next_action(conn, app_id, action, due=None):
    conn.execute("UPDATE applications SET next_action=?, next_action_due=?, updated_at=? WHERE id=?",
                 (action, due, db.now(), app_id))
    conn.commit()


def add_communication(conn, direction, channel, counterpart, subject, body, classification=None, app_id=None,
                      external_id=None, ts=None):
    try:
        cur = conn.execute("INSERT INTO communications(application_id,ts,direction,channel,counterpart,subject,body,"
                           "classification,external_id) VALUES(?,?,?,?,?,?,?,?,?)",
                           (app_id, ts or db.now(), direction, channel, counterpart, subject, db.encrypt(body),
                            classification, external_id))
    except Exception as e:  # duplicate external_id: already ingested
        if "UNIQUE" in str(e):
            return None
        raise
    db.audit(conn, "communication.logged", f"application:{app_id}", {"direction": direction,
                                                                     "classification": classification})
    return cur.lastrowid


def add_interview(conn, app_id, scheduled_at, stage, interviewer=None):
    cur = conn.execute("INSERT INTO interviews(application_id,scheduled_at,stage,interviewer,created_at) "
                       "VALUES(?,?,?,?,?)", (app_id, scheduled_at, stage, interviewer, db.now()))
    db.audit(conn, "interview.scheduled", f"application:{app_id}", {"at": scheduled_at, "stage": stage})
    return cur.lastrowid


def interview_feedback(conn, interview_id, feedback):
    conn.execute("UPDATE interviews SET feedback=? WHERE id=?", (feedback, interview_id))
    db.audit(conn, "interview.feedback", f"interview:{interview_id}", actor="user")


def request_approval(conn, kind, question, app_id=None, context=None):
    cur = conn.execute("INSERT INTO approvals(ts,kind,application_id,question,context) VALUES(?,?,?,?,?)",
                       (db.now(), kind, app_id, question, json.dumps(context or {})))
    db.audit(conn, "approval.requested", f"application:{app_id}", {"kind": kind, "question": question})
    return cur.lastrowid


def resolve_approval(conn, approval_id, status, answer=None):
    if status not in ("approved", "denied"):
        raise ValueError("status must be approved or denied")
    conn.execute("UPDATE approvals SET status=?, answer=?, resolved_at=? WHERE id=? AND status='pending'",
                 (status, answer, db.now(), approval_id))
    db.audit(conn, "approval." + status, f"approval:{approval_id}", {"answer": answer}, actor="user")
