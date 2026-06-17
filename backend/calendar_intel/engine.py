"""Calendar Intelligence engine — operates on normalized events.

Conflict detection, free/focus-block discovery, task time-blocking, travel-buffer
suggestions, meeting prep, and a daily plan. Pure datetime logic, unit-tested.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional


def parse_dt(s: str) -> Optional[datetime]:
    """Parse an ISO datetime/date to a naive wall-clock datetime."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.fromisoformat(s[:10])  # date-only
        except ValueError:
            return None
    return dt.replace(tzinfo=None)


def _events_on(events: list[dict], day: date) -> list[dict]:
    out = []
    for e in events:
        st = parse_dt(e.get("start", ""))
        if st and st.date() == day:
            out.append(e)
    return sorted(out, key=lambda e: parse_dt(e["start"]) or datetime.max)


def detect_conflicts(events: list[dict]) -> list[dict]:
    """Overlapping event pairs."""
    timed = [(parse_dt(e.get("start", "")), parse_dt(e.get("end", "")), e) for e in events]
    timed = [(s, en, e) for s, en, e in timed if s and en]
    timed.sort(key=lambda x: x[0])
    conflicts = []
    for i in range(len(timed)):
        for j in range(i + 1, len(timed)):
            si, ei, ei_e = timed[i]
            sj, ej, ej_e = timed[j]
            if sj < ei:  # j starts before i ends → overlap
                conflicts.append({"a": ei_e.get("title"), "b": ej_e.get("title"),
                                  "a_start": ei_e.get("start"), "b_start": ej_e.get("start")})
            else:
                break
    return conflicts


def free_slots(events: list[dict], day: date, work_start: str = "09:00", work_end: str = "18:00") -> list[dict]:
    """Gaps between events within working hours on ``day``."""
    sh, sm = (int(x) for x in work_start.split(":"))
    eh, em = (int(x) for x in work_end.split(":"))
    cursor = datetime.combine(day, datetime.min.time()).replace(hour=sh, minute=sm)
    end_of_day = datetime.combine(day, datetime.min.time()).replace(hour=eh, minute=em)
    slots = []
    for e in _events_on(events, day):
        st, en = parse_dt(e["start"]), parse_dt(e.get("end", ""))
        if not st or not en:
            continue
        if st > cursor:
            mins = int((min(st, end_of_day) - cursor).total_seconds() // 60)
            if mins >= 15:
                slots.append({"start": cursor.isoformat(timespec="minutes"),
                              "end": min(st, end_of_day).isoformat(timespec="minutes"), "minutes": mins})
        cursor = max(cursor, en)
    if cursor < end_of_day:
        mins = int((end_of_day - cursor).total_seconds() // 60)
        if mins >= 15:
            slots.append({"start": cursor.isoformat(timespec="minutes"),
                          "end": end_of_day.isoformat(timespec="minutes"), "minutes": mins})
    return slots


def focus_blocks(slots: list[dict], min_minutes: int = 50) -> list[dict]:
    return [s for s in slots if s["minutes"] >= min_minutes]


def suggest_time_blocks(tasks: list[dict], slots: list[dict]) -> list[dict]:
    """Assign the highest-scoring tasks into focus blocks (one per block)."""
    blocks = focus_blocks(slots)
    ranked = sorted(tasks, key=lambda t: -float(t.get("score", t.get("priority", 3))))
    out = []
    for block, task in zip(blocks, ranked):
        out.append({"start": block["start"], "end": block["end"], "minutes": block["minutes"],
                    "task": task.get("title"), "task_id": task.get("id")})
    return out


def travel_buffers(events: list[dict], buffer_min: int = 30) -> list[dict]:
    """Flag back-to-back events at different physical locations with too little gap."""
    timed = sorted([(parse_dt(e.get("start", "")), parse_dt(e.get("end", "")), e) for e in events
                    if parse_dt(e.get("start", ""))], key=lambda x: x[0])
    warnings = []
    for (s1, e1, ev1), (s2, e2, ev2) in zip(timed, timed[1:]):
        loc1, loc2 = (ev1.get("location") or "").strip(), (ev2.get("location") or "").strip()
        if loc1 and loc2 and loc1.lower() != loc2.lower() and e1:
            gap = int((s2 - e1).total_seconds() // 60)
            if gap < buffer_min:
                warnings.append({"from": ev1.get("title"), "to": ev2.get("title"),
                                 "gap_minutes": gap, "from_location": loc1, "to_location": loc2,
                                 "suggestion": f"Only {gap}m between locations — add a travel buffer."})
    return warnings


def meeting_prep(event: dict) -> dict:
    attendees = event.get("attendees", []) or []
    checklist = [
        "Review the agenda and desired outcome",
        f"Confirm attendees ({len(attendees)}) and roles" if attendees else "Confirm attendees",
        "Gather relevant documents / prior notes",
        "Prepare your talking points and questions",
    ]
    if event.get("location"):
        checklist.append(f"Plan travel/logistics to {event['location']}")
    return {"title": event.get("title"), "when": event.get("start"),
            "attendees": attendees, "checklist": checklist}


def daily_plan(events: list[dict], tasks: list[dict], day: Optional[date] = None,
               work_start: str = "09:00", work_end: str = "18:00") -> dict:
    day = day or date.today()
    todays = _events_on(events, day)
    slots = free_slots(events, day, work_start, work_end)
    return {
        "date": day.isoformat(),
        "events": [{"title": e.get("title"), "start": e.get("start"), "end": e.get("end"),
                    "location": e.get("location")} for e in todays],
        "conflicts": detect_conflicts(todays),
        "travel_buffers": travel_buffers(todays),
        "free_slots": slots,
        "focus_blocks": focus_blocks(slots),
        "suggested_time_blocks": suggest_time_blocks(tasks, slots),
        "total_meeting_minutes": sum(
            int(((parse_dt(e.get("end", "")) or parse_dt(e.get("start", ""))) - parse_dt(e["start"])).total_seconds() // 60)
            for e in todays if parse_dt(e.get("start", "")) and parse_dt(e.get("end", ""))),
    }
