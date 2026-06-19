"""
Release channel assignment and version pinning engine.
SQLite persistence at ~/.helios/release_channels.db.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "release_channels.db"

CHANNEL_META = {
    "stable": {"name": "stable", "index": 0,
               "description": "Production-tested, fully stable"},
    "beta": {"name": "beta", "index": 1,
             "description": "Pre-release, mostly stable"},
    "experimental": {"name": "experimental", "index": 2,
                     "description": "Cutting-edge, may be unstable"},
    "development": {"name": "development", "index": 3,
                    "description": "Nightly dev builds"},
}


class ReleaseChannelEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS assignment (
                target_type TEXT,
                target_id TEXT,
                channel TEXT,
                updated_at REAL,
                PRIMARY KEY (target_type, target_id)
            );
            CREATE TABLE IF NOT EXISTS version_pin (
                target_type TEXT,
                target_id TEXT,
                version TEXT,
                pinned_at REAL,
                PRIMARY KEY (target_type, target_id)
            );
            """)

    def list_channels(self) -> list:
        return [
            {"name": m["name"], "index": m["index"], "description": m["description"]}
            for m in sorted(CHANNEL_META.values(), key=lambda x: x["index"])
        ]

    def get_channel(self, name: str) -> dict:
        if name not in CHANNEL_META:
            raise ValueError(f"Unknown channel: {name}")
        m = CHANNEL_META[name]
        return {"name": m["name"], "index": m["index"], "description": m["description"]}

    def set_channel(self, target_type: str, target_id: str, channel: str) -> dict:
        if channel not in CHANNEL_META:
            raise ValueError(f"Unknown channel: {channel}")
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT OR REPLACE INTO assignment VALUES (?,?,?,?)",
                (target_type, target_id, channel, time.time())
            )
        return {"target_type": target_type, "target_id": target_id, "channel": channel}

    def get_assigned_channel(self, target_type: str, target_id: str) -> str:
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT channel FROM assignment WHERE target_type=? AND target_id=?",
                (target_type, target_id)
            ).fetchone()
        return row[0] if row else "stable"

    def set_user_channel(self, user_id: str, channel: str) -> dict:
        return self.set_channel("user", user_id, channel)

    def get_user_channel(self, user_id: str) -> str:
        return self.get_assigned_channel("user", user_id)

    def set_workspace_channel(self, ws_id: str, channel: str) -> dict:
        return self.set_channel("workspace", ws_id, channel)

    def get_workspace_channel(self, ws_id: str) -> str:
        return self.get_assigned_channel("workspace", ws_id)

    def pin_version(self, target_type: str, target_id: str, version: str) -> dict:
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT OR REPLACE INTO version_pin VALUES (?,?,?,?)",
                (target_type, target_id, version, time.time())
            )
        return {"target_type": target_type, "target_id": target_id, "version": version}

    def get_pin(self, target_type: str, target_id: str):
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT target_type, target_id, version, pinned_at "
                "FROM version_pin WHERE target_type=? AND target_id=?",
                (target_type, target_id)
            ).fetchone()
        if row is None:
            return None
        cols = ["target_type", "target_id", "version", "pinned_at"]
        return dict(zip(cols, row))

    def rollback(self, target_type: str, target_id: str) -> dict:
        with sqlite3.connect(self._db) as c:
            c.execute(
                "DELETE FROM version_pin WHERE target_type=? AND target_id=?",
                (target_type, target_id)
            )
        return {"target_type": target_type, "target_id": target_id, "rolled_back": True}

    def channel_allows(self, channel: str, feature_stability: str) -> bool:
        if channel not in CHANNEL_META:
            raise ValueError(f"Unknown channel: {channel}")
        if feature_stability not in CHANNEL_META:
            raise ValueError(f"Unknown feature stability: {feature_stability}")
        return CHANNEL_META[channel]["index"] >= CHANNEL_META[feature_stability]["index"]

    def list_assignments(self) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT target_type, target_id, channel, updated_at FROM assignment"
            ).fetchall()
        cols = ["target_type", "target_id", "channel", "updated_at"]
        return [dict(zip(cols, r)) for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_assignments = c.execute(
                "SELECT COUNT(*) FROM assignment"
            ).fetchone()[0]
            total_pins = c.execute("SELECT COUNT(*) FROM version_pin").fetchone()[0]
            channel_rows = c.execute(
                "SELECT channel, COUNT(*) FROM assignment GROUP BY channel"
            ).fetchall()
        by_channel = {r[0]: r[1] for r in channel_rows}
        return {
            "channels": 4,
            "total_assignments": total_assignments,
            "total_pins": total_pins,
            "by_channel": by_channel,
        }


_instance: Optional[ReleaseChannelEngine] = None


def get_release_channels() -> ReleaseChannelEngine:
    global _instance
    if _instance is None:
        _instance = ReleaseChannelEngine()
    return _instance
