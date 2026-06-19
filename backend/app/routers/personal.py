"""Phase-5 personal chief-of-staff endpoints: tasks, goals, scheduler, email &
calendar intelligence, and the Chief of Staff (briefing / review / plan)."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Query

from ..models import (
    CalendarPlanRequest, CosContext, EmailBatch, GoalCreate, JobCreate,
    ProgressUpdate, TaskCreate, TaskUpdate,
)
from tasks.engine import TaskStore
from goals.engine import GoalStore
from scheduler.engine import Scheduler
from email_intel import engine as mail
from calendar_intel import engine as cal
from cos import daily_briefing, evening_review, planner
from accounting.collectors.registry import collect_all
from accounting.storage.db import IntelStore

router = APIRouter(tags=["personal"])

# Shared, file-backed stores (paths overridable via env).
_tasks = TaskStore()
_goals = GoalStore()
_sched = Scheduler()


# Scheduler handlers: real work the jobs can do without external data.
def _accounting_refresh(_payload: dict) -> str:
    items, errors = collect_all()
    res = IntelStore().upsert_many(items)
    return f"intel refresh: +{res['inserted']} ({len(errors)} sources unreachable)"


def _memory_maintenance(_payload: dict) -> str:
    return "memory maintenance tick"


SCHED_HANDLERS = {
    "accounting_refresh": _accounting_refresh,
    "memory_maintenance": _memory_maintenance,
    "morning_briefing": lambda p: "morning briefing tick",
    "evening_review": lambda p: "evening review tick",
    "noop": lambda p: "ok",
}


# ---- Tasks ----
@router.post("/tasks")
def create_task(req: TaskCreate):
    return _tasks.create(req.title, notes=req.notes, project=req.project, priority=req.priority,
                         due=req.due, recurrence=req.recurrence, depends_on=req.depends_on, category=req.category)


@router.get("/tasks")
def list_tasks(status: str = None, project: str = None, category: str = None):
    return {"tasks": _tasks.list(status=status, project=project, category=category), "stats": _tasks.stats()}


@router.post("/tasks/update")
def update_task(req: TaskUpdate):
    return _tasks.update(req.id, **req.fields)


@router.post("/tasks/{tid}/complete")
def complete_task(tid: str):
    return _tasks.complete(tid)


@router.delete("/tasks/{tid}")
def delete_task(tid: str):
    return _tasks.delete(tid)


@router.get("/tasks/recommend")
def recommend_tasks(limit: int = 8):
    return {"recommended": _tasks.recommend(limit=limit)}


# ---- Goals ----
@router.post("/goals")
def create_goal(req: GoalCreate):
    return _goals.create(req.title, category=req.category, target=req.target, unit=req.unit,
                         deadline=req.deadline, milestones=req.milestones)


@router.get("/goals")
def goals_dashboard():
    return _goals.dashboard()


@router.post("/goals/progress")
def goal_progress(req: ProgressUpdate):
    return _goals.update_progress(req.id, req.progress)


@router.delete("/goals/{gid}")
def delete_goal(gid: str):
    return _goals.delete(gid)


# ---- Scheduler ----
@router.get("/scheduler/jobs")
def list_jobs():
    return {"jobs": _sched.list(), "handlers": sorted(SCHED_HANDLERS)}


@router.post("/scheduler/jobs")
def add_job(req: JobCreate):
    return _sched.add_job(req.name, req.handler, req.kind, req.spec, tz=req.tz, payload=req.payload)


@router.post("/scheduler/seed")
def seed_jobs():
    """Create the default operating-system jobs (idempotent-ish per name)."""
    existing = {j["name"] for j in _sched.list()}
    created = []
    defaults = [
        ("Morning briefing", "morning_briefing", "daily", "07:00"),
        ("Evening review", "evening_review", "daily", "18:00"),
        ("Accounting refresh", "accounting_refresh", "cron", "0 * * * *"),
        ("Memory maintenance", "memory_maintenance", "daily", "03:00"),
    ]
    for name, handler, kind, spec in defaults:
        if name not in existing:
            created.append(_sched.add_job(name, handler, kind, spec))
    return {"created": [c["name"] for c in created], "total": len(_sched.list())}


@router.post("/scheduler/tick")
def scheduler_tick():
    """Run all due jobs now (the background loop does this automatically)."""
    return {"ran": _sched.run_due(handlers=SCHED_HANDLERS)}


@router.get("/scheduler/history")
def scheduler_history(limit: int = 50):
    return {"history": _sched.history(limit)}


# ---- Email intelligence ----
@router.post("/email/triage")
def email_triage(req: EmailBatch):
    return {"emails": mail.prioritize(req.emails)}


@router.post("/email/briefing")
def email_briefing(req: EmailBatch):
    return mail.inbox_briefing(req.emails)


# ---- Calendar intelligence ----
@router.post("/calendar/plan")
def calendar_plan(req: CalendarPlanRequest):
    return cal.daily_plan(req.events, req.tasks, work_start=req.work_start, work_end=req.work_end)


# ---- Chief of Staff ----
@router.post("/cos/daily-briefing")
def cos_daily_briefing(ctx: CosContext):
    context = ctx.model_dump()
    if context.get("tasks") is None:
        context["tasks"] = _tasks.list(status="open")
    if context.get("goals") is None:
        context["goals"] = [g for g in _goals.dashboard()["goals"]]
    return daily_briefing.generate(context)


@router.post("/cos/evening-review")
def cos_evening_review(ctx: CosContext):
    context = ctx.model_dump()
    if context.get("tasks") is None:
        context["tasks"] = _tasks.list()
    return evening_review.generate(context)


@router.post("/cos/plan")
def cos_plan(ctx: CosContext):
    context = ctx.model_dump()
    tasks = context.get("tasks") if context.get("tasks") is not None else _tasks.list(status="open")
    goals = context.get("goals") if context.get("goals") is not None else _goals.dashboard()["goals"]
    return planner.plan_day(goals, tasks, context.get("events", []))


@router.get("/cos/plan/auto")
def cos_plan_auto():
    """Plan the day from the sidecar's own task + goal stores (no external data)."""
    return planner.plan_day(_goals.dashboard()["goals"], _tasks.list(status="open"), [])


@router.get("/cos/briefing/auto")
def cos_briefing_auto():
    """Briefing from the sidecar's own stores (calendar/email come from the app)."""
    return daily_briefing.generate({"tasks": _tasks.list(status="open"),
                                    "goals": _goals.dashboard()["goals"]})
