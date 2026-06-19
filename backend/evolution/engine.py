"""
Continuous Evolution engine — the HELIOS improvement backlog.

Every issue discovered anywhere in the platform can be captured here as a
structured backlog item: problem, impact, frequency, suggested solution,
priority, owner, status. SQLite persistence at ~/.helios/evolution.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "evolution.db"

STATUSES = ("backlog", "planned", "in_progress", "done", "wont_fix")
PRIORITIES = ("low", "medium", "high", "critical")
_PRIORITY_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class EvolutionEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS backlog_item (
                id TEXT PRIMARY KEY,
                problem TEXT,
                impact TEXT,
                frequency INTEGER DEFAULT 1,
                suggested_solution TEXT,
                priority TEXT DEFAULT 'medium',
                owner TEXT DEFAULT '',
                status TEXT DEFAULT 'backlog',
                source TEXT DEFAULT 'manual',
                tags_json TEXT DEFAULT '[]',
                created_at REAL,
                updated_at REAL
            );
            """)

    def _row(self, r) -> dict:
        cols = ["id", "problem", "impact", "frequency", "suggested_solution",
                "priority", "owner", "status", "source", "tags_json",
                "created_at", "updated_at"]
        d = dict(zip(cols, r))
        try:
            d["tags"] = json.loads(d.pop("tags_json") or "[]")
        except Exception:
            d["tags"] = []
        d["priority_score"] = _PRIORITY_WEIGHT.get(d["priority"], 2) * max(1, d.get("frequency", 1))
        return d

    def add_item(self, problem: str, impact: str = "", frequency: int = 1,
                 suggested_solution: str = "", priority: str = "medium",
                 owner: str = "", source: str = "manual", tags: list = None) -> dict:
        if priority not in PRIORITIES:
            raise ValueError(f"Unknown priority: {priority}")
        now = time.time()
        iid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO backlog_item VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (iid, problem, impact, int(frequency), suggested_solution,
                 priority, owner, "backlog", source,
                 json.dumps(tags or []), now, now)
            )
        return self.get_item(iid)

    def get_item(self, item_id: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            r = c.execute("SELECT * FROM backlog_item WHERE id=?", (item_id,)).fetchone()
        return self._row(r) if r else None

    def list_items(self, status: str = None, priority: str = None,
                   limit: int = 200) -> list:
        q = "SELECT * FROM backlog_item"
        clauses, params = [], []
        if status:
            clauses.append("status=?")
            params.append(status)
        if priority:
            clauses.append("priority=?")
            params.append(priority)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self._db) as c:
            rows = c.execute(q, params).fetchall()
        return [self._row(r) for r in rows]

    def update_item(self, item_id: str, **fields) -> Optional[dict]:
        allowed = {"problem", "impact", "frequency", "suggested_solution",
                   "priority", "owner", "status", "source"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed and v is not None:
                if k == "priority" and v not in PRIORITIES:
                    raise ValueError(f"Unknown priority: {v}")
                if k == "status" and v not in STATUSES:
                    raise ValueError(f"Unknown status: {v}")
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return self.get_item(item_id)
        sets.append("updated_at=?")
        params.append(time.time())
        params.append(item_id)
        with sqlite3.connect(self._db) as c:
            c.execute(f"UPDATE backlog_item SET {', '.join(sets)} WHERE id=?", params)
        return self.get_item(item_id)

    def set_status(self, item_id: str, status: str) -> Optional[dict]:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        return self.update_item(item_id, status=status)

    def assign(self, item_id: str, owner: str) -> Optional[dict]:
        return self.update_item(item_id, owner=owner)

    def bump_frequency(self, item_id: str, by: int = 1) -> Optional[dict]:
        item = self.get_item(item_id)
        if not item:
            return None
        return self.update_item(item_id, frequency=item["frequency"] + by)

    def prioritized(self, limit: int = 50) -> list:
        items = [i for i in self.list_items(limit=1000)
                 if i["status"] not in ("done", "wont_fix")]
        items.sort(key=lambda i: i["priority_score"], reverse=True)
        return items[:limit]

    def roadmap(self) -> dict:
        out = {s: [] for s in STATUSES}
        for i in self.list_items(limit=1000):
            out.setdefault(i["status"], []).append(i)
        return out

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM backlog_item").fetchone()[0]
            by_status = dict(c.execute(
                "SELECT status, COUNT(*) FROM backlog_item GROUP BY status").fetchall())
            by_priority = dict(c.execute(
                "SELECT priority, COUNT(*) FROM backlog_item GROUP BY priority").fetchall())
            open_count = c.execute(
                "SELECT COUNT(*) FROM backlog_item WHERE status NOT IN ('done','wont_fix')"
            ).fetchone()[0]
        return {
            "total": total,
            "open": open_count,
            "by_status": by_status,
            "by_priority": by_priority,
        }


_instance: Optional[EvolutionEngine] = None


def get_evolution_engine() -> EvolutionEngine:
    global _instance
    if _instance is None:
        _instance = EvolutionEngine()
    return _instance
