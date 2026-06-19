"""Approval + Execution engine.

Actions are proposed, approved/rejected by a human, executed, and (where possible)
rolled back or retried — every transition audited. The risk tier governs the path:
  • Tier 1 may auto-execute (propose(auto=True)).
  • Tier 2/3 require human approval before execute().
  • Tier 4 NEVER auto-executes and requires an explicit confirm to approve; even
    then the executor only prepares (no autonomous external action).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from . import registry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS action (
  id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, tier INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed', payload TEXT NOT NULL DEFAULT '{}',
  confidence REAL, affected TEXT NOT NULL DEFAULT '{}', result TEXT, error TEXT,
  proposed_by TEXT, approved_by TEXT, confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, decided_at TEXT, executed_at TEXT
);
CREATE TABLE IF NOT EXISTS action_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INTEGER, ts TEXT NOT NULL,
  event TEXT NOT NULL, actor TEXT, detail TEXT
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


class ExecutionEngine:
    def __init__(self, path: Optional[str] = None, context: Optional[dict] = None):
        self.path = path or os.environ.get("HELIOS_EXEC_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "execution.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.context = context or {}
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _audit(self, action_id, event, actor="system", detail=None):
        self.conn.execute("INSERT INTO action_audit (action_id,ts,event,actor,detail) VALUES (?,?,?,?,?)",
                          (action_id, _now(), event, actor, json.dumps(detail) if detail is not None else None))

    def _row(self, r) -> dict:
        d = dict(r)
        for k in ("payload", "affected", "result"):
            d[k] = json.loads(d[k]) if d.get(k) else ({} if k != "result" else None)
        d["audit"] = [dict(a) for a in self.conn.execute(
            "SELECT event,ts,actor,detail FROM action_audit WHERE action_id=? ORDER BY id", (r["id"],))]
        for a in d["audit"]:
            a["detail"] = json.loads(a["detail"]) if a["detail"] else None
        return d

    def get(self, action_id: int) -> Optional[dict]:
        r = self.conn.execute("SELECT * FROM action WHERE id=?", (action_id,)).fetchone()
        return self._row(r) if r else None

    def list(self, status: Optional[str] = None, tier: Optional[int] = None) -> list[dict]:
        sql, args = "SELECT * FROM action WHERE 1=1", []
        if status:
            sql += " AND status=?"; args.append(status)
        if tier:
            sql += " AND tier=?"; args.append(tier)
        sql += " ORDER BY id DESC"
        return [self._row(r) for r in self.conn.execute(sql, args)]

    def propose(self, action_type: str, payload: dict, *, confidence: Optional[float] = None,
                affected: Optional[dict] = None, proposed_by: str = "system", auto: bool = False) -> dict:
        tier = registry.tier_of(action_type)
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO action (type,tier,status,payload,confidence,affected,proposed_by,created_at) "
                "VALUES (?,?, 'proposed', ?,?,?,?,?)",
                (action_type, tier, json.dumps(payload), confidence, json.dumps(affected or {}),
                 proposed_by, _now()))
            aid = cur.lastrowid
            self._audit(aid, "proposed", proposed_by, {"tier": tier})
            self.conn.commit()
        # Tier 1 only may auto-execute when explicitly requested.
        if auto and tier == 1:
            self.approve(aid, approved_by="auto")
            return self.execute(aid)
        return self.get(aid)

    def approve(self, action_id: int, approved_by: str = "user", confirm: bool = False) -> dict:
        a = self.get(action_id)
        if not a:
            raise ValueError("no such action")
        if a["status"] not in ("proposed",):
            raise ValueError(f"cannot approve an action in status '{a['status']}'")
        if a["tier"] == 4 and not confirm:
            raise ValueError("Tier 4 (critical) action requires explicit confirm=True to approve; "
                             "HELIOS will only PREPARE it — a human must perform the external action.")
        with self._lock:
            self.conn.execute("UPDATE action SET status='approved', approved_by=?, confirmed=?, decided_at=? WHERE id=?",
                              (approved_by, 1 if confirm else 0, _now(), action_id))
            self._audit(action_id, "approved", approved_by, {"confirm": confirm})
            self.conn.commit()
        return self.get(action_id)

    def reject(self, action_id: int, reason: str = "", rejected_by: str = "user") -> dict:
        a = self.get(action_id)
        if not a:
            raise ValueError("no such action")
        with self._lock:
            self.conn.execute("UPDATE action SET status='rejected', approved_by=?, decided_at=? WHERE id=?",
                              (rejected_by, _now(), action_id))
            self._audit(action_id, "rejected", rejected_by, {"reason": reason})
            self.conn.commit()
        return self.get(action_id)

    def execute(self, action_id: int) -> dict:
        a = self.get(action_id)
        if not a:
            raise ValueError("no such action")
        if a["status"] != "approved":
            raise ValueError(f"action must be approved before execution (status: {a['status']})")
        if a["tier"] == 4 and not a["confirmed"]:
            raise ValueError("Tier 4 action not confirmed — refusing to execute")
        spec = registry.executor(a["type"])
        if not spec:
            raise ValueError(f"no executor for {a['type']}")
        try:
            result = spec["run"](a["payload"], self.context)
            with self._lock:
                self.conn.execute("UPDATE action SET status='executed', result=?, executed_at=? WHERE id=?",
                                  (json.dumps(result), _now(), action_id))
                self._audit(action_id, "executed", a.get("approved_by") or "system", {"result_keys": list(result)})
                self.conn.commit()
        except Exception as exc:  # noqa: BLE001 - record failure, never crash the queue
            with self._lock:
                self.conn.execute("UPDATE action SET status='failed', error=? WHERE id=?", (str(exc), action_id))
                self._audit(action_id, "failed", "system", {"error": str(exc)})
                self.conn.commit()
        return self.get(action_id)

    def rollback(self, action_id: int, actor: str = "user") -> dict:
        a = self.get(action_id)
        if not a or a["status"] != "executed":
            raise ValueError("only executed actions can be rolled back")
        spec = registry.executor(a["type"])
        if not spec or not spec.get("rollback"):
            raise ValueError(f"action type '{a['type']}' is not reversible")
        rb = spec["rollback"](a["payload"], a["result"], self.context)
        with self._lock:
            self.conn.execute("UPDATE action SET status='rolled_back' WHERE id=?", (action_id,))
            self._audit(action_id, "rolled_back", actor, rb)
            self.conn.commit()
        return self.get(action_id)

    def retry(self, action_id: int) -> dict:
        a = self.get(action_id)
        if not a or a["status"] != "failed":
            raise ValueError("only failed actions can be retried")
        with self._lock:
            self.conn.execute("UPDATE action SET status='approved', error=NULL WHERE id=?", (action_id,))
            self._audit(action_id, "retry", "user")
            self.conn.commit()
        return self.execute(action_id)

    def queue_summary(self) -> dict:
        rows = self.conn.execute("SELECT status, COUNT(*) n FROM action GROUP BY status")
        by_status = {r["status"]: r["n"] for r in rows}
        pending = self.list(status="proposed")
        return {"by_status": by_status,
                "pending_approval": [{"id": a["id"], "type": a["type"], "tier": a["tier"],
                                      "tier_label": registry.TIER_LABEL[a["tier"]],
                                      "confidence": a["confidence"], "affected": a["affected"]} for a in pending]}

    def close(self):
        self.conn.close()
