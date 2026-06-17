"""Chief of Staff — daily briefing.

Assembles a single executive briefing from the day's schedule, inbox, tasks,
goals, and (optionally) market + accounting intelligence. Pure synthesis over
the other engines; deterministic and unit-tested.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from calendar_intel import engine as cal
from email_intel import engine as mail
from tasks.engine import priority_score
from goals.engine import forecast


def generate(context: dict, day: Optional[date] = None) -> dict:
    day = day or date.today()
    events = context.get("events", []) or []
    emails = context.get("emails", []) or []
    tasks = context.get("tasks", []) or []
    goals = context.get("goals", []) or []
    market = context.get("market")
    accounting = context.get("accounting")

    plan = cal.daily_plan(events, tasks, day)
    inbox = mail.inbox_briefing(emails) if emails else None

    # Task priorities (actionable, unblocked handled by caller; rank by score).
    scored = sorted(
        ({**t, "score": priority_score(t, day),
          "overdue": bool(t.get("due") and t["due"][:10] < day.isoformat())} for t in tasks if t.get("status") != "done"),
        key=lambda t: (not t["overdue"], -t["score"]))
    top_tasks = scored[:5]

    # Deadlines from tasks + goals + email.
    deadlines = []
    for t in scored:
        if t.get("due"):
            deadlines.append({"what": t["title"], "when": t["due"][:10], "kind": "task"})
    for g in goals:
        if g.get("deadline"):
            f = forecast(g, day)
            deadlines.append({"what": g["title"], "when": g["deadline"][:10], "kind": "goal",
                              "status": f["status"], "days_remaining": f.get("days_remaining")})
    if inbox:
        for d in inbox.get("deadlines", [])[:5]:
            deadlines.append({"what": "(email) " + d, "when": d, "kind": "email"})
    deadlines.sort(key=lambda d: str(d.get("when")))

    # Risks: conflicts, overdue tasks, behind goals.
    risks = []
    for c in plan["conflicts"]:
        risks.append(f"Calendar conflict: {c['a']} overlaps {c['b']}.")
    for w in plan["travel_buffers"]:
        risks.append(w["suggestion"] + f" ({w['from']} → {w['to']})")
    overdue = [t for t in scored if t["overdue"]]
    if overdue:
        risks.append(f"{len(overdue)} overdue task(s): {', '.join(t['title'] for t in overdue[:3])}.")
    behind_goals = [g for g in goals if forecast(g, day)["status"] in ("behind", "overdue")]
    for g in behind_goals:
        f = forecast(g, day)
        risks.append(f"Goal behind: {g['title']} (need ~{f.get('required_pace_per_day')} {g.get('unit','%')}/day).")

    # Opportunities: focus blocks, near-complete goals.
    opportunities = []
    fb = plan["focus_blocks"]
    if fb:
        biggest = max(fb, key=lambda b: b["minutes"])
        opportunities.append(f"{biggest['minutes']}m focus block available ({biggest['start'][11:]}–{biggest['end'][11:]}) for deep work.")
    for g in goals:
        f = forecast(g, day)
        if f["status"] != "complete" and f["percent_complete"] >= 80:
            opportunities.append(f"{g['title']} is {f['percent_complete']}% done — a push could finish it.")

    # Energy allocation heuristic from the day's shape.
    energy = _energy_allocation(plan, top_tasks)

    # Recommended actions.
    actions = []
    for t in top_tasks[:3]:
        actions.append(("⚠ " if t["overdue"] else "") + f"Work on: {t['title']}.")
    if inbox:
        actions.extend(inbox["suggested_actions"][:2])
    for blk in plan["suggested_time_blocks"][:2]:
        actions.append(f"Block {blk['start'][11:]}–{blk['end'][11:]} for: {blk['task']}.")

    # Executive summary.
    parts = [f"{len(plan['events'])} meeting(s) ({plan['total_meeting_minutes']}m)",
             f"{len(scored)} open task(s), {len(overdue)} overdue"]
    if inbox:
        parts.append(f"{inbox['total']} email(s) to triage")
    if behind_goals:
        parts.append(f"{len(behind_goals)} goal(s) behind pace")
    summary = ". ".join(["Good morning. Today: " + ", ".join(parts)]) + "."

    return {
        "date": day.isoformat(),
        "executive_summary": summary,
        "todays_priorities": [{"title": t["title"], "score": t["score"], "overdue": t["overdue"], "due": t.get("due")} for t in top_tasks],
        "schedule": plan["events"],
        "important_emails": (inbox["top"] if inbox else []),
        "market_intelligence": (market.get("market_overview") if isinstance(market, dict) else None),
        "accounting_intelligence": (accounting.get("executive_summary") if isinstance(accounting, dict) else None),
        "upcoming_deadlines": deadlines[:10],
        "potential_conflicts": plan["conflicts"],
        "suggested_focus_areas": plan["suggested_time_blocks"],
        "energy_allocation": energy,
        "risks": risks,
        "opportunities": opportunities,
        "recommended_actions": actions,
        "confidence": _confidence(events, emails, tasks, goals),
    }


def _energy_allocation(plan: dict, top_tasks: list[dict]) -> list[str]:
    recs = []
    fb = plan["focus_blocks"]
    morning = [b for b in fb if b["start"][11:13] < "12"]
    if morning:
        b = max(morning, key=lambda x: x["minutes"])
        recs.append(f"Deep work in your morning block ({b['start'][11:]}–{b['end'][11:]}): "
                    + (top_tasks[0]["title"] if top_tasks else "your top priority") + ".")
    if plan["total_meeting_minutes"] > 180:
        recs.append("Heavy meeting load — protect at least one no-meeting block and keep replies short.")
    short = [b for b in plan["free_slots"] if b["minutes"] < 50]
    if short:
        recs.append(f"Batch email/admin into a short slot ({short[0]['start'][11:]}).")
    if not recs:
        recs.append("Light schedule — front-load your highest-leverage task this morning.")
    return recs


def _confidence(events, emails, tasks, goals) -> dict:
    present = sum(bool(x) for x in (events, emails, tasks, goals))
    level = "High" if present >= 3 else "Medium" if present == 2 else "Low" if present == 1 else "None"
    return {"level": level, "inputs": {"calendar": bool(events), "email": bool(emails),
                                       "tasks": bool(tasks), "goals": bool(goals)}}
