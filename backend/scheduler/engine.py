"""Scheduler Engine — persistent, timezone-aware, recoverable jobs.

Supports interval / daily@HH:MM / weekly@DOW HH:MM / cron (5-field) / once jobs.
Jobs and their run history persist in SQLite, so next-run times survive restarts
(recovery). ``run_due(now, handlers)`` is the pure, testable core; ``start()``
runs it on a background thread. Every run is audit-logged.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

_SCHEMA = """
CREATE TABLE IF NOT EXISTS job (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, handler TEXT NOT NULL, kind TEXT NOT NULL,
  spec TEXT NOT NULL, tz TEXT NOT NULL DEFAULT 'UTC', payload TEXT NOT NULL DEFAULT '{}',
  next_run TEXT, last_run TEXT, enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, ran_at TEXT NOT NULL,
  ok INTEGER NOT NULL, detail TEXT
);
"""

_DOW = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


# ---- cron (5-field: minute hour day-of-month month day-of-week) ----
def _field_match(value: int, field: str, lo: int, hi: int) -> bool:
    if field == "*":
        return True
    for part in field.split(","):
        if part.startswith("*/"):
            if (value - lo) % int(part[2:]) == 0:
                return True
        elif "-" in part:
            a, b = part.split("-")
            if int(a) <= value <= int(b):
                return True
        elif part.isdigit() and int(part) == value:
            return True
    return False


def cron_matches(dt: datetime, expr: str) -> bool:
    m, h, dom, mon, dow = expr.split()
    # Standard cron day-of-week: 0 = Sunday. Python weekday(): 0 = Monday.
    cron_dow = (dt.weekday() + 1) % 7
    return (_field_match(dt.minute, m, 0, 59)
            and _field_match(dt.hour, h, 0, 23)
            and _field_match(dt.day, dom, 1, 31)
            and _field_match(dt.month, mon, 1, 12)
            and _field_match(cron_dow, dow, 0, 6))


def compute_next_run(kind: str, spec: str, after: datetime, tzname: str = "UTC") -> datetime:
    """Next run strictly after ``after`` (aware UTC in, aware UTC out)."""
    tz = ZoneInfo(tzname)
    after = after.astimezone(tz)

    if kind == "interval":
        return (after + timedelta(seconds=float(spec))).astimezone(timezone.utc)

    if kind == "once":
        dt = datetime.fromisoformat(spec)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(timezone.utc)

    if kind == "daily":
        hh, mm = (int(x) for x in spec.split(":"))
        cand = after.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= after:
            cand += timedelta(days=1)
        return cand.astimezone(timezone.utc)

    if kind == "weekly":
        dow_s, hm = spec.split()
        target = _DOW[dow_s.lower()[:3]]
        hh, mm = (int(x) for x in hm.split(":"))
        cand = after.replace(hour=hh, minute=mm, second=0, microsecond=0)
        days = (target - cand.weekday()) % 7
        cand += timedelta(days=days)
        if cand <= after:
            cand += timedelta(days=7)
        return cand.astimezone(timezone.utc)

    if kind == "cron":
        cand = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(366 * 24 * 60):  # cap: search up to a year
            if cron_matches(cand, spec):
                return cand.astimezone(timezone.utc)
            cand += timedelta(minutes=1)
        raise ValueError(f"no cron match within a year for '{spec}'")

    raise ValueError(f"unknown job kind: {kind}")


class Scheduler:
    def __init__(self, path: Optional[str] = None, tz: str = None):
        self.path = path or os.environ.get("HELIOS_SCHED_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "scheduler.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.tz = tz or os.environ.get("HELIOS_TZ", "UTC")
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def add_job(self, name: str, handler: str, kind: str, spec: str, *,
                tz: Optional[str] = None, payload: Optional[dict] = None,
                now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        tzn = tz or self.tz
        jid = "job_" + name.lower().replace(" ", "_")[:24] + "_" + os.urandom(2).hex()
        nxt = compute_next_run(kind, spec, now, tzn).isoformat()
        with self._lock:
            self.conn.execute(
                "INSERT INTO job (id,name,handler,kind,spec,tz,payload,next_run,enabled,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,1,?)",
                (jid, name, handler, kind, spec, tzn, json.dumps(payload or {}), nxt, now.isoformat()))
            self.conn.commit()
        return self.get(jid)

    def get(self, jid: str) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM job WHERE id=?", (jid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["payload"] = json.loads(d.get("payload") or "{}")
        d["enabled"] = bool(d["enabled"])
        return d

    def list(self) -> list[dict]:
        return [self.get(r["id"]) for r in self.conn.execute("SELECT id FROM job ORDER BY next_run")]

    def set_enabled(self, jid: str, enabled: bool) -> dict:
        with self._lock:
            self.conn.execute("UPDATE job SET enabled=? WHERE id=?", (1 if enabled else 0, jid))
            self.conn.commit()
        return self.get(jid)

    def remove(self, jid: str) -> dict:
        with self._lock:
            self.conn.execute("DELETE FROM job WHERE id=?", (jid,))
            self.conn.commit()
        return {"removed": jid}

    def due_jobs(self, now: Optional[datetime] = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        return [j for j in self.list() if j["enabled"] and j["next_run"] and j["next_run"] <= now.isoformat()]

    def run_due(self, now: Optional[datetime] = None,
                handlers: Optional[dict[str, Callable]] = None) -> list[dict]:
        """Run all due jobs via the handler registry; advance schedules; audit."""
        now = now or datetime.now(timezone.utc)
        handlers = handlers or {}
        results = []
        for job in self.due_jobs(now):
            ok, detail = True, None
            fn = handlers.get(job["handler"])
            try:
                if fn is None:
                    ok, detail = False, f"no handler '{job['handler']}'"
                else:
                    out = fn(job.get("payload") or {})
                    detail = (str(out)[:200] if out is not None else "ok")
            except Exception as exc:  # noqa: BLE001 - a failing job must not kill the loop
                ok, detail = False, str(exc)[:200]
            self._record_run(job["id"], now, ok, detail)
            self._advance(job, now)
            results.append({"job": job["name"], "handler": job["handler"], "ok": ok, "detail": detail})
        return results

    def _advance(self, job: dict, now: datetime) -> None:
        with self._lock:
            if job["kind"] == "once":
                self.conn.execute("UPDATE job SET enabled=0, last_run=? WHERE id=?", (now.isoformat(), job["id"]))
            else:
                nxt = compute_next_run(job["kind"], job["spec"], now, job["tz"]).isoformat()
                self.conn.execute("UPDATE job SET next_run=?, last_run=? WHERE id=?",
                                  (nxt, now.isoformat(), job["id"]))
            self.conn.commit()

    def _record_run(self, job_id: str, now: datetime, ok: bool, detail: Optional[str]) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO job_run (job_id,ran_at,ok,detail) VALUES (?,?,?,?)",
                              (job_id, now.isoformat(), 1 if ok else 0, detail))
            self.conn.commit()

    def history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM job_run ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    # ---- background loop (production) ----
    def start(self, handlers: dict[str, Callable], poll_seconds: float = 30) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.run_due(handlers=handlers)
                except Exception:  # noqa: BLE001
                    pass
                self._stop.wait(poll_seconds)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def close(self):
        self.stop()
        self.conn.close()
