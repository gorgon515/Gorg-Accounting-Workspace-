"""AutonomousProposalLoop — the daily strategic scan.

Scans all domains, generates a strategic briefing plus draft actions (tasks,
workflows, research, accounting reviews), and files every draft into an approval
queue. Nothing above Tier 1 executes automatically — human approval is mandatory.

Tiers:
  1 — informational / draft only (safe to auto-create as a proposal)
  2 — operational change (requires approval)
  3 — financial / external commitment (requires explicit approval; never auto)
"""
from __future__ import annotations

import uuid
from typing import Optional

from intelligence.db import get_connection, now


class AutonomousProposalLoop:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def _add(self, kind: str, title: str, detail: str, rationale: str,
             tier: int, source: str) -> dict:
        pid = "prop_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO proposal (id, kind, title, detail, rationale, tier, status, source, created_at) "
                "VALUES (?,?,?,?,?,?, 'pending', ?, ?)",
                (pid, kind, title, detail, rationale, tier, source, now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": pid, "kind": kind, "title": title, "detail": detail,
                "rationale": rationale, "tier": tier, "status": "pending", "source": source}

    def run_daily(self) -> dict:
        """Execute the morning scan and produce the strategic briefing + proposals."""
        from intelligence.opportunities import get_opportunity_engine
        from intelligence.risks import get_risk_engine
        from intelligence.sources import accounting_snapshot, goals_snapshot, tasks_snapshot

        opps = get_opportunity_engine().scan()
        risks = get_risk_engine().scan()
        acct = accounting_snapshot()
        goals = goals_snapshot()
        tasks = tasks_snapshot()

        created = []

        # Draft accounting review proposal when there is meaningful ledger activity.
        if acct["available"] and acct["entry_count"] > 0:
            created.append(self._add(
                "accounting_review", "Review month-to-date ledger",
                f"Revenue ${acct['revenue']:.0f}, expenses ${acct['expenses']:.0f}, "
                f"net ${acct['net']:.0f} across {acct['entry_count']} entries.",
                "Routine financial oversight keeps the books decision-ready.",
                tier=1, source="proposal_loop",
            ))

        # Draft tasks for the top opportunities.
        for o in opps[:2]:
            created.append(self._add(
                "task", f"Act on: {o['title']}", o["description"],
                f"Opportunity score {o['score']} in {o['domain']}.",
                tier=1, source="opportunity_engine",
            ))

        # Draft mitigation workflows for high/critical risks.
        for r in risks:
            if r["severity"] in ("critical", "high"):
                created.append(self._add(
                    "workflow", f"Mitigation plan: {r['title']}",
                    "; ".join(r["mitigation"]) if r["mitigation"] else r["description"],
                    f"{r['severity'].title()} risk (score {r['score']}) in {r['domain']}.",
                    tier=2, source="risk_engine",
                ))

        # Draft a research project if at-risk goals need a plan.
        if goals["at_risk"] > 0:
            created.append(self._add(
                "research", "Recovery plan for at-risk goals",
                f"{goals['at_risk']} goals below 40% — draft a focused recovery plan.",
                "Concentrating effort recovers stalled goals.",
                tier=1, source="goals",
            ))

        briefing = self._briefing(opps, risks, acct, goals, tasks)
        return {
            "briefing": briefing,
            "proposals_created": len(created),
            "proposals": created,
            "scanned": {"opportunities": len(opps), "risks": len(risks),
                        "pending_tasks": tasks["pending_count"]},
        }

    @staticmethod
    def _briefing(opps, risks, acct, goals, tasks) -> str:
        lines = ["Daily Strategic Briefing", "=" * 24]
        if acct["available"]:
            lines.append(f"Financials: net ${acct['net']:.0f} "
                         f"(rev ${acct['revenue']:.0f} / exp ${acct['expenses']:.0f}).")
        lines.append(f"Goals: {goals['active']} active, {goals['at_risk']} at risk.")
        lines.append(f"Tasks: {tasks['pending_count']} pending.")
        if opps:
            lines.append(f"Top opportunity: {opps[0]['title']} (score {opps[0]['score']}).")
        if risks:
            lines.append(f"Top risk: {risks[0]['title']} ({risks[0]['severity']}).")
        lines.append("All drafts filed to the approval queue; nothing executes automatically.")
        return "\n".join(lines)

    # ---- Approval queue ----

    def list_proposals(self, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM proposal WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM proposal ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def decide(self, proposal_id: str, decision: str) -> dict:
        if decision not in ("approved", "rejected"):
            raise ValueError("decision must be 'approved' or 'rejected'")
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE proposal SET status=?, decided_at=? WHERE id=?",
                (decision, now(), proposal_id),
            )
            conn.commit()
            return {"id": proposal_id, "status": decision, "updated": cur.rowcount > 0}
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) c FROM proposal GROUP BY status"
            ).fetchall()
            by_status = {r["status"]: r["c"] for r in rows}
            return {"by_status": by_status, "pending": by_status.get("pending", 0)}
        finally:
            conn.close()


_instance: Optional[AutonomousProposalLoop] = None


def get_proposal_loop() -> AutonomousProposalLoop:
    global _instance
    if _instance is None:
        _instance = AutonomousProposalLoop()
    return _instance
