"""OpportunityEngine — scans domains and scores actionable opportunities.

Score = expected_impact * confidence / (1 + required_effort), normalized to 0..100.
This rewards high-impact, high-confidence, low-effort opportunities.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from .db import get_connection, now


def _score(impact: float, effort: float, confidence: float) -> float:
    raw = (impact * confidence) / (1.0 + effort)
    return round(min(max(raw, 0.0), 1.0) * 100, 1)


class OpportunityEngine:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def _persist(self, domain, title, description, impact, effort, confidence, evidence) -> dict:
        opp_id = "opp_" + uuid.uuid4().hex[:12]
        score = _score(impact, effort, confidence)
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO opportunity (id, domain, title, description, score, expected_impact, "
                "required_effort, confidence, evidence, status, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?, 'open', ?)",
                (opp_id, domain, title, description, score, impact, effort, confidence,
                 json.dumps(evidence), now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": opp_id, "domain": domain, "title": title, "description": description,
                "score": score, "expected_impact": impact, "required_effort": effort,
                "confidence": confidence, "evidence": evidence, "status": "open"}

    def scan(self) -> list[dict]:
        """Run all detectors against current data and persist fresh opportunities."""
        from .sources import accounting_snapshot, goals_snapshot, tasks_snapshot
        # Clear prior open scan results so the list reflects the latest snapshot.
        conn = self._conn()
        try:
            conn.execute("DELETE FROM opportunity WHERE status='open'")
            conn.commit()
        finally:
            conn.close()

        acct = accounting_snapshot()
        goals = goals_snapshot()
        tasks = tasks_snapshot()
        found = []

        # Tax savings: positive net income → estimated quarterly tax planning headroom.
        if acct["net"] > 0:
            est_savings = acct["net"] * 0.07
            found.append(self._persist(
                "tax", "Proactive tax planning",
                f"Net income of ${acct['net']:.0f} suggests ~${est_savings:.0f} in planning headroom "
                "via entity structure and deferral strategies.",
                impact=min(est_savings / max(acct["net"], 1), 1.0), effort=0.3, confidence=0.7,
                evidence={"net_income": acct["net"], "est_savings": round(est_savings, 2)},
            ))

        # Cash-flow: high AR relative to revenue → collections opportunity.
        if acct["ar_outstanding"] > 0 and acct["revenue"] > 0:
            ratio = acct["ar_outstanding"] / acct["revenue"]
            if ratio > 0.1:
                found.append(self._persist(
                    "accounting", "Accelerate receivables collection",
                    f"${acct['ar_outstanding']:.0f} in AR ({ratio*100:.0f}% of revenue) could be "
                    "collected faster with automated reminders and early-pay discounts.",
                    impact=min(ratio, 1.0), effort=0.2, confidence=0.75,
                    evidence={"ar": acct["ar_outstanding"], "ratio": round(ratio, 3)},
                ))

        # Automation: many pending tasks → workflow automation opportunity.
        if tasks["pending_count"] >= 5:
            found.append(self._persist(
                "tasks", "Automate recurring task load",
                f"{tasks['pending_count']} pending tasks indicate recurring work that could be "
                "automated via workflow templates.",
                impact=min(tasks["pending_count"] / 20, 1.0), effort=0.4, confidence=0.6,
                evidence={"pending": tasks["pending_count"]},
            ))

        # Goals: stalled goals → focus opportunity.
        if goals["at_risk"] > 0:
            found.append(self._persist(
                "goals", "Re-prioritize at-risk goals",
                f"{goals['at_risk']} goals are below 40% progress; concentrating effort could "
                "recover them this quarter.",
                impact=min(goals["at_risk"] / max(goals["total"], 1), 1.0), effort=0.3, confidence=0.65,
                evidence={"at_risk": goals["at_risk"], "total": goals["total"]},
            ))

        return sorted(found, key=lambda o: o["score"], reverse=True)

    def list(self, status: Optional[str] = None, min_score: float = 0.0) -> list[dict]:
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM opportunity WHERE status=? AND score>=? ORDER BY score DESC",
                    (status, min_score),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM opportunity WHERE score>=? ORDER BY score DESC", (min_score,)
                ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, opp_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM opportunity WHERE id=?", (opp_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def set_status(self, opp_id: str, status: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("UPDATE opportunity SET status=? WHERE id=?", (status, opp_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        try:
            d["evidence"] = json.loads(d["evidence"] or "{}")
        except Exception:
            d["evidence"] = {}
        return d


_instance: Optional[OpportunityEngine] = None


def get_opportunity_engine() -> OpportunityEngine:
    global _instance
    if _instance is None:
        _instance = OpportunityEngine()
    return _instance
