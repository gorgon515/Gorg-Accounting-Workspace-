from __future__ import annotations

"""Agent security model for HELIOS."""

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .roles import RolePermissions

AGENT_PERMISSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_permission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL DEFAULT 'viewer',
  allowed_tools TEXT NOT NULL DEFAULT '[]',
  denied_tools TEXT NOT NULL DEFAULT '[]',
  memory_scope TEXT NOT NULL DEFAULT 'own',
  document_scope TEXT NOT NULL DEFAULT 'read',
  execution_scope TEXT NOT NULL DEFAULT 'none',
  max_concurrent_tasks INTEGER NOT NULL DEFAULT 1,
  can_approve INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentPermission:
    agent_name: str
    role: str = "viewer"
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    memory_scope: str = "own"       # own | team | all
    document_scope: str = "read"    # none | read | write
    execution_scope: str = "none"   # none | request | execute
    max_concurrent_tasks: int = 1
    can_approve: bool = False


MEMORY_SCOPE_LEVELS = {"own": 0, "team": 1, "all": 2}
EXECUTION_SCOPE_LEVELS = {"none": 0, "request": 1, "execute": 2}
DOCUMENT_SCOPE_LEVELS = {"none": 0, "read": 1, "write": 2}


class AgentPermissionRegistry:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or os.environ.get("HELIOS_AGENT_PERMISSIONS_DB") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".data", "agent_permissions.db",
        )
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(AGENT_PERMISSIONS_SCHEMA)
        conn.commit()

    def _row_to_dict(self, row) -> dict:
        d = dict(row)
        d["allowed_tools"] = json.loads(d["allowed_tools"])
        d["denied_tools"] = json.loads(d["denied_tools"])
        d["can_approve"] = bool(d["can_approve"])
        return d

    def register(self, agent_name: str, role: str = "viewer", **kwargs) -> dict:
        now = _now()
        allowed_tools = json.dumps(kwargs.get("allowed_tools", []))
        denied_tools = json.dumps(kwargs.get("denied_tools", []))
        memory_scope = kwargs.get("memory_scope", "own")
        document_scope = kwargs.get("document_scope", "read")
        execution_scope = kwargs.get("execution_scope", "none")
        max_concurrent_tasks = kwargs.get("max_concurrent_tasks", 1)
        can_approve = int(kwargs.get("can_approve", False))
        with self._lock:
            self._get_conn().execute(
                "INSERT OR REPLACE INTO agent_permission "
                "(agent_name,role,allowed_tools,denied_tools,memory_scope,document_scope,execution_scope,"
                "max_concurrent_tasks,can_approve,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (agent_name, role, allowed_tools, denied_tools, memory_scope, document_scope,
                 execution_scope, max_concurrent_tasks, can_approve, now, now),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute(
                "SELECT * FROM agent_permission WHERE agent_name=?", (agent_name,)
            ).fetchone()
        )

    def update(self, agent_name: str, **kwargs) -> dict:
        row = self._get_conn().execute(
            "SELECT * FROM agent_permission WHERE agent_name=?", (agent_name,)
        ).fetchone()
        if not row:
            raise KeyError(f"Agent '{agent_name}' not registered.")
        current = self._row_to_dict(row)
        now = _now()
        updates = {
            "role": kwargs.get("role", current["role"]),
            "allowed_tools": json.dumps(kwargs.get("allowed_tools", current["allowed_tools"])),
            "denied_tools": json.dumps(kwargs.get("denied_tools", current["denied_tools"])),
            "memory_scope": kwargs.get("memory_scope", current["memory_scope"]),
            "document_scope": kwargs.get("document_scope", current["document_scope"]),
            "execution_scope": kwargs.get("execution_scope", current["execution_scope"]),
            "max_concurrent_tasks": kwargs.get("max_concurrent_tasks", current["max_concurrent_tasks"]),
            "can_approve": int(kwargs.get("can_approve", current["can_approve"])),
        }
        with self._lock:
            self._get_conn().execute(
                "UPDATE agent_permission SET role=?,allowed_tools=?,denied_tools=?,memory_scope=?,"
                "document_scope=?,execution_scope=?,max_concurrent_tasks=?,can_approve=?,updated_at=? "
                "WHERE agent_name=?",
                (updates["role"], updates["allowed_tools"], updates["denied_tools"],
                 updates["memory_scope"], updates["document_scope"], updates["execution_scope"],
                 updates["max_concurrent_tasks"], updates["can_approve"], now, agent_name),
            )
            self._get_conn().commit()
        return self._row_to_dict(
            self._get_conn().execute(
                "SELECT * FROM agent_permission WHERE agent_name=?", (agent_name,)
            ).fetchone()
        )

    def get(self, agent_name: str) -> AgentPermission:
        row = self._get_conn().execute(
            "SELECT * FROM agent_permission WHERE agent_name=?", (agent_name,)
        ).fetchone()
        if not row:
            raise KeyError(f"Agent '{agent_name}' not registered.")
        d = self._row_to_dict(row)
        return AgentPermission(
            agent_name=d["agent_name"],
            role=d["role"],
            allowed_tools=d["allowed_tools"],
            denied_tools=d["denied_tools"],
            memory_scope=d["memory_scope"],
            document_scope=d["document_scope"],
            execution_scope=d["execution_scope"],
            max_concurrent_tasks=d["max_concurrent_tasks"],
            can_approve=d["can_approve"],
        )

    def check_tool(self, agent_name: str, tool_name: str) -> bool:
        try:
            perm = self.get(agent_name)
        except KeyError:
            return False
        if tool_name in perm.denied_tools:
            return False
        if perm.allowed_tools and tool_name not in perm.allowed_tools:
            return False
        return True

    def check_memory(self, agent_name: str, scope_needed: str) -> bool:
        try:
            perm = self.get(agent_name)
        except KeyError:
            return False
        agent_level = MEMORY_SCOPE_LEVELS.get(perm.memory_scope, 0)
        needed_level = MEMORY_SCOPE_LEVELS.get(scope_needed, 0)
        return agent_level >= needed_level

    def check_execution(self, agent_name: str, scope_needed: str) -> bool:
        try:
            perm = self.get(agent_name)
        except KeyError:
            return False
        agent_level = EXECUTION_SCOPE_LEVELS.get(perm.execution_scope, 0)
        needed_level = EXECUTION_SCOPE_LEVELS.get(scope_needed, 0)
        return agent_level >= needed_level

    def list_agents(self) -> list[dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM agent_permission ORDER BY agent_name"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def audit_check(self, agent_name: str, resource: str, action: str) -> dict:
        try:
            perm = self.get(agent_name)
        except KeyError:
            return {
                "allowed": False,
                "denied": True,
                "reason": f"Agent '{agent_name}' not registered.",
            }
        category = resource.lower()
        role_allowed = RolePermissions.has_permission(perm.role, category, action)
        if not role_allowed:
            return {
                "allowed": False,
                "denied": True,
                "reason": f"Role '{perm.role}' does not have permission '{category}:{action}'",
            }
        return {
            "allowed": True,
            "denied": False,
            "reason": f"Role '{perm.role}' has permission '{category}:{action}'",
        }


_registry: Optional[AgentPermissionRegistry] = None


def get_agent_registry() -> AgentPermissionRegistry:
    global _registry
    if _registry is None:
        _registry = AgentPermissionRegistry()
    return _registry
