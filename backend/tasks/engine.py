"""Task Intelligence System.

SQLite-backed tasks with priority/deadline scoring, recurrence, dependencies
(blocking), automatic categorization, project tracking, and recommendations.
Pure-logic scoring is unit-tested; the store works with an in-memory database.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, notes TEXT, project TEXT,
  priority INTEGER NOT NULL DEFAULT 3, due TEXT, status TEXT NOT NULL DEFAULT 'open',
  recurrence TEXT NOT NULL DEFAULT 'none', depends_on TEXT NOT NULL DEFAULT '[]',
  category TEXT, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);
CREATE INDEX IF NOT EXISTS idx_task_due ON task(due);
"""

_CATEGORIES = {
    "accounting": ["invoice", "ledger", "reconcile", "asc", "fasb", "audit", "close", "journal"],
    "tax": ["tax", "irs", "filing", "1040", "return", "deduction"],
    "study": ["cpa", "far", "reg", "aud", "tcp", "study", "exam", "flashcard"],
    "finance": ["portfolio", "trade", "stock", "rebalance", "market"],
    "meeting": ["meeting", "call", "sync", "1:1", "standup"],
    "email": ["email", "reply", "follow up", "follow-up", "respond"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _newid() -> str:
    return "tsk_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:18] + os.urandom(2).hex()


def categorize(title: str, notes: str = "") -> str:
    blob = f"{title} {notes}".lower()
    for cat, kws in _CATEGORIES.items():
        if any(k in blob for k in kws):
            return cat
    return "general"


def deadline_urgency(due: Optional[str], today: Optional[date] = None) -> float:
    """0–1 urgency from days-until-due (overdue → 1.0; no due → 0.2 baseline)."""
    if not due:
        return 0.2
    today = today or date.today()
    try:
        d = date.fromisoformat(due[:10])
    except ValueError:
        return 0.2
    days = (d - today).days
    if days <= 0:
        return 1.0
    if days >= 30:
        return 0.25
    return round(1.0 - (days / 30) * 0.75, 3)


def priority_score(task: dict, today: Optional[date] = None) -> float:
    """0–100 composite: priority (1–5) × deadline urgency, with a small bump for
    tasks that unblock others is handled at recommendation time."""
    pri = max(1, min(5, int(task.get("priority", 3))))
    urgency = deadline_urgency(task.get("due"), today)
    return round((pri / 5) * 50 + urgency * 50, 1)


class TaskStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_TASKS_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "tasks.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["depends_on"] = json.loads(d.get("depends_on") or "[]")
        return d

    def create(self, title: str, *, notes: str = "", project: Optional[str] = None,
               priority: int = 3, due: Optional[str] = None, recurrence: str = "none",
               depends_on: Optional[list] = None, category: Optional[str] = None) -> dict:
        if not title or not title.strip():
            raise ValueError("title is required")
        tid = _newid()
        cat = category or categorize(title, notes)
        with self._lock:
            self.conn.execute(
                "INSERT INTO task (id,title,notes,project,priority,due,status,recurrence,depends_on,category,created_at) "
                "VALUES (?,?,?,?,?,?,'open',?,?,?,?)",
                (tid, title.strip(), notes, project, int(priority), due, recurrence,
                 json.dumps(depends_on or []), cat, _now()))
            self.conn.commit()
        return self.get(tid)

    def get(self, tid: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM task WHERE id=?", (tid,)).fetchone()
        return self._row(r) if r else None

    def update(self, tid: str, **fields) -> dict:
        allowed = {"title", "notes", "project", "priority", "due", "status", "recurrence", "category"}
        sets, args = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?"); args.append(v)
        if not sets:
            return self.get(tid)
        args.append(tid)
        with self._lock:
            self.conn.execute(f"UPDATE task SET {','.join(sets)} WHERE id=?", args)
            self.conn.commit()
        return self.get(tid)

    def delete(self, tid: str) -> dict:
        with self._lock:
            self.conn.execute("DELETE FROM task WHERE id=?", (tid,))
            self.conn.commit()
        return {"deleted": tid}

    def complete(self, tid: str) -> dict:
        """Mark done; if recurring, spawn the next occurrence."""
        t = self.get(tid)
        if not t:
            raise ValueError("no such task")
        with self._lock:
            self.conn.execute("UPDATE task SET status='done', completed_at=? WHERE id=?", (_now(), tid))
            self.conn.commit()
        spawned = None
        if t["recurrence"] != "none":
            spawned = self._spawn_next(t)
        return {"completed": tid, "next": spawned}

    def _spawn_next(self, t: dict) -> Optional[dict]:
        delta = {"daily": 1, "weekly": 7, "monthly": 30}.get(t["recurrence"])
        if not delta:
            return None
        base = date.fromisoformat(t["due"][:10]) if t.get("due") else date.today()
        nxt = (base + timedelta(days=delta)).isoformat()
        return self.create(t["title"], notes=t.get("notes") or "", project=t.get("project"),
                           priority=t["priority"], due=nxt, recurrence=t["recurrence"],
                           category=t.get("category"))

    def list(self, status: Optional[str] = None, project: Optional[str] = None,
             category: Optional[str] = None) -> list[dict]:
        sql, args = "SELECT * FROM task WHERE 1=1", []
        if status:
            sql += " AND status=?"; args.append(status)
        if project:
            sql += " AND project=?"; args.append(project)
        if category:
            sql += " AND category=?"; args.append(category)
        sql += " ORDER BY COALESCE(due,'9999') ASC"
        return [self._row(r) for r in self.conn.execute(sql, args)]

    def is_blocked(self, task: dict) -> bool:
        for dep in task.get("depends_on", []):
            d = self.get(dep)
            if d and d["status"] != "done":
                return True
        return False

    def recommend(self, today: Optional[date] = None, limit: int = 8) -> list[dict]:
        """Actionable (unblocked) open tasks ranked by score; overdue first."""
        today = today or date.today()
        out = []
        for t in self.list(status="open"):
            if self.is_blocked(t):
                continue
            t = {**t, "score": priority_score(t, today),
                 "overdue": bool(t.get("due") and t["due"][:10] < today.isoformat())}
            out.append(t)
        out.sort(key=lambda x: (not x["overdue"], -x["score"]))
        return out[:limit]

    def stats(self, today: Optional[date] = None) -> dict:
        today = today or date.today()
        openn = self.list(status="open")
        overdue = [t for t in openn if t.get("due") and t["due"][:10] < today.isoformat()]
        done = self.list(status="done")
        return {"open": len(openn), "overdue": len(overdue), "done": len(done),
                "blocked": sum(1 for t in openn if self.is_blocked(t))}

    def close(self):
        self.conn.close()
