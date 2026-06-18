"""
Institutional Memory: store decisions, recommendations, approvals, outcomes, history.
Who / what / when / why / result / confidence.
"""
from __future__ import annotations
import json
import uuid
from typing import Optional
from .db import get_connection, init_schema

_EVENT_TYPES = [
    "decision", "recommendation", "approval", "rejection", "outcome",
    "lesson_learned", "milestone", "policy_change", "observation",
]


class InstitutionalMemory:
    def __init__(self):
        init_schema()

    def record(
        self,
        event_type: str,
        title: str,
        description: str = "",
        decision: str = "",
        rationale: str = "",
        outcome: str = "",
        confidence: float = 1.0,
        who: str = "",
        domain: str = "general",
        tags: Optional[list] = None,
    ) -> dict:
        mem_id = str(uuid.uuid4())
        conn = get_connection()
        conn.execute(
            """INSERT INTO institutional_memory
               (id, event_type, title, description, decision, rationale,
                outcome, confidence, who, domain, tags)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (mem_id, event_type, title, description, decision, rationale,
             outcome, confidence, who, domain, json.dumps(tags or [])),
        )
        conn.commit()
        conn.close()
        return self.get(mem_id)

    def get(self, mem_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM institutional_memory WHERE id=?", (mem_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return self._fmt(row)

    def _fmt(self, row) -> dict:
        d = dict(row)
        try:
            d["tags"] = json.loads(d.get("tags", "[]"))
        except Exception:
            d["tags"] = []
        return d

    def list(
        self,
        event_type: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        conn = get_connection()
        clauses = []
        params: list = []
        if event_type:
            clauses.append("event_type=?")
            params.append(event_type)
        if domain:
            clauses.append("domain=?")
            params.append(domain)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM institutional_memory {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def update_outcome(self, mem_id: str, outcome: str, confidence: float) -> Optional[dict]:
        conn = get_connection()
        conn.execute(
            "UPDATE institutional_memory SET outcome=?, confidence=?, updated_at=datetime('now') WHERE id=?",
            (outcome, confidence, mem_id),
        )
        conn.commit()
        conn.close()
        return self.get(mem_id)

    def search_by_keyword(self, keyword: str, limit: int = 20) -> list[dict]:
        conn = get_connection()
        kw = f"%{keyword}%"
        rows = conn.execute(
            """SELECT * FROM institutional_memory
               WHERE title LIKE ? OR description LIKE ? OR decision LIKE ? OR outcome LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (kw, kw, kw, kw, limit),
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def stats(self) -> dict:
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) FROM institutional_memory").fetchone()[0]
        by_type = {}
        for row in conn.execute(
            "SELECT event_type, COUNT(*) as cnt FROM institutional_memory GROUP BY event_type"
        ).fetchall():
            by_type[row[0]] = row[1]
        by_domain = {}
        for row in conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM institutional_memory GROUP BY domain"
        ).fetchall():
            by_domain[row[0]] = row[1]
        avg_conf = conn.execute("SELECT AVG(confidence) FROM institutional_memory").fetchone()[0] or 0
        conn.close()
        return {
            "total_events": total,
            "by_type": by_type,
            "by_domain": by_domain,
            "avg_confidence": round(avg_conf, 3),
        }


_instance: Optional["InstitutionalMemory"] = None


def get_institutional_memory() -> "InstitutionalMemory":
    global _instance
    if _instance is None:
        _instance = InstitutionalMemory()
    return _instance
