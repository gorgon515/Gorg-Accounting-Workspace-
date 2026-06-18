"""RiskEngine — monitors domains and scores risks with mitigation strategies.

Risk score = probability * impact, normalized to 0..100. Severity bands:
  >=70 critical, >=45 high, >=20 medium, else low.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from .db import get_connection, now


def _severity(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


class RiskEngine:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def _persist(self, domain, title, description, probability, impact, mitigation) -> dict:
        risk_id = "risk_" + uuid.uuid4().hex[:12]
        score = round(min(probability * impact, 1.0) * 100, 1)
        sev = _severity(score)
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO risk (id, domain, title, description, score, severity, probability, "
                "impact, mitigation, status, created_at) VALUES (?,?,?,?,?,?,?,?,?, 'open', ?)",
                (risk_id, domain, title, description, score, sev, probability, impact,
                 json.dumps(mitigation), now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": risk_id, "domain": domain, "title": title, "description": description,
                "score": score, "severity": sev, "probability": probability, "impact": impact,
                "mitigation": mitigation, "status": "open"}

    def scan(self) -> list[dict]:
        from .sources import accounting_snapshot, goals_snapshot, tasks_snapshot
        conn = self._conn()
        try:
            conn.execute("DELETE FROM risk WHERE status='open'")
            conn.commit()
        finally:
            conn.close()

        acct = accounting_snapshot()
        goals = goals_snapshot()
        tasks = tasks_snapshot()
        found = []

        # Cash-flow risk: negative net income.
        if acct["net"] < 0:
            found.append(self._persist(
                "accounting", "Negative net income",
                f"Operating at a loss (net ${acct['net']:.0f}). Sustained losses threaten runway.",
                probability=0.8, impact=0.9,
                mitigation=["Review discretionary expenses", "Reprice underperforming services",
                            "Accelerate collections"],
            ))

        # AR concentration risk.
        if acct["revenue"] > 0 and acct["ar_outstanding"] / acct["revenue"] > 0.3:
            found.append(self._persist(
                "accounting", "High receivables concentration",
                f"${acct['ar_outstanding']:.0f} AR exceeds 30% of revenue — collection delay risk.",
                probability=0.6, impact=0.7,
                mitigation=["Tighten credit terms", "Automate dunning", "Offer early-pay discounts"],
            ))

        # Goal slippage risk.
        if goals["total"] > 0 and goals["at_risk"] / goals["total"] > 0.3:
            found.append(self._persist(
                "goals", "Goal portfolio slippage",
                f"{goals['at_risk']} of {goals['total']} goals are at risk of missing targets.",
                probability=0.65, impact=0.5,
                mitigation=["Rebalance effort to top goals", "Defer low-priority goals"],
            ))

        # Operational overload risk.
        if tasks["pending_count"] >= 12:
            found.append(self._persist(
                "tasks", "Operational overload",
                f"{tasks['pending_count']} pending tasks may exceed capacity and cause missed deadlines.",
                probability=0.55, impact=0.6,
                mitigation=["Delegate or automate", "Triage and drop low-value tasks"],
            ))

        # Compliance/data risk if accounting unavailable.
        if not acct["available"]:
            found.append(self._persist(
                "compliance", "Accounting data unavailable",
                "No accounting database found — financial monitoring and integrity checks degraded.",
                probability=0.4, impact=0.5,
                mitigation=["Verify data directory", "Restore from backup"],
            ))

        return sorted(found, key=lambda r: r["score"], reverse=True)

    def list(self, status: Optional[str] = None, severity: Optional[str] = None) -> list[dict]:
        clauses, params = [], []
        if status:
            clauses.append("status=?")
            params.append(status)
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT * FROM risk {where} ORDER BY score DESC", tuple(params)
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, risk_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM risk WHERE id=?", (risk_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def set_status(self, risk_id: str, status: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("UPDATE risk SET status=? WHERE id=?", (status, risk_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def summary(self) -> dict:
        risks = self.list(status="open")
        by_sev = {}
        for r in risks:
            by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
        top = risks[0] if risks else None
        return {"open_risks": len(risks), "by_severity": by_sev,
                "top_risk": top["title"] if top else None,
                "max_score": top["score"] if top else 0}

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        try:
            d["mitigation"] = json.loads(d["mitigation"] or "[]")
        except Exception:
            d["mitigation"] = []
        return d


_instance: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    global _instance
    if _instance is None:
        _instance = RiskEngine()
    return _instance
