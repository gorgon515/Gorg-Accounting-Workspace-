"""
Stability Analytics engine — crash analysis, failure clustering, slow-workflow
and long-running-task detection, memory-leak detection, and reliability scoring
for agents and connectors. SQLite persistence at ~/.helios/stability.db.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "stability.db"


def _signature(component: str, error: str) -> str:
    # Normalize an error to a cluster signature (component + first line, lowercased).
    head = (error or "").strip().splitlines()[0] if error else ""
    raw = f"{component}|{head}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class StabilityEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS crash (
                id TEXT PRIMARY KEY,
                component TEXT,
                error TEXT,
                severity TEXT,
                signature TEXT,
                context_json TEXT DEFAULT '{}',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS workflow_timing (
                id TEXT PRIMARY KEY,
                name TEXT,
                duration_ms REAL,
                status TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS task_run (
                id TEXT PRIMARY KEY,
                name TEXT,
                duration_ms REAL,
                status TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS memory_sample (
                id TEXT PRIMARY KEY,
                rss_mb REAL,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS reliability (
                id TEXT PRIMARY KEY,
                kind TEXT,
                name TEXT,
                success INTEGER,
                total INTEGER,
                updated_at REAL,
                UNIQUE(kind, name)
            );
            """)

    # ── Crashes ────────────────────────────────────────────────────────────────
    def record_crash(self, component: str, error: str, severity: str = "error",
                     context: dict = None) -> dict:
        cid = str(uuid.uuid4())
        sig = _signature(component, error)
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO crash VALUES (?,?,?,?,?,?,?)",
                (cid, component, error, severity, sig,
                 json.dumps(context or {}), now)
            )
        return {"id": cid, "component": component, "severity": severity,
                "signature": sig, "created_at": now}

    def crash_analysis(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM crash").fetchone()[0]
            by_component = dict(c.execute(
                "SELECT component, COUNT(*) FROM crash GROUP BY component").fetchall())
            by_severity = dict(c.execute(
                "SELECT severity, COUNT(*) FROM crash GROUP BY severity").fetchall())
        return {"total": total, "by_component": by_component,
                "by_severity": by_severity}

    def cluster_failures(self, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT signature, component, COUNT(*) cnt, MAX(error) err, "
                "MAX(created_at) last FROM crash GROUP BY signature "
                "ORDER BY cnt DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"signature": r[0], "component": r[1], "count": r[2],
                 "sample_error": r[3], "last_seen": r[4]} for r in rows]

    def list_crashes(self, limit: int = 50) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT id, component, error, severity, signature, created_at "
                "FROM crash ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        cols = ["id", "component", "error", "severity", "signature", "created_at"]
        return [dict(zip(cols, r)) for r in rows]

    # ── Workflow timing ────────────────────────────────────────────────────────
    def record_workflow(self, name: str, duration_ms: float,
                        status: str = "ok") -> dict:
        wid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO workflow_timing VALUES (?,?,?,?,?)",
                      (wid, name, float(duration_ms), status, now))
        return {"id": wid, "name": name, "duration_ms": float(duration_ms)}

    def slow_workflows(self, threshold_ms: float = 1000.0, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT name, COUNT(*) cnt, AVG(duration_ms) avg_ms, MAX(duration_ms) max_ms "
                "FROM workflow_timing GROUP BY name HAVING avg_ms >= ? "
                "ORDER BY avg_ms DESC LIMIT ?", (threshold_ms, limit)
            ).fetchall()
        return [{"name": r[0], "runs": r[1], "avg_ms": round(r[2], 2),
                 "max_ms": round(r[3], 2)} for r in rows]

    # ── Tasks ──────────────────────────────────────────────────────────────────
    def record_task(self, name: str, duration_ms: float,
                    status: str = "ok") -> dict:
        tid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO task_run VALUES (?,?,?,?,?)",
                      (tid, name, float(duration_ms), status, now))
        return {"id": tid, "name": name, "duration_ms": float(duration_ms)}

    def long_running_tasks(self, threshold_ms: float = 5000.0, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT id, name, duration_ms, status, created_at FROM task_run "
                "WHERE duration_ms >= ? ORDER BY duration_ms DESC LIMIT ?",
                (threshold_ms, limit)
            ).fetchall()
        cols = ["id", "name", "duration_ms", "status", "created_at"]
        return [dict(zip(cols, r)) for r in rows]

    # ── Memory ─────────────────────────────────────────────────────────────────
    def record_memory_sample(self, rss_mb: float) -> dict:
        mid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO memory_sample VALUES (?,?,?)",
                      (mid, float(rss_mb), now))
        return {"id": mid, "rss_mb": float(rss_mb), "created_at": now}

    def detect_memory_leak(self) -> dict:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT rss_mb, created_at FROM memory_sample ORDER BY created_at ASC"
            ).fetchall()
        n = len(rows)
        if n < 3:
            return {"leak_suspected": False, "samples": n,
                    "slope_mb_per_sample": 0.0, "reason": "insufficient samples"}
        # Simple least-squares slope of rss vs sample index.
        xs = list(range(n))
        ys = [r[0] for r in rows]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs) or 1.0
        slope = num / den
        first, last = ys[0], ys[-1]
        growth = last - first
        leak = slope > 1.0 and growth > 0  # monotonic upward drift
        return {"leak_suspected": bool(leak), "samples": n,
                "slope_mb_per_sample": round(slope, 3),
                "first_mb": round(first, 2), "last_mb": round(last, 2),
                "growth_mb": round(growth, 2)}

    # ── Reliability scoring ────────────────────────────────────────────────────
    def score_reliability(self, kind: str, name: str, success: bool,
                          total_delta: int = 1) -> dict:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT id, success, total FROM reliability WHERE kind=? AND name=?",
                (kind, name)
            ).fetchone()
            if row:
                new_success = row[1] + (1 if success else 0)
                new_total = row[2] + total_delta
                c.execute("UPDATE reliability SET success=?, total=?, updated_at=? WHERE id=?",
                          (new_success, new_total, now, row[0]))
            else:
                new_success = 1 if success else 0
                new_total = total_delta
                c.execute("INSERT INTO reliability VALUES (?,?,?,?,?,?)",
                          (str(uuid.uuid4()), kind, name, new_success, new_total, now))
        score = new_success / new_total if new_total else 0.0
        return {"kind": kind, "name": name, "success": new_success,
                "total": new_total, "score": round(score, 4)}

    def reliability_scores(self, kind: str = None) -> list:
        q = "SELECT kind, name, success, total FROM reliability"
        params = []
        if kind:
            q += " WHERE kind=?"
            params.append(kind)
        with sqlite3.connect(self._db) as c:
            rows = c.execute(q, params).fetchall()
        out = []
        for k, name, success, total in rows:
            out.append({"kind": k, "name": name, "success": success,
                        "total": total,
                        "score": round(success / total, 4) if total else 0.0})
        out.sort(key=lambda r: r["score"])
        return out

    def agent_reliability(self) -> list:
        return self.reliability_scores("agent")

    def connector_reliability(self) -> list:
        return self.reliability_scores("connector")

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            crashes = c.execute("SELECT COUNT(*) FROM crash").fetchone()[0]
            workflows = c.execute("SELECT COUNT(*) FROM workflow_timing").fetchone()[0]
            tasks = c.execute("SELECT COUNT(*) FROM task_run").fetchone()[0]
            samples = c.execute("SELECT COUNT(*) FROM memory_sample").fetchone()[0]
            tracked = c.execute("SELECT COUNT(*) FROM reliability").fetchone()[0]
        return {"crashes": crashes, "workflows_timed": workflows,
                "tasks_recorded": tasks, "memory_samples": samples,
                "reliability_tracked": tracked}


_instance: Optional[StabilityEngine] = None


def get_stability_engine() -> StabilityEngine:
    global _instance
    if _instance is None:
        _instance = StabilityEngine()
    return _instance
