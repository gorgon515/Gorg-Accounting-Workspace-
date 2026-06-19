"""
Runtime mode and startup diagnostics engine.
SQLite persistence at ~/.helios/runtime.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "runtime.db"

MODES = ("production", "sandbox", "development", "daily_driver")


class RuntimeEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._mode = "production"
        self._mode_started_at = time.time()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS mode_history (
                id TEXT PRIMARY KEY,
                mode TEXT,
                started_at REAL,
                ended_at REAL,
                duration_sec REAL
            );
            CREATE TABLE IF NOT EXISTS startup_log (
                id TEXT PRIMARY KEY,
                mode TEXT,
                ok INTEGER,
                checks_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS crash_event (
                id TEXT PRIMARY KEY,
                component TEXT,
                error TEXT,
                severity TEXT,
                recovered INTEGER,
                created_at REAL
            );
            """)

    def set_mode(self, mode: str) -> dict:
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        now = time.time()
        prev_duration = now - self._mode_started_at
        hid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO mode_history VALUES (?,?,?,?,?)",
                (hid, self._mode, self._mode_started_at, now, prev_duration)
            )
        self._mode = mode
        self._mode_started_at = now
        return {"mode": mode, "started_at": now}

    def get_mode(self) -> dict:
        return {
            "mode": self._mode,
            "started_at": self._mode_started_at,
            "duration_sec": time.time() - self._mode_started_at,
            "is_production": self._mode == "production",
            "experimental_enabled": self._mode in ("sandbox", "development"),
        }

    def is_experimental_enabled(self) -> bool:
        return self._mode in ("sandbox", "development")

    def run_startup_diagnostics(self) -> dict:
        checks = {
            "dependencies": self.dependency_check(),
            "database_integrity": self.db_integrity_check(),
            "health": self.health_validation(),
        }
        ok = all(c.get("ok", False) for c in checks.values())
        now = time.time()
        sid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO startup_log VALUES (?,?,?,?,?)",
                (sid, self._mode, 1 if ok else 0, json.dumps(checks), now)
            )
        return {"ok": ok, "mode": self._mode, "checks": checks, "timestamp": now}

    def dependency_check(self) -> dict:
        deps = ["fastapi", "sqlite3", "json"]
        results = []
        for name in deps:
            try:
                __import__(name)
                available = True
            except Exception:
                available = False
            results.append({"name": name, "available": available})
        return {
            "ok": all(d["available"] for d in results),
            "dependencies": results,
        }

    def db_integrity_check(self) -> dict:
        helios_dir = Path.home() / ".helios"
        if not helios_dir.exists():
            return {"ok": True, "databases": []}
        databases = []
        all_ok = True
        for db_file in sorted(helios_dir.glob("*.db")):
            entry = {"name": db_file.name, "ok": True, "size_bytes": 0}
            try:
                entry["size_bytes"] = db_file.stat().st_size
            except Exception:
                entry["size_bytes"] = 0
            try:
                with sqlite3.connect(str(db_file)) as c:
                    row = c.execute("PRAGMA integrity_check").fetchone()
                entry["ok"] = bool(row and row[0] == "ok")
            except Exception:
                entry["ok"] = False
            if not entry["ok"]:
                all_ok = False
            databases.append(entry)
        return {"ok": all_ok, "databases": databases}

    def health_validation(self) -> dict:
        return {
            "ok": True,
            "subsystems": [
                {"name": n, "ok": True}
                for n in ["sidecar", "storage", "config"]
            ],
        }

    def safe_startup(self) -> dict:
        result = self.run_startup_diagnostics()
        return {**result, "safe": result["ok"]}

    def record_crash(self, component: str, error: str, severity: str = "error") -> dict:
        cid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO crash_event VALUES (?,?,?,?,?,?)",
                (cid, component, error, severity, 0, now)
            )
        return {
            "id": cid,
            "component": component,
            "severity": severity,
            "recovered": False,
        }

    def attempt_recovery(self, crash_id: str) -> dict:
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE crash_event SET recovered=1 WHERE id=?",
                (crash_id,)
            )
        return {"id": crash_id, "recovered": True}

    def list_crashes(self, limit: int = 50) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM crash_event ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        cols = ["id", "component", "error", "severity", "recovered", "created_at"]
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            d["recovered"] = bool(d["recovered"])
            result.append(d)
        return result

    def daily_driver_startup(self) -> dict:
        self.set_mode("daily_driver")

        try:
            health_ok = self.run_startup_diagnostics()["ok"]
        except Exception:
            health_ok = False

        try:
            from desktop.engine import get_desktop_engine
            pending_approvals = len(get_desktop_engine().list_approvals())
        except Exception:
            pending_approvals = 0

        try:
            from notifications.engine import get_notification_engine
            unread_notifications = get_notification_engine().stats().get("unread", 0)
        except Exception:
            unread_notifications = 0

        try:
            from ambient.engine import get_ambient_engine
            briefing_preview = get_ambient_engine().generate_briefing().get("voice_text", "")[:200]
        except Exception:
            briefing_preview = ""

        try:
            from presence.engine import get_presence_engine
            presence_mode = get_presence_engine().get_mode().get("mode", "work")
        except Exception:
            presence_mode = "work"

        try:
            from voice_os.engine import get_voice_os
            voice_ready = True if get_voice_os() else False
        except Exception:
            voice_ready = False

        return {
            "mode": "daily_driver",
            "health_ok": health_ok,
            "pending_approvals": pending_approvals,
            "unread_notifications": unread_notifications,
            "briefing_preview": briefing_preview,
            "presence_mode": presence_mode,
            "voice_ready": voice_ready,
            "ready": True,
            "timestamp": time.time(),
        }

    def mode_history(self, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM mode_history ORDER BY started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        cols = ["id", "mode", "started_at", "ended_at", "duration_sec"]
        return [dict(zip(cols, r)) for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_startups = c.execute("SELECT COUNT(*) FROM startup_log").fetchone()[0]
            total_crashes = c.execute("SELECT COUNT(*) FROM crash_event").fetchone()[0]
            unrecovered = c.execute(
                "SELECT COUNT(*) FROM crash_event WHERE recovered=0"
            ).fetchone()[0]
            mode_changes = c.execute("SELECT COUNT(*) FROM mode_history").fetchone()[0]
        return {
            "current_mode": self._mode,
            "total_startups": total_startups,
            "total_crashes": total_crashes,
            "unrecovered_crashes": unrecovered,
            "mode_changes": mode_changes,
        }


_instance: Optional[RuntimeEngine] = None


def get_runtime_engine() -> RuntimeEngine:
    global _instance
    if _instance is None:
        _instance = RuntimeEngine()
    return _instance
