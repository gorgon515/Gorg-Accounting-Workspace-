"""Personal Goal System.

SQLite-backed goals with milestones, progress tracking, deadline-aware
forecasting (on-track / behind / ahead with a required-pace estimate), and
recommendations. Forecasting math is pure and unit-tested.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS goal (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT, target REAL NOT NULL DEFAULT 100,
  progress REAL NOT NULL DEFAULT 0, unit TEXT DEFAULT '%', deadline TEXT,
  milestones TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""

CATEGORIES = ["cpa", "language", "fitness", "career", "financial", "business", "reading", "learning", "personal"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _newid() -> str:
    return "goal_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:18] + os.urandom(2).hex()


def forecast(goal: dict, today: Optional[date] = None) -> dict:
    """Deadline-aware forecast.

    Compares progress made vs. time elapsed since creation against the deadline.
    Returns status (ahead/on_track/behind/no_deadline/complete), percent_complete,
    days_remaining, and the required daily pace to finish on time.
    """
    today = today or date.today()
    target = float(goal.get("target", 100)) or 100
    progress = float(goal.get("progress", 0))
    pct = round(min(100.0, progress / target * 100), 1)
    if progress >= target:
        return {"status": "complete", "percent_complete": 100.0, "days_remaining": 0, "required_pace_per_day": 0}
    if not goal.get("deadline"):
        return {"status": "no_deadline", "percent_complete": pct, "days_remaining": None, "required_pace_per_day": None}

    deadline = date.fromisoformat(goal["deadline"][:10])
    created = date.fromisoformat((goal.get("created_at") or _now())[:10])
    total_days = max(1, (deadline - created).days)
    elapsed = max(0, (today - created).days)
    days_remaining = (deadline - today).days
    expected_pct = min(100.0, elapsed / total_days * 100)
    remaining_amount = target - progress
    required_pace = round(remaining_amount / days_remaining, 3) if days_remaining > 0 else None

    if days_remaining < 0:
        status = "overdue"
    elif pct >= expected_pct + 5:
        status = "ahead"
    elif pct <= expected_pct - 5:
        status = "behind"
    else:
        status = "on_track"
    return {"status": status, "percent_complete": pct, "expected_percent": round(expected_pct, 1),
            "days_remaining": days_remaining, "required_pace_per_day": required_pace}


def recommend(goal: dict, today: Optional[date] = None) -> list[str]:
    f = forecast(goal, today)
    recs = []
    if f["status"] == "behind":
        recs.append(f"Behind pace — schedule ~{f['required_pace_per_day']} {goal.get('unit','%')}/day to finish on time.")
    elif f["status"] == "overdue":
        recs.append("Deadline passed — reset the deadline or descope the target.")
    elif f["status"] == "ahead":
        recs.append("Ahead of pace — consider raising the target or reallocating time.")
    elif f["status"] == "on_track":
        recs.append("On track — maintain current pace.")
    nxt = next((m for m in goal.get("milestones", []) if not m.get("done")), None)
    if nxt:
        recs.append(f"Next milestone: {nxt.get('title')}.")
    return recs


class GoalStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_GOALS_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "goals.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["milestones"] = json.loads(d.get("milestones") or "[]")
        return d

    def create(self, title: str, *, category: str = "personal", target: float = 100,
               unit: str = "%", deadline: Optional[str] = None, milestones: Optional[list] = None) -> dict:
        if not title or not title.strip():
            raise ValueError("title is required")
        gid = _newid()
        now = _now()
        with self._lock:
            self.conn.execute(
                "INSERT INTO goal (id,title,category,target,progress,unit,deadline,milestones,created_at,updated_at) "
                "VALUES (?,?,?,?,0,?,?,?,?,?)",
                (gid, title.strip(), category, float(target), unit, deadline,
                 json.dumps(milestones or []), now, now))
            self.conn.commit()
        return self.get(gid)

    def get(self, gid: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM goal WHERE id=?", (gid,)).fetchone()
        return self._row(r) if r else None

    def update_progress(self, gid: str, progress: float) -> dict:
        with self._lock:
            self.conn.execute("UPDATE goal SET progress=?, updated_at=? WHERE id=?",
                              (float(progress), _now(), gid))
            self.conn.commit()
        return self.get(gid)

    def add_milestone(self, gid: str, title: str, *, target: Optional[float] = None) -> dict:
        g = self.get(gid)
        if not g:
            raise ValueError("no such goal")
        ms = g["milestones"]
        ms.append({"title": title, "target": target, "done": False})
        with self._lock:
            self.conn.execute("UPDATE goal SET milestones=?, updated_at=? WHERE id=?",
                              (json.dumps(ms), _now(), gid))
            self.conn.commit()
        return self.get(gid)

    def delete(self, gid: str) -> dict:
        with self._lock:
            self.conn.execute("DELETE FROM goal WHERE id=?", (gid,))
            self.conn.commit()
        return {"deleted": gid}

    def list(self, category: Optional[str] = None) -> list[dict]:
        sql, args = "SELECT * FROM goal", []
        if category:
            sql += " WHERE category=?"; args.append(category)
        sql += " ORDER BY created_at DESC"
        return [self._row(r) for r in self.conn.execute(sql, args)]

    def dashboard(self, today: Optional[date] = None) -> dict:
        goals = []
        for g in self.list():
            goals.append({**g, "forecast": forecast(g, today), "recommendations": recommend(g, today)})
        behind = [g for g in goals if g["forecast"]["status"] in ("behind", "overdue")]
        return {"goals": goals, "count": len(goals), "behind": len(behind)}

    def close(self):
        self.conn.close()
