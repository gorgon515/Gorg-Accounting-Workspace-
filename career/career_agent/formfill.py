"""Application form-filler.

`plan()` is pure: it maps extracted form fields to answers that exist in the verified profile and sends
everything else to the approval queue. `run()` drives a real browser (browser/fill.js), fills only planned answers,
and clicks submit only when the submission gate allows it. A submission is recorded only if the portal's own page
confirms it. CAPTCHA, logins and identity checks are reported as manual steps and never bypassed.
"""
import json
import re
import subprocess
from pathlib import Path

from . import crm, db, documents, profile, rules

FILL_JS = Path(__file__).parent / "browser" / "fill.js"
CONFIRM = re.compile(r"thank you for (applying|your application|your interest)|application (has been |was )?(received|submitted)|"
                     r"we('ve| have) received your application|successfully submitted", re.I)


def _facts(prof, resume_pdf, cover_pdf):
    i, q = prof.get("identity", {}), prof.get("qualifications", {})
    parts = (i.get("legal_name") or "").split()
    edu = (q.get("education") or [""])[0]
    return [  # (label pattern, field types, value) - first match wins
        (r"first name|given name", "text", parts[0] if parts else None),
        (r"last name|surname|family name", "text", parts[-1] if parts else None),
        (r"middle name", "text", " ".join(parts[1:-1]) or None),
        (r"^(full |legal )?name\b|your name", "text", i.get("legal_name")),
        (r"e-?mail", "text", i.get("email")),
        (r"phone|mobile|telephone", "text", i.get("phone")),
        (r"linkedin", "text", i.get("linkedin")),
        (r"\bcity\b|location|where are you (based|located)", "text", i.get("city")),
        (r"resume|\bcv\b|curriculum", "file", resume_pdf),
        (r"cover letter", "file", cover_pdf),
        (r"school|university|college|institution", "text", "Long Island University" if "Long Island University" in edu else None),
        (r"major|field of study|discipline", "text", "Accounting" if "Accounting" in edu else None),
        (r"degree", "text", "Bachelor of Science" if "B.S." in edu else None),
        (r"graduation|grad(uated)? (date|year)", "text", "May 2026" if "May 2026" in edu else None),
        (r"(major|accounting).{0,12}gpa|gpa.{0,20}(major|accounting)", "text", q.get("gpa_accounting")),
        (r"\bgpa\b|grade point", "text", q.get("gpa_overall")),
    ]


def plan(fields, prof, resume_pdf=None, cover_pdf=None, approved_answers=None):
    """Return {'fills': [...], 'questions': [...], 'skipped': [...]}. `questions` feeds rules.gate()."""
    approved = {k.strip().lower(): v for k, v in (approved_answers or {}).items()}
    facts = _facts(prof, resume_pdf, cover_pdf)
    fills, questions, skipped = [], [], []
    for f in fields:
        label, kind = (f.get("label") or "").strip(), "file" if f["type"] == "file" else "text"
        low = label.lower()
        if low in approved:  # the user answered this exact question in the approval queue
            fills.append({"idx": f["idx"], "value": approved[low]})
            questions.append({"question": label, "answer": approved[low], "source": "profile", "user_approved": True})
            continue
        sensitive = rules.classify_question(label)
        value = None
        if not sensitive and f["type"] in ("text", "email", "tel", "url", "textarea", "file", "number"):
            for pat, want, val in facts:
                if want == kind and val not in (None, "") and re.search(pat, low):
                    value = val
                    break
        if value is not None:
            fills.append({"idx": f["idx"], "value": value})
            questions.append({"question": label, "answer": str(value), "source": "profile"})
        elif sensitive or f.get("required"):
            questions.append({"question": label, "answer": None, "source": None, "options": f.get("options")})
        else:
            skipped.append(label)
    return {"fills": fills, "questions": questions, "skipped": skipped}


def run(conn, app_id, url, resume_pdf, cover_pdf=None, out_dir=".", submit=False, approved_answers=None,
        resume_doc_id=None, cover_doc_id=None):
    """Open the form, fill what the profile supports, and submit only if the gate says so.
    Returns {'outcome': 'submitted'|'filled'|'needs_approval'|'manual'|'blocked'|'error', ...}."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(["node", str(FILL_JS), url, str(out_dir)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True)
    try:
        page = json.loads(proc.stdout.readline() or '{"fatal": "browser produced no output"}')
        if page.get("fatal"):
            return _done(conn, app_id, {"outcome": "error", "error": page["fatal"], "url": url})
        if page.get("captcha") or page.get("login"):
            why = "CAPTCHA / human verification" if page.get("captcha") else "login or account creation"
            crm.set_next_action(conn, app_id, f"Manual: portal requires {why}. Apply at {url}")
            return _done(conn, app_id, {"outcome": "manual", "reason": why, "url": url})
        p = plan(page["fields"], profile.get(conn), resume_pdf, cover_pdf, approved_answers)
        pre_approved = [q for q in p["questions"] if q.get("user_approved")]
        gate = rules.gate(conn, app_id, [q for q in p["questions"] if not q.get("user_approved")], page.get("text", ""))
        do_submit = bool(submit and gate["mode"] == "auto")
        proc.stdin.write(json.dumps({"fills": p["fills"], "submit": do_submit}) + "\n")
        proc.stdin.flush()
        res = json.loads(proc.stdout.readline() or '{"fatal": "browser closed before filling"}')
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    documents.save(conn, "application_answers", f"form answers for application {app_id}",
                   {"url": url, "answers": p["questions"], "skipped_optional": p["skipped"], "gate": gate},
                   application_id=app_id)
    base = {"url": url, "gate": gate, "filled": len(p["fills"]), "pre_approved": len(pre_approved),
            "screenshots": res.get("screenshots"), "errors": res.get("errors") or res.get("fatal")}
    if res.get("fatal") or res.get("errors"):
        return _done(conn, app_id, {**base, "outcome": "error"})
    if gate["mode"] == "blocked":
        return _done(conn, app_id, {**base, "outcome": "blocked"})
    if gate["mode"] == "manual":
        return _done(conn, app_id, {**base, "outcome": "manual"})
    if gate["mode"] == "approval":
        for item in gate["approval_items"]:
            crm.request_approval(conn, item["kind"], item["question"], app_id, {"url": url})
        if not gate["approval_items"]:
            crm.request_approval(conn, "submit", "Form is filled from your verified profile. Submit this application?",
                                 app_id, {"url": url})
        return _done(conn, app_id, {**base, "outcome": "needs_approval"})
    if not do_submit:
        return _done(conn, app_id, {**base, "outcome": "filled"})
    m = CONFIRM.search(res.get("text", ""))
    if res.get("submitted_clicked") and m:
        s = res["text"]
        crm.mark_submitted(conn, app_id, s[max(0, m.start() - 80):m.end() + 160].strip(),
                           f"{res['final_url']} | {res['screenshots'][-1]}", resume_doc_id, cover_doc_id)
        return _done(conn, app_id, {**base, "outcome": "submitted"})
    crm.set_next_action(conn, app_id, f"Submit was clicked but the portal showed no confirmation. Verify at {url}")
    return _done(conn, app_id, {**base, "outcome": "unconfirmed"})


def _done(conn, app_id, result):
    db.audit(conn, "formfill." + result["outcome"], f"application:{app_id}",
             {k: v for k, v in result.items() if k in ("url", "reason", "filled", "errors", "gate")})
    return result
