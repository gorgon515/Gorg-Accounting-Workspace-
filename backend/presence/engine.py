"""
Presence and mode awareness engine.
SQLite persistence at ~/.helios/presence.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "presence.db"

MODES = ("work", "study", "market", "accounting", "personal", "break", "meeting", "away")


class PresenceEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._current_mode = "work"
        self._mode_started_at = time.time()
        self._context = {
            "app": "", "task": "", "url": "", "document": "", "updated_at": time.time()
        }
        self._calendar_status = {
            "status": "free", "meeting_title": "", "ends_at": None, "updated_at": time.time()
        }
        self._focus_state = {
            "enabled": False, "ends_at": None, "goal": "", "duration_min": 0,
            "started_at": None
        }

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS mode_history (
                id TEXT PRIMARY KEY,
                mode TEXT,
                context_json TEXT DEFAULT '{}',
                started_at REAL,
                ended_at REAL,
                duration_sec REAL
            );
            """)

    def set_mode(self, mode: str, context: dict = None) -> dict:
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        now = time.time()
        # Save previous mode to history
        prev_duration = now - self._mode_started_at
        hid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO mode_history VALUES (?,?,?,?,?,?)",
                (hid, self._current_mode, json.dumps(self._context),
                 self._mode_started_at, now, prev_duration)
            )
        self._current_mode = mode
        self._mode_started_at = now
        if context:
            self._context.update(context)
            self._context["updated_at"] = now
        return {"mode": mode, "started_at": now, "context": self._context.copy()}

    def get_mode(self) -> dict:
        return {
            "mode": self._current_mode,
            "started_at": self._mode_started_at,
            "duration_sec": time.time() - self._mode_started_at,
        }

    def update_context(self, app: str = "", task: str = "", url: str = "",
                       document: str = "") -> dict:
        now = time.time()
        if app:
            self._context["app"] = app
        if task:
            self._context["task"] = task
        if url:
            self._context["url"] = url
        if document:
            self._context["document"] = document
        self._context["updated_at"] = now
        return self._context.copy()

    def get_context(self) -> dict:
        return self._context.copy()

    def set_calendar_status(self, status: str, meeting_title: str = "",
                            ends_at: float = None) -> dict:
        now = time.time()
        self._calendar_status = {
            "status": status,
            "meeting_title": meeting_title,
            "ends_at": ends_at,
            "updated_at": now,
        }
        return self._calendar_status.copy()

    def get_calendar_status(self) -> dict:
        return self._calendar_status.copy()

    def set_focus(self, enabled: bool, duration_min: int = 0, goal: str = "") -> dict:
        now = time.time()
        ends_at = None
        if enabled and duration_min > 0:
            ends_at = now + duration_min * 60
        self._focus_state = {
            "enabled": enabled,
            "ends_at": ends_at,
            "goal": goal,
            "duration_min": duration_min,
            "started_at": now if enabled else None,
        }
        return self._focus_state.copy()

    def get_focus(self) -> dict:
        return self._focus_state.copy()

    def get_state(self) -> dict:
        return {
            "mode": self._current_mode,
            "mode_started_at": self._mode_started_at,
            "mode_duration_sec": time.time() - self._mode_started_at,
            "context": self._context.copy(),
            "calendar": self._calendar_status.copy(),
            "focus": self._focus_state.copy(),
        }

    def mode_history(self, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM mode_history ORDER BY started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        cols = ["id", "mode", "context_json", "started_at", "ended_at", "duration_sec"]
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            try:
                d["context"] = json.loads(d.pop("context_json") or "{}")
            except Exception:
                d["context"] = {}
            result.append(d)
        return result

    def adaptive_config(self) -> dict:
        mode = self._current_mode
        if mode == "market":
            return {
                "notification_level": "high",
                "voice_sensitivity": "low",
                "briefing_freq": "hourly",
            }
        elif mode in ("accounting", "work"):
            return {
                "notification_level": "medium",
                "voice_sensitivity": "medium",
                "briefing_freq": "daily",
            }
        elif mode == "study":
            return {
                "notification_level": "low",
                "voice_sensitivity": "low",
                "briefing_freq": "daily",
            }
        elif mode in ("break", "away"):
            return {
                "notification_level": "low",
                "voice_sensitivity": "high",
                "briefing_freq": "none",
            }
        elif mode == "meeting":
            return {
                "notification_level": "low",
                "voice_sensitivity": "low",
                "briefing_freq": "none",
            }
        elif mode == "personal":
            return {
                "notification_level": "low",
                "voice_sensitivity": "medium",
                "briefing_freq": "none",
            }
        else:
            return {
                "notification_level": "medium",
                "voice_sensitivity": "medium",
                "briefing_freq": "daily",
            }

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_mode_changes = c.execute(
                "SELECT COUNT(*) FROM mode_history"
            ).fetchone()[0]
            mode_breakdown_rows = c.execute(
                "SELECT mode, COUNT(*) FROM mode_history GROUP BY mode"
            ).fetchall()
        mode_breakdown = {r[0]: r[1] for r in mode_breakdown_rows}
        return {
            "current_mode": self._current_mode,
            "total_mode_changes": total_mode_changes,
            "mode_breakdown": mode_breakdown,
            "focus_active": self._focus_state.get("enabled", False),
            "calendar_status": self._calendar_status.get("status", "free"),
        }


_instance: Optional[PresenceEngine] = None


def get_presence_engine() -> PresenceEngine:
    global _instance
    if _instance is None:
        _instance = PresenceEngine()
    return _instance
