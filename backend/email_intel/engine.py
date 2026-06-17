"""Email Intelligence engine — operates on normalized emails (provider-agnostic).

Categorization, task/deadline extraction, meeting/invoice detection, priority
scoring, reply drafting, and an inbox briefing. Pure logic, fully unit-tested.
"""
from __future__ import annotations

import re
from typing import Optional

_URGENT = ["urgent", "asap", "immediately", "by eod", "end of day", "time sensitive", "deadline", "today"]
_WAITING = ["waiting on", "following up", "per my last", "any update", "circling back", "gentle reminder"]
_FOLLOWUP = ["follow up", "follow-up", "next steps", "action required", "please review", "awaiting your"]
_ACCOUNTING = ["invoice", "asc ", "fasb", "audit", "ledger", "reconcile", "journal entry", "month-end", "10-k", "10-q"]
_FINANCE = ["payment", "wire", "statement", "balance due", "portfolio", "remittance", "ach", "deposit"]
_MEETING = ["meeting", "invite", "calendar", "zoom", "google meet", "teams", "schedule a call", "availability", "let's meet"]
_INVOICE = ["invoice", "inv #", "invoice #", "amount due", "balance due", "remittance", "receipt"]

_DEADLINE_RE = re.compile(
    r"\b(?:by|due|before|no later than|deadline[: ])\s+"
    r"([A-Z][a-z]+ \d{1,2}(?:,? \d{4})?|\d{1,2}/\d{1,2}(?:/\d{2,4})?|tomorrow|today|"
    r"end of day|eod|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_ACTION_RE = re.compile(r"(?:please|kindly|can you|could you|would you|need you to|"
                        r"make sure to|don't forget to)\s+([^.!?\n]{4,120})", re.I)


def _blob(email: dict) -> str:
    return f"{email.get('subject','')} {email.get('snippet','')} {email.get('body','')}".lower()


def categorize(email: dict) -> str:
    t = _blob(email)
    if any(k in t for k in _ACCOUNTING):
        return "accounting"
    if any(k in t for k in _FINANCE):
        return "finance"
    if any(k in t for k in _URGENT):
        return "urgent"
    if any(k in t for k in _WAITING):
        return "waiting_for"
    if any(k in t for k in _FOLLOWUP) or is_meeting_request(email):
        return "follow_up"
    frm = email.get("from", "").lower()
    if (any(k in frm for k in ("noreply", "no-reply", "newsletter", "notifications"))
            or any(k in t for k in ("newsletter", "digest", "unsubscribe"))):
        return "archived"
    return "personal"


def is_meeting_request(email: dict) -> bool:
    return any(k in _blob(email) for k in _MEETING)


def is_invoice(email: dict) -> bool:
    return any(k in _blob(email) for k in _INVOICE)


def is_financial(email: dict) -> bool:
    return is_invoice(email) or any(k in _blob(email) for k in _FINANCE)


def extract_tasks(email: dict) -> list[str]:
    text = f"{email.get('snippet','')} {email.get('body','')}"
    return [m.group(1).strip().rstrip(".") for m in _ACTION_RE.finditer(text)][:8]


def extract_deadlines(email: dict) -> list[str]:
    text = f"{email.get('subject','')} {email.get('snippet','')} {email.get('body','')}"
    seen, out = set(), []
    for m in _DEADLINE_RE.finditer(text):
        v = m.group(1).strip()
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def priority_score(email: dict) -> float:
    """0–100. Urgency keywords + deadlines + meeting + unread + accounting/finance."""
    t = _blob(email)
    score = 30.0
    if any(k in t for k in _URGENT):
        score += 35
    if extract_deadlines(email):
        score += 15
    if is_meeting_request(email):
        score += 10
    if any(k in t for k in _ACCOUNTING + _FINANCE):
        score += 10
    if email.get("unread"):
        score += 5
    if "noreply" in email.get("from", "").lower() or "newsletter" in t:
        score -= 30
    return round(max(0.0, min(100.0, score)), 1)


def draft_reply(email: dict) -> str:
    cat = categorize(email)
    sender = (email.get("from", "") or "there").split("<")[0].strip() or "there"
    if is_meeting_request(email):
        return (f"Hi {sender},\n\nThanks for the note. I can meet — a few options that work for me: "
                "Tue 10:00, Wed 14:00, or Thu 11:00 (your timezone). Let me know what suits and I'll send an invite.\n\nBest,")
    if cat == "accounting" or is_invoice(email):
        return (f"Hi {sender},\n\nReceived — thank you. I'll review and route this for processing, and follow up "
                "if anything's needed. Confirming receipt for your records.\n\nBest,")
    if cat in ("follow_up", "waiting_for"):
        return (f"Hi {sender},\n\nThanks for following up. Quick status: this is in progress and I expect to have "
                "an update by end of week. I'll circle back then.\n\nBest,")
    return f"Hi {sender},\n\nThanks for your email — noted. I'll get back to you shortly.\n\nBest,"


def prioritize(emails: list[dict]) -> list[dict]:
    enriched = []
    for e in emails:
        enriched.append({**e, "category": categorize(e), "priority_score": priority_score(e),
                         "deadlines": extract_deadlines(e), "tasks": extract_tasks(e),
                         "meeting": is_meeting_request(e), "invoice": is_invoice(e)})
    enriched.sort(key=lambda x: -x["priority_score"])
    return enriched


def inbox_briefing(emails: list[dict]) -> dict:
    ranked = prioritize(emails)
    by_cat: dict[str, int] = {}
    all_tasks, all_deadlines = [], []
    for e in ranked:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
        all_tasks.extend(e["tasks"])
        all_deadlines.extend(e["deadlines"])
    top = ranked[:5]
    actions = []
    for e in top:
        if e["meeting"]:
            actions.append(f"Respond with availability: \"{e['subject']}\".")
        elif e["invoice"]:
            actions.append(f"Process invoice: \"{e['subject']}\".")
        elif e["category"] in ("urgent", "follow_up", "waiting_for"):
            actions.append(f"Reply ({e['category']}): \"{e['subject']}\".")
    return {
        "total": len(emails),
        "by_category": by_cat,
        "top": [{"from": e.get("from"), "subject": e.get("subject"), "category": e["category"],
                 "score": e["priority_score"], "deadlines": e["deadlines"]} for e in top],
        "extracted_tasks": all_tasks[:12],
        "deadlines": all_deadlines[:12],
        "suggested_actions": actions,
        "summary": (f"{len(emails)} message(s): "
                    + ", ".join(f"{n} {c}" for c, n in sorted(by_cat.items(), key=lambda kv: -kv[1]))
                    + f". {len(all_tasks)} action(s) and {len(all_deadlines)} deadline(s) detected."),
    }
