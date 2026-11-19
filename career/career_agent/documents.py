"""Versioned, encrypted document store plus the achievements / skills databases and the fact-check that keeps
tailored documents tied to verified source facts."""
import hashlib
import json
import re

from . import db

KINDS = ["source_upload", "master_resume", "master_cv", "executive_profile", "cover_letter_template",
         "tailored_resume", "tailored_cv", "cover_letter", "application_answers", "interview_prep"]
NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?[kKmMbB]?\+?")


def save(conn, kind, name, content, application_id=None, fact_check=None, actor="agent"):
    """Every save is a new immutable version; nothing is overwritten."""
    if kind not in KINDS:
        raise ValueError(f"unknown document kind {kind!r}")
    prev = conn.execute("SELECT id, version FROM documents WHERE kind=? AND name=? AND application_id IS ? "
                        "ORDER BY version DESC LIMIT 1", (kind, name, application_id)).fetchone()
    raw = json.dumps(content, sort_keys=True)
    cur = conn.execute("INSERT INTO documents(kind,name,version,parent_id,application_id,content,sha256,fact_check,"
                       "created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       (kind, name, (prev["version"] + 1) if prev else 1, prev["id"] if prev else None,
                        application_id, db.encrypt(content), hashlib.sha256(raw.encode()).hexdigest(),
                        json.dumps(fact_check) if fact_check is not None else None, db.now()))
    db.audit(conn, "document.saved", f"document:{cur.lastrowid}", {"kind": kind, "name": name}, actor)
    return cur.lastrowid


def get(conn, doc_id):
    r = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not r:
        raise KeyError(f"document {doc_id} not found")
    d = dict(r)
    d["content"] = db.decrypt(d["content"])
    d["fact_check"] = json.loads(d["fact_check"]) if d["fact_check"] else None
    return d


def listing(conn):
    return [dict(r) for r in conn.execute("SELECT id,kind,name,version,parent_id,application_id,sha256,approved,"
                                          "fact_check,created_at FROM documents ORDER BY id DESC")]


def approve(conn, doc_id):
    conn.execute("UPDATE documents SET approved=1 WHERE id=?", (doc_id,))
    db.audit(conn, "document.approved", f"document:{doc_id}", actor="user")


def add_achievement(conn, text, context=None, evidence=None, tags=None, verified=False):
    cur = conn.execute("INSERT INTO achievements(text,context,evidence,tags,verified,created_at) VALUES(?,?,?,?,?,?)",
                       (text, context, evidence, json.dumps(tags or []), int(verified), db.now()))
    db.audit(conn, "achievement.added", f"achievement:{cur.lastrowid}")
    return cur.lastrowid


def add_skill(conn, name, category=None, level=None, verified=False):
    conn.execute("INSERT INTO skills(name,category,level,verified) VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
                 "category=excluded.category, level=excluded.level, verified=excluded.verified",
                 (name, category, level, int(verified)))
    conn.commit()


def verify_fact(conn, table, row_id):
    if table not in ("achievements", "skills"):
        raise ValueError("table must be achievements or skills")
    conn.execute(f"UPDATE {table} SET verified=1 WHERE id=?", (row_id,))
    db.audit(conn, "fact.verified", f"{table}:{row_id}", actor="user")


def fact_check(conn, tailored: dict) -> dict:
    """A tailored document is structured: {'bullets': [{'text', 'achievement_ids': [...]}], 'skills': [...]}.
    Every bullet must cite verified achievements, every figure in it must appear in a cited source, and every
    listed skill must be a verified skill. Anything else is reported and blocks submission."""
    issues = []
    for i, b in enumerate(tailored.get("bullets", [])):
        ids = b.get("achievement_ids") or []
        if not ids:
            issues.append({"bullet": i, "issue": "no source achievement cited"})
            continue
        src = ""
        for aid in ids:
            r = conn.execute("SELECT * FROM achievements WHERE id=?", (aid,)).fetchone()
            if not r:
                issues.append({"bullet": i, "issue": f"achievement {aid} does not exist"})
            elif not r["verified"]:
                issues.append({"bullet": i, "issue": f"achievement {aid} is not verified by the user"})
            else:
                src += " " + r["text"] + " " + (r["context"] or "")
        src_nums = {n.rstrip("+").replace(",", "").lower() for n in NUM.findall(src)}
        for n in (NUM.findall(b.get("text", "")) if src else []):
            if n.rstrip("+").replace(",", "").lower() not in src_nums:
                issues.append({"bullet": i, "issue": f"figure {n!r} not found in cited sources"})
    known = {r["name"].lower() for r in conn.execute("SELECT name FROM skills WHERE verified=1")}
    for s in tailored.get("skills", []):
        if s.lower() not in known:
            issues.append({"skill": s, "issue": "not a verified skill"})
    return {"ok": not issues, "issues": issues}


def save_tailored(conn, kind, name, tailored, application_id):
    fc = fact_check(conn, tailored)
    return save(conn, kind, name, tailored, application_id=application_id, fact_check=fc), fc
