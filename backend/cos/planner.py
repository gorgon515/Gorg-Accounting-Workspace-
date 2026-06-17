"""Chief of Staff — memory-driven autonomous planner.

Given goals (with deadlines), tasks, and the calendar, it derives the daily pace
needed to hit each goal, schedules study/work blocks into free focus time, and
recommends task-priority adjustments. Example: "CPA exam in 45 days" → required
daily study minutes → calendar blocks + bumped study-task priority.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from calendar_intel import engine as cal
from goals.engine import forecast

# Goals expressed in study-minutes can be scheduled directly; percent goals get a
# proportional daily target translated to a default block length.
_DEFAULT_BLOCK_MIN = 60


def plan_day(goals: list[dict], tasks: list[dict], events: list[dict],
             day: Optional[date] = None, work_start: str = "09:00", work_end: str = "18:00") -> dict:
    day = day or date.today()
    slots = cal.free_slots(events, day, work_start, work_end)
    blocks = cal.focus_blocks(slots)

    recommendations: list[dict] = []
    priority_adjustments: list[dict] = []
    calendar_blocks: list[dict] = []

    # 1) For each deadline-bearing goal that is behind/on a clock, derive a daily plan.
    for g in goals:
        f = forecast(g, day)
        if f["status"] in ("complete", "no_deadline"):
            continue
        dr = f.get("days_remaining")
        pace = f.get("required_pace_per_day")
        urgency = "high" if (dr is not None and dr <= 14) or f["status"] in ("behind", "overdue") else "normal"
        rec = {
            "goal": g["title"], "status": f["status"], "days_remaining": dr,
            "required_pace_per_day": pace, "unit": g.get("unit", "%"), "urgency": urgency,
        }
        # Minutes/day: explicit if the goal is measured in minutes, else a default block.
        minutes = int(pace) if g.get("unit") == "min" and pace else _DEFAULT_BLOCK_MIN
        rec["recommended_minutes_today"] = minutes
        recommendations.append(rec)

        # Bump the priority of tasks tied to this goal (category match on title/category).
        key = g.get("category") or g["title"].split()[0].lower()
        for t in tasks:
            if t.get("status") == "done":
                continue
            if key.lower() in (t.get("category", "") + " " + t.get("title", "")).lower():
                priority_adjustments.append({"task": t["title"], "to_priority": 5,
                                             "reason": f"supports goal '{g['title']}' ({urgency} urgency)"})

    # 2) Schedule the most urgent goal recommendations into focus blocks.
    urgent_recs = sorted(recommendations, key=lambda r: (r["urgency"] != "high", r.get("days_remaining") or 9999))
    for block, rec in zip(blocks, urgent_recs):
        calendar_blocks.append({
            "start": block["start"], "end": block["end"],
            "title": f"Focus: {rec['goal']}", "minutes": min(block["minutes"], rec["recommended_minutes_today"]),
            "reason": f"{rec['status']} · {rec.get('days_remaining')} days left",
        })

    # 3) If focus blocks remain, slot in top tasks not already covered.
    used = len(calendar_blocks)
    open_tasks = sorted((t for t in tasks if t.get("status") != "done"),
                        key=lambda t: -int(t.get("priority", 3)))
    for block, task in zip(blocks[used:], open_tasks):
        calendar_blocks.append({"start": block["start"], "end": block["end"],
                                "title": f"Task: {task['title']}", "minutes": block["minutes"],
                                "reason": "open task in free focus time"})

    return {
        "date": day.isoformat(),
        "free_focus_blocks": len(blocks),
        "goal_recommendations": recommendations,
        "calendar_blocks": calendar_blocks,
        "priority_adjustments": priority_adjustments,
        "summary": (f"{len(recommendations)} active goal(s) on a clock; "
                    f"{len(calendar_blocks)} block(s) scheduled into {len(blocks)} free focus block(s); "
                    f"{len(priority_adjustments)} task priority adjustment(s) recommended."),
    }
