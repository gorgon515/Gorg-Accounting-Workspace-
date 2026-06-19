"""
Base class for all HELIOS workforce agents.
Agents are autonomous research units with dedicated tools, memory, and performance tracking.
High-impact actions require human approval — agents propose, humans decide.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

_DB = Path(".data/agents.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_run (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            trigger TEXT DEFAULT 'manual',
            inputs TEXT DEFAULT '{}',
            outputs TEXT DEFAULT '{}',
            findings TEXT DEFAULT '[]',
            actions_proposed TEXT DEFAULT '[]',
            error TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_memory (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(agent_id, key)
        );

        CREATE TABLE IF NOT EXISTS proposed_action (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            run_id TEXT,
            action_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            payload TEXT DEFAULT '{}',
            requires_approval INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            approved_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );
    """)
    return conn


class AgentResult:
    def __init__(self, agent_id: str, findings: list[dict], proposed_actions: list[dict],
                 summary: str = "", error: str | None = None):
        self.agent_id = agent_id
        self.findings = findings
        self.proposed_actions = proposed_actions
        self.summary = summary
        self.error = error

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "findings": self.findings,
            "proposed_actions": self.proposed_actions,
            "summary": self.summary,
            "error": self.error,
        }


class BaseAgent(ABC):
    agent_id: str = ""
    agent_name: str = ""
    domain: str = ""
    description: str = ""

    # Actions this agent can propose (never execute autonomously)
    # "signal" = informational, "advisory" = client advisory, "alert" = risk alert
    # All "high_impact" types require human approval
    allowed_action_types: list[str] = ["signal", "advisory", "alert"]

    def __init__(self):
        _conn().close()

    def run(self, trigger: str = "manual", inputs: dict | None = None) -> AgentResult:
        run_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO agent_run(id, agent_id, status, trigger, inputs)
               VALUES(?,?,?,?,?)""",
            (run_id, self.agent_id, "running", trigger, json.dumps(inputs or {})),
        )
        conn.commit()
        conn.close()

        try:
            result = self._execute(inputs or {})
            self._save_run(run_id, "completed", result)
            for action in result.proposed_actions:
                self._propose_action(
                    run_id=run_id,
                    action_type=action.get("type", "alert"),
                    title=action.get("title", ""),
                    description=action.get("description", ""),
                    payload=action.get("payload", {}),
                    requires_approval=action.get("requires_approval", True),
                )
            return result
        except Exception as exc:
            error_result = AgentResult(
                agent_id=self.agent_id,
                findings=[],
                proposed_actions=[],
                error=str(exc),
            )
            self._save_run(run_id, "error", error_result)
            return error_result

    @abstractmethod
    def _execute(self, inputs: dict) -> AgentResult:
        """Core agent logic. Must return AgentResult."""

    def _save_run(self, run_id: str, status: str, result: AgentResult):
        conn = _conn()
        conn.execute(
            """UPDATE agent_run SET status=?, outputs=?, findings=?, actions_proposed=?,
               error=?, completed_at=datetime('now') WHERE id=?""",
            (status, json.dumps(result.to_dict()),
             json.dumps(result.findings), json.dumps(result.proposed_actions),
             result.error, run_id),
        )
        conn.commit()
        conn.close()

    def _propose_action(self, run_id: str, action_type: str, title: str,
                        description: str, payload: dict,
                        requires_approval: bool = True):
        action_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO proposed_action
               (id, agent_id, run_id, action_type, title, description, payload, requires_approval)
               VALUES(?,?,?,?,?,?,?,?)""",
            (action_id, self.agent_id, run_id, action_type, title, description,
             json.dumps(payload), 1 if requires_approval else 0),
        )
        conn.commit()
        conn.close()

    def remember(self, key: str, value):
        conn = _conn()
        conn.execute(
            """INSERT INTO agent_memory(id, agent_id, key, value, updated_at)
               VALUES(?,?,?,?,datetime('now'))
               ON CONFLICT(agent_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (str(uuid.uuid4()), self.agent_id, key, json.dumps(value)),
        )
        conn.commit()
        conn.close()

    def recall(self, key: str, default=None):
        conn = _conn()
        row = conn.execute(
            "SELECT value FROM agent_memory WHERE agent_id=? AND key=?",
            (self.agent_id, key),
        ).fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row["value"])
            except Exception:
                return row["value"]
        return default

    def list_runs(self, limit: int = 20) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM agent_run WHERE agent_id=? ORDER BY started_at DESC LIMIT ?",
            (self.agent_id, limit),
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            for f in ("inputs", "outputs", "findings", "actions_proposed"):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = {}
            result.append(d)
        return result

    def list_proposed_actions(self, status: str = "pending") -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM proposed_action WHERE agent_id=? AND status=? ORDER BY created_at DESC",
            (self.agent_id, status),
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                d["payload"] = {}
            result.append(d)
        return result


def approve_action(action_id: str, approved_by: str = "user") -> Optional[dict]:
    conn = _conn()
    conn.execute(
        """UPDATE proposed_action SET status='approved', approved_by=?, resolved_at=datetime('now')
           WHERE id=?""",
        (approved_by, action_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM proposed_action WHERE id=?", (action_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def reject_action(action_id: str, reason: str = "") -> Optional[dict]:
    conn = _conn()
    conn.execute(
        """UPDATE proposed_action SET status='rejected', resolved_at=datetime('now') WHERE id=?""",
        (action_id,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM proposed_action WHERE id=?", (action_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_pending_approvals(limit: int = 50) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM proposed_action WHERE status='pending' AND requires_approval=1 ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["payload"] = json.loads(d["payload"])
        except Exception:
            d["payload"] = {}
        result.append(d)
    return result


def agent_stats() -> dict:
    conn = _conn()
    runs = conn.execute("SELECT COUNT(*) FROM agent_run WHERE status='completed'").fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM agent_run WHERE status='error'").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM proposed_action WHERE status='pending' AND requires_approval=1"
    ).fetchone()[0]
    approved = conn.execute(
        "SELECT COUNT(*) FROM proposed_action WHERE status='approved'"
    ).fetchone()[0]
    conn.close()
    return {
        "completed_runs": runs,
        "error_runs": errors,
        "pending_approvals": pending,
        "approved_actions": approved,
    }
