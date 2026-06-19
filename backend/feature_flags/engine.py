"""
Feature flag engine with channel-based rollout.
SQLite persistence at ~/.helios/feature_flags.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "feature_flags.db"

CHANNELS = ("stable", "beta", "experimental", "development")


class FeatureFlagEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS flag (
                key TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                enabled INTEGER,
                rollout TEXT,
                roles_json TEXT,
                workspaces_json TEXT,
                kill_switch INTEGER,
                created_at REAL,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS flag_event (
                id TEXT PRIMARY KEY,
                key TEXT,
                enabled INTEGER,
                context_json TEXT,
                created_at REAL
            );
            """)

    def create_flag(self, key: str, name: str, description: str = "",
                    enabled: bool = False, rollout: str = "stable",
                    roles=None, workspaces=None) -> dict:
        now = time.time()
        roles = roles or []
        workspaces = workspaces or []
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT OR REPLACE INTO flag VALUES (?,?,?,?,?,?,?,?,?,?)",
                (key, name, description, 1 if enabled else 0, rollout,
                 json.dumps(roles), json.dumps(workspaces), 0, now, now)
            )
        return self.get_flag(key)

    def get_flag(self, key: str):
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM flag WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        cols = ["key", "name", "description", "enabled", "rollout",
                "roles_json", "workspaces_json", "kill_switch",
                "created_at", "updated_at"]
        d = dict(zip(cols, row))
        d["enabled"] = bool(d["enabled"])
        d["kill_switch"] = bool(d["kill_switch"])
        try:
            d["roles"] = json.loads(d.pop("roles_json") or "[]")
        except Exception:
            d.pop("roles_json", None)
            d["roles"] = []
        try:
            d["workspaces"] = json.loads(d.pop("workspaces_json") or "[]")
        except Exception:
            d.pop("workspaces_json", None)
            d["workspaces"] = []
        return d

    def list_flags(self) -> list:
        with sqlite3.connect(self._db) as c:
            keys = [r[0] for r in c.execute("SELECT key FROM flag").fetchall()]
        return [self.get_flag(k) for k in keys]

    def enable(self, key: str):
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET enabled=1, updated_at=? WHERE key=?",
                (time.time(), key)
            )
        return self.get_flag(key)

    def disable(self, key: str):
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET enabled=0, updated_at=? WHERE key=?",
                (time.time(), key)
            )
        return self.get_flag(key)

    def set_rollout(self, key: str, channel: str):
        if channel not in CHANNELS:
            raise ValueError(f"Unknown channel: {channel}")
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET rollout=?, updated_at=? WHERE key=?",
                (channel, time.time(), key)
            )
        return self.get_flag(key)

    def set_roles(self, key: str, roles):
        roles = roles or []
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET roles_json=?, updated_at=? WHERE key=?",
                (json.dumps(roles), time.time(), key)
            )
        return self.get_flag(key)

    def set_workspaces(self, key: str, workspaces):
        workspaces = workspaces or []
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET workspaces_json=?, updated_at=? WHERE key=?",
                (json.dumps(workspaces), time.time(), key)
            )
        return self.get_flag(key)

    def kill(self, key: str):
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET kill_switch=1, updated_at=? WHERE key=?",
                (time.time(), key)
            )
        return self.get_flag(key)

    def revive(self, key: str):
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE flag SET kill_switch=0, updated_at=? WHERE key=?",
                (time.time(), key)
            )
        return self.get_flag(key)

    def is_enabled(self, key: str, role=None, workspace=None,
                   channel: str = "stable") -> bool:
        flag = self.get_flag(key)
        if flag is None:
            return False
        if flag["kill_switch"]:
            return False
        if not flag["enabled"]:
            return False
        if flag["roles"] and role not in flag["roles"]:
            return False
        if flag["workspaces"] and workspace not in flag["workspaces"]:
            return False
        req_channel = channel if channel in CHANNELS else "stable"
        req_idx = CHANNELS.index(req_channel)
        try:
            rollout_idx = CHANNELS.index(flag["rollout"])
        except ValueError:
            rollout_idx = 0
        result = req_idx >= rollout_idx
        self.record_evaluation(
            key, result,
            {"role": role, "workspace": workspace, "channel": channel}
        )
        return result

    def record_evaluation(self, key: str, enabled: bool, context=None):
        eid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO flag_event VALUES (?,?,?,?,?)",
                (eid, key, 1 if enabled else 0,
                 json.dumps(context or {}), time.time())
            )

    def analytics(self, key: str) -> dict:
        with sqlite3.connect(self._db) as c:
            evaluations = c.execute(
                "SELECT COUNT(*) FROM flag_event WHERE key=?", (key,)
            ).fetchone()[0]
            enabled_count = c.execute(
                "SELECT COUNT(*) FROM flag_event WHERE key=? AND enabled=1", (key,)
            ).fetchone()[0]
            disabled_count = c.execute(
                "SELECT COUNT(*) FROM flag_event WHERE key=? AND enabled=0", (key,)
            ).fetchone()[0]
        return {
            "key": key,
            "evaluations": evaluations,
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
        }

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_flags = c.execute("SELECT COUNT(*) FROM flag").fetchone()[0]
            enabled_flags = c.execute(
                "SELECT COUNT(*) FROM flag WHERE enabled=1"
            ).fetchone()[0]
            killed_flags = c.execute(
                "SELECT COUNT(*) FROM flag WHERE kill_switch=1"
            ).fetchone()[0]
            rollout_rows = c.execute(
                "SELECT rollout, COUNT(*) FROM flag GROUP BY rollout"
            ).fetchall()
            total_evaluations = c.execute(
                "SELECT COUNT(*) FROM flag_event"
            ).fetchone()[0]
        by_rollout = {r[0]: r[1] for r in rollout_rows}
        return {
            "total_flags": total_flags,
            "enabled_flags": enabled_flags,
            "killed_flags": killed_flags,
            "by_rollout": by_rollout,
            "total_evaluations": total_evaluations,
        }


_instance: Optional[FeatureFlagEngine] = None


def get_feature_flags() -> FeatureFlagEngine:
    global _instance
    if _instance is None:
        _instance = FeatureFlagEngine()
    return _instance
