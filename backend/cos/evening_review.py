"""Chief of Staff — evening review.

Summarizes the day (completed/missed work, meetings, inbox), tracks learning and
optionally portfolio/accounting, prepares tomorrow, and offers reflection prompts.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from calendar_intel import engine as cal
from tasks.engine import priority_score


def generate(context: dict, day: Optional[date] = None) -> dict:
    day = day or date.today()
    tomorrow = day + timedelta(days=1)
    tasks = context.get("tasks", []) or []
    events = context.get("events", []) or []
    emails = context.get("emails", []) or []
    goals_progress = context.get("goals_progress", []) or []  # [{title, delta, percent}]
    portfolio = context.get("portfolio")
    accounting = context.get("accounting")

    completed = [t for t in tasks if t.get("status") == "done"
                 and (t.get("completed_at") or "")[:10] == day.isoformat()]
    missed = [t for t in tasks if t.get("status") != "done"
              and t.get("due") and t["due"][:10] <= day.isoformat()]

    todays_events = [e for e in events if (cal.parse_dt(e.get("start", "")) and
                                           cal.parse_dt(e["start"]).date() == day)]
    tomorrows_events = [e for e in events if (cal.parse_dt(e.get("start", "")) and
                                              cal.parse_dt(e["start"]).date() == tomorrow)]
    top_tomorrow = sorted((t for t in tasks if t.get("status") != "done"),
                          key=lambda t: -priority_score(t, tomorrow))[:5]

    productivity = round(len(completed) / (len(completed) + len(missed)) * 100, 0) if (completed or missed) else None

    return {
        "date": day.isoformat(),
        "completed_work": [{"title": t["title"], "category": t.get("category")} for t in completed],
        "missed_tasks": [{"title": t["title"], "due": t.get("due")} for t in missed],
        "productivity_score": productivity,
        "meeting_summary": {"count": len(todays_events),
                            "titles": [e.get("title") for e in todays_events]},
        "inbox_summary": {"processed_estimate": len(emails),
                          "note": "Triage complete" if emails else "No inbox data"},
        "learning_progress": goals_progress,
        "portfolio_review": (portfolio.get("market_overview") if isinstance(portfolio, dict) else portfolio),
        "accounting_updates": (accounting.get("executive_summary") if isinstance(accounting, dict) else accounting),
        "tomorrow_preparation": {
            "events": [{"title": e.get("title"), "start": e.get("start")} for e in tomorrows_events],
            "top_tasks": [{"title": t["title"], "due": t.get("due")} for t in top_tomorrow],
        },
        "reflection_notes": [
            f"You completed {len(completed)} task(s)" + (f" and missed {len(missed)}." if missed else "."),
            "What was the highest-leverage thing you did today?",
            "What is the one thing that, if done tomorrow, makes the day a win?",
        ],
    }
