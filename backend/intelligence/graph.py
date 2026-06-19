"""IntelligenceGraph — cross-domain knowledge graph with relationship discovery."""
from __future__ import annotations

import uuid
from typing import Optional

from .db import get_connection, now

DOMAINS = [
    "accounting", "tax", "markets", "portfolio", "calendar", "tasks", "goals",
    "documents", "research", "email", "projects", "clients", "memory",
]


class IntelligenceGraph:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def add_node(self, domain: str, label: str, attributes: Optional[dict] = None) -> dict:
        import json
        node_id = "n_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO intel_node (id, domain, label, attributes, created_at) VALUES (?,?,?,?,?)",
                (node_id, domain, label, json.dumps(attributes or {}), now()),
            )
            conn.commit()
            return {"id": node_id, "domain": domain, "label": label, "attributes": attributes or {}}
        finally:
            conn.close()

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0) -> dict:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO intel_edge (source_id, target_id, relationship, weight, created_at) "
                "VALUES (?,?,?,?,?)",
                (source_id, target_id, relationship, weight, now()),
            )
            conn.commit()
            return {"id": cur.lastrowid, "source_id": source_id, "target_id": target_id,
                    "relationship": relationship, "weight": weight}
        finally:
            conn.close()

    def nodes(self, domain: Optional[str] = None) -> list[dict]:
        import json
        conn = self._conn()
        try:
            if domain:
                rows = conn.execute("SELECT * FROM intel_node WHERE domain=?", (domain,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM intel_node").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["attributes"] = json.loads(d["attributes"] or "{}")
                out.append(d)
            return out
        finally:
            conn.close()

    def edges(self) -> list[dict]:
        conn = self._conn()
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM intel_edge").fetchall()]
        finally:
            conn.close()

    def neighbors(self, node_id: str) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM intel_edge WHERE source_id=? OR target_id=?", (node_id, node_id)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def build_from_domains(self) -> dict:
        """Materialize a baseline graph from live subsystem data and connect
        domains that share dependencies (e.g. clients → accounting → cash flow)."""
        from .sources import accounting_snapshot, goals_snapshot, tasks_snapshot
        conn = self._conn()
        try:
            conn.execute("DELETE FROM intel_edge")
            conn.execute("DELETE FROM intel_node")
            conn.commit()
        finally:
            conn.close()

        acct = accounting_snapshot()
        goals = goals_snapshot()
        tasks = tasks_snapshot()

        n_acct = self.add_node("accounting", "Accounting Ledger",
                               {"revenue": acct["revenue"], "net": acct["net"]})
        n_cash = self.add_node("portfolio", "Cash Position", {"ar": acct["ar_outstanding"]})
        n_goals = self.add_node("goals", "Active Goals", {"count": goals["active"]})
        n_tasks = self.add_node("tasks", "Open Tasks", {"count": tasks["pending_count"]})
        n_clients = self.add_node("clients", "Client Book", {})

        self.add_edge(n_clients["id"], n_acct["id"], "generates_revenue", 0.9)
        self.add_edge(n_acct["id"], n_cash["id"], "drives", 0.8)
        self.add_edge(n_goals["id"], n_acct["id"], "depends_on", 0.6)
        self.add_edge(n_tasks["id"], n_goals["id"], "advances", 0.5)

        return {"nodes": len(self.nodes()), "edges": len(self.edges()), "domains": DOMAINS}

    def discover_relationships(self) -> list[dict]:
        """Surface notable cross-domain relationships as plain-language insights."""
        from .sources import accounting_snapshot, goals_snapshot, tasks_snapshot
        acct = accounting_snapshot()
        goals = goals_snapshot()
        tasks = tasks_snapshot()
        insights = []
        if acct["ar_outstanding"] > 0 and acct["revenue"] > 0:
            ratio = acct["ar_outstanding"] / max(acct["revenue"], 1)
            insights.append({
                "domains": ["accounting", "portfolio"],
                "relationship": "AR concentration affects cash position",
                "strength": round(min(ratio, 1.0), 2),
                "detail": f"${acct['ar_outstanding']:.0f} outstanding vs ${acct['revenue']:.0f} revenue",
            })
        if goals["at_risk"] > 0 and tasks["pending_count"] > 0:
            insights.append({
                "domains": ["goals", "tasks"],
                "relationship": "At-risk goals lack supporting task throughput",
                "strength": round(min(goals["at_risk"] / max(goals["total"], 1), 1.0), 2),
                "detail": f"{goals['at_risk']} goals at risk, {tasks['pending_count']} tasks pending",
            })
        if acct["net"] < 0:
            insights.append({
                "domains": ["accounting", "clients"],
                "relationship": "Negative net income pressures client pricing strategy",
                "strength": 0.8,
                "detail": f"Net income ${acct['net']:.0f}",
            })
        return insights

    def stats(self) -> dict:
        return {"nodes": len(self.nodes()), "edges": len(self.edges()),
                "domains": len(DOMAINS), "insights": len(self.discover_relationships())}


_instance: Optional[IntelligenceGraph] = None


def get_graph() -> IntelligenceGraph:
    global _instance
    if _instance is None:
        _instance = IntelligenceGraph()
    return _instance
