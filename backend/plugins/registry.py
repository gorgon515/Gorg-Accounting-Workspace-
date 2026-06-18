"""PluginRegistry — persistent record of installed plugins and lifecycle audit."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .manifest import PluginManifest

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
DB_PATH = os.path.join(BASE_DIR, "plugins.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "plugin"


def get_connection(path: Optional[str] = None) -> sqlite3.Connection:
    p = path or DB_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS plugin (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
            description TEXT, author TEXT, entry_point TEXT,
            permissions TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'disabled',
            installed_at TEXT NOT NULL, enabled_at TEXT, disabled_at TEXT,
            tags TEXT DEFAULT '[]', manifest_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plugin_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT,
            detail TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plugin_call_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_id TEXT NOT NULL, function_name TEXT NOT NULL,
            allowed INTEGER NOT NULL, args_summary TEXT, blocked_reason TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


class PluginRegistry:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def register(self, manifest: PluginManifest, actor: Optional[str] = None) -> dict:
        plugin_id = _slug(manifest.name)
        conn = self._conn()
        try:
            ts = _now()
            conn.execute(
                "INSERT OR REPLACE INTO plugin (id, name, version, description, author, entry_point, "
                "permissions, status, installed_at, tags, manifest_json) "
                "VALUES (?,?,?,?,?,?,?, 'installed', ?, ?, ?)",
                (plugin_id, manifest.name, manifest.version, manifest.description, manifest.author,
                 manifest.entry_point, json.dumps(manifest.permissions), ts,
                 json.dumps(manifest.tags), json.dumps(manifest.to_dict())),
            )
            conn.execute(
                "INSERT INTO plugin_audit (plugin_id, action, actor, detail, created_at) "
                "VALUES (?, 'install', ?, ?, ?)",
                (plugin_id, actor, f"v{manifest.version}", ts),
            )
            conn.commit()
            return self.get(plugin_id)
        finally:
            conn.close()

    def get(self, plugin_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM plugin WHERE id=?", (plugin_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def list(self, status: Optional[str] = None) -> list[dict]:
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM plugin WHERE status=? ORDER BY installed_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM plugin ORDER BY installed_at DESC").fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def set_status(self, plugin_id: str, status: str, actor: Optional[str] = None) -> bool:
        col = {"enabled": "enabled_at", "disabled": "disabled_at"}.get(status)
        conn = self._conn()
        try:
            ts = _now()
            if col:
                conn.execute(
                    f"UPDATE plugin SET status=?, {col}=? WHERE id=?", (status, ts, plugin_id)
                )
            else:
                conn.execute("UPDATE plugin SET status=? WHERE id=?", (status, plugin_id))
            cur = conn.execute(
                "INSERT INTO plugin_audit (plugin_id, action, actor, detail, created_at) "
                "VALUES (?,?,?,?,?)",
                (plugin_id, status, actor, "", ts),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def unregister(self, plugin_id: str, actor: Optional[str] = None) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("DELETE FROM plugin WHERE id=?", (plugin_id,))
            conn.execute(
                "INSERT INTO plugin_audit (plugin_id, action, actor, detail, created_at) "
                "VALUES (?, 'uninstall', ?, '', ?)",
                (plugin_id, actor, _now()),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_audit(self, plugin_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = self._conn()
        try:
            if plugin_id:
                rows = conn.execute(
                    "SELECT * FROM plugin_audit WHERE plugin_id=? ORDER BY created_at DESC LIMIT ?",
                    (plugin_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM plugin_audit ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        d["permissions"] = json.loads(d["permissions"])
        d["tags"] = json.loads(d["tags"])
        try:
            d["manifest"] = json.loads(d["manifest_json"])
        except Exception:
            d["manifest"] = {}
        return d


_instance: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    global _instance
    if _instance is None:
        _instance = PluginRegistry()
    return _instance
