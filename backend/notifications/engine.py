"""
Notification engine with priority scoring, batching, quiet hours, focus mode, escalation.
SQLite persistence at ~/.helios/notifications.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "notifications.db"

PRIORITY_LEVELS = ("low", "medium", "high", "urgent", "critical")
CATEGORIES = ("market", "portfolio", "accounting", "tax", "research", "system",
              "approval", "calendar", "email", "voice", "general")
CHANNELS = ("desktop", "voice", "mobile", "email")

_PRIORITY_SCORES = {
    "critical": 1.0,
    "urgent": 0.85,
    "high": 0.7,
    "medium": 0.5,
    "low": 0.25,
}


class NotificationEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._quiet_hours = {"start_hour": 22, "end_hour": 7, "enabled": True}
        self._focus_mode = {"enabled": False, "ends_at": None}

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS notification (
                id TEXT PRIMARY KEY,
                title TEXT,
                body TEXT,
                priority TEXT DEFAULT 'medium',
                score REAL DEFAULT 0.5,
                category TEXT DEFAULT 'general',
                channel TEXT DEFAULT 'desktop',
                source TEXT,
                action_url TEXT,
                metadata_json TEXT DEFAULT '{}',
                status TEXT DEFAULT 'unread',
                created_at REAL,
                read_at REAL
            );
            """)

    def _score_priority(self, priority: str, category: str) -> float:
        base = _PRIORITY_SCORES.get(priority, 0.5)
        # Boost score for market/portfolio/approval categories
        category_boost = {
            "market": 0.05, "portfolio": 0.05, "approval": 0.1,
            "tax": 0.03, "accounting": 0.03,
        }
        boost = category_boost.get(category, 0.0)
        return min(1.0, base + boost)

    def send(self, title: str, body: str = "", priority: str = "medium",
             category: str = "general", channel: str = "desktop",
             source: str = "", action_url: str = "", metadata: dict = None) -> dict:
        if priority not in PRIORITY_LEVELS:
            priority = "medium"
        if category not in CATEGORIES:
            category = "general"
        if channel not in CHANNELS:
            channel = "desktop"
        nid = str(uuid.uuid4())
        now = time.time()
        score = self._score_priority(priority, category)
        metadata = metadata or {}
        with sqlite3.connect(self._db) as c:
            c.execute(
                """INSERT INTO notification
                   (id, title, body, priority, score, category, channel, source,
                    action_url, metadata_json, status, created_at, read_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                (nid, title, body, priority, score, category, channel, source,
                 action_url or "", json.dumps(metadata), "unread", now)
            )
        return {"id": nid, "title": title, "body": body, "priority": priority,
                "score": score, "category": category, "channel": channel,
                "source": source, "status": "unread", "created_at": now}

    def list(self, status: str = "", priority: str = "", limit: int = 50) -> list:
        query = "SELECT * FROM notification WHERE 1=1"
        params = []
        if status:
            query += " AND status=?"
            params.append(status)
        if priority:
            query += " AND priority=?"
            params.append(priority)
        query += " ORDER BY score DESC, created_at DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self._db) as c:
            rows = c.execute(query, params).fetchall()
        cols = ["id", "title", "body", "priority", "score", "category", "channel",
                "source", "action_url", "metadata_json", "status", "created_at", "read_at"]
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            try:
                d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            result.append(d)
        return result

    def mark_read(self, nid: str) -> bool:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE notification SET status='read', read_at=? WHERE id=? AND status='unread'",
                (now, nid)
            ).rowcount
        return bool(n)

    def mark_all_read(self) -> int:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE notification SET status='read', read_at=? WHERE status='unread'",
                (now,)
            ).rowcount
        return n

    def dismiss(self, nid: str) -> bool:
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE notification SET status='dismissed' WHERE id=?",
                (nid,)
            ).rowcount
        return bool(n)

    def set_quiet_hours(self, start_hour: int, end_hour: int, enabled: bool = True) -> dict:
        self._quiet_hours = {"start_hour": start_hour, "end_hour": end_hour, "enabled": enabled}
        return self._quiet_hours.copy()

    def get_quiet_hours(self) -> dict:
        return self._quiet_hours.copy()

    def set_focus_mode(self, enabled: bool, duration_minutes: int = 0) -> dict:
        ends_at = None
        if enabled and duration_minutes > 0:
            ends_at = time.time() + duration_minutes * 60
        self._focus_mode = {"enabled": enabled, "ends_at": ends_at}
        return self._focus_mode.copy()

    def get_focus_mode(self) -> dict:
        return self._focus_mode.copy()

    def is_quiet(self) -> bool:
        """Check if quiet hours or focus mode is active."""
        # Focus mode check
        if self._focus_mode.get("enabled"):
            ends_at = self._focus_mode.get("ends_at")
            if ends_at is None or time.time() < ends_at:
                return True
        # Quiet hours check
        if self._quiet_hours.get("enabled"):
            current_hour = datetime.now().hour
            start = self._quiet_hours.get("start_hour", 22)
            end = self._quiet_hours.get("end_hour", 7)
            if start > end:
                # Spans midnight: quiet if hour >= start OR hour < end
                if current_hour >= start or current_hour < end:
                    return True
            else:
                if start <= current_hour < end:
                    return True
        return False

    def batch_pending(self) -> list:
        """Group unread notifications by category."""
        notifications = self.list(status="unread", limit=200)
        groups: dict = {}
        for n in notifications:
            cat = n.get("category", "general")
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(n)
        return [{"category": k, "count": len(v), "notifications": v}
                for k, v in groups.items()]

    def escalate(self, nid: str, new_priority: str) -> dict:
        if new_priority not in PRIORITY_LEVELS:
            raise ValueError(f"Unknown priority: {new_priority}")
        new_score = _PRIORITY_SCORES.get(new_priority, 0.5)
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE notification SET priority=?, score=? WHERE id=?",
                (new_priority, new_score, nid)
            )
            row = c.execute("SELECT * FROM notification WHERE id=?", (nid,)).fetchone()
        if not row:
            return {"error": "Notification not found"}
        cols = ["id", "title", "body", "priority", "score", "category", "channel",
                "source", "action_url", "metadata_json", "status", "created_at", "read_at"]
        d = dict(zip(cols, row))
        try:
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        return d

    def channels(self) -> list:
        return list(CHANNELS)

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM notification").fetchone()[0]
            unread = c.execute(
                "SELECT COUNT(*) FROM notification WHERE status='unread'"
            ).fetchone()[0]
            by_priority_rows = c.execute(
                "SELECT priority, COUNT(*) FROM notification GROUP BY priority"
            ).fetchall()
            by_category_rows = c.execute(
                "SELECT category, COUNT(*) FROM notification GROUP BY category"
            ).fetchall()
        by_priority = {r[0]: r[1] for r in by_priority_rows}
        by_category = {r[0]: r[1] for r in by_category_rows}
        return {
            "total": total,
            "unread": unread,
            "by_priority": by_priority,
            "by_category": by_category,
            "is_quiet": self.is_quiet(),
            "focus_mode": self._focus_mode.copy(),
        }


_instance: Optional[NotificationEngine] = None


def get_notification_engine() -> NotificationEngine:
    global _instance
    if _instance is None:
        _instance = NotificationEngine()
    return _instance
