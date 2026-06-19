"""
Research Missions: create, schedule, run, and track research missions.
Each mission continuously collects, ranks, summarizes, and ingests intelligence.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from .db import get_connection, init_schema

TEAMS = {
    "market": {
        "name": "Market Intelligence Team",
        "domain": "markets",
        "description": "Monitors equities, sectors, earnings, macro signals",
        "connectors": ["yahoo_finance", "fred"],
    },
    "accounting": {
        "name": "Accounting Standards Team",
        "domain": "accounting",
        "description": "Tracks FASB, GAAP, PCAOB, audit standards",
        "connectors": ["federal_register", "sec_edgar"],
    },
    "tax": {
        "name": "Tax Research Team",
        "domain": "tax",
        "description": "Monitors IRS guidance, tax legislation, regulatory changes",
        "connectors": ["federal_register"],
    },
    "economic": {
        "name": "Economic Intelligence Team",
        "domain": "finance",
        "description": "Tracks GDP, CPI, employment, Fed policy, macro indicators",
        "connectors": ["fred", "bls"],
    },
    "technology": {
        "name": "Technology Intelligence Team",
        "domain": "strategy",
        "description": "Monitors tech sector, AI developments, SEC tech filings",
        "connectors": ["yahoo_finance", "sec_edgar"],
    },
    "competitive": {
        "name": "Competitive Intelligence Team",
        "domain": "strategy",
        "description": "Competitive landscape, industry dynamics, market position",
        "connectors": ["yahoo_finance", "sec_edgar", "federal_register"],
    },
}

SCHEDULE_DELTA = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


class ResearchMissions:
    def __init__(self):
        init_schema()
        self._seed_teams()

    def _seed_teams(self):
        conn = get_connection()
        for tid, td in TEAMS.items():
            existing = conn.execute("SELECT id FROM research_team WHERE id=?", (tid,)).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO research_team(id, name, domain, description, connectors)
                       VALUES(?,?,?,?,?)""",
                    (tid, td["name"], td["domain"], td["description"],
                     json.dumps(td["connectors"])),
                )
        conn.commit()
        conn.close()

    def create_mission(self, name: str, description: str = "", team: str = "market",
                       topics: list[str] | None = None, domain: str = "",
                       connectors: list[str] | None = None,
                       schedule: str = "daily") -> dict:
        mission_id = str(uuid.uuid4())
        team_info = TEAMS.get(team, {})
        actual_domain = domain or team_info.get("domain", "general")
        actual_connectors = connectors or team_info.get("connectors", [])
        next_run = (datetime.utcnow() + SCHEDULE_DELTA.get(schedule, timedelta(days=1))).isoformat()
        conn = get_connection()
        conn.execute(
            """INSERT INTO research_mission
               (id, name, description, team, topics, connectors, domain, schedule, next_run)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (mission_id, name, description, team,
             json.dumps(topics or []), json.dumps(actual_connectors),
             actual_domain, schedule, next_run),
        )
        conn.commit()
        conn.close()
        return self.get_mission(mission_id)

    def get_mission(self, mission_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM research_mission WHERE id=?", (mission_id,)).fetchone()
        conn.close()
        return self._fmt_mission(row) if row else None

    def _fmt_mission(self, row) -> dict:
        d = dict(row)
        for f in ("topics", "connectors"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        return d

    def list_missions(self, status: str = "active", team: Optional[str] = None) -> list[dict]:
        conn = get_connection()
        if team:
            rows = conn.execute(
                "SELECT * FROM research_mission WHERE status=? AND team=? ORDER BY created_at DESC",
                (status, team),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM research_mission WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        conn.close()
        return [self._fmt_mission(r) for r in rows]

    def run_mission(self, mission_id: str) -> dict:
        """Execute a research mission: poll connectors, synthesize, store report."""
        mission = self.get_mission(mission_id)
        if not mission:
            return {"error": "Mission not found"}
        from live_intelligence.monitor import get_monitor
        monitor = get_monitor()
        total_items = 0
        findings = []
        for connector_id in mission["connectors"]:
            try:
                result = monitor.poll_connector(connector_id, domain=mission["domain"])
                total_items += result.get("new_items", 0)
                if result.get("new_items", 0) > 0:
                    findings.append(
                        f"{connector_id}: {result['new_items']} new items ingested"
                    )
            except Exception as exc:
                findings.append(f"{connector_id}: error — {exc}")
        # synthesize if we have items
        summary = f"Mission '{mission['name']}' collected {total_items} new intelligence items."
        if findings:
            summary += " Sources: " + "; ".join(findings)
        # create synthesis report if items found
        citations = []
        if total_items > 0:
            try:
                from synthesis.engine import get_synthesis_engine
                topics_str = " ".join(mission["topics"]) if mission["topics"] else mission["name"]
                synth = get_synthesis_engine().synthesize(topics_str, n_sources=5,
                                                          domain=mission["domain"])
                summary = synth.get("summary", summary)
                citations = synth.get("citations", [])
            except Exception:
                pass
        report = self._create_report(
            mission_id=mission_id,
            team=mission["team"],
            title=f"{mission['name']} — Research Report",
            summary=summary,
            findings=findings,
            citations=citations,
            item_count=total_items,
            domain=mission["domain"],
        )
        # update mission stats
        conn = get_connection()
        next_run = (datetime.utcnow() + SCHEDULE_DELTA.get(mission["schedule"],
                    timedelta(days=1))).isoformat()
        conn.execute(
            """UPDATE research_mission SET run_count=run_count+1, last_run=datetime('now'),
               next_run=? WHERE id=?""",
            (next_run, mission_id),
        )
        conn.commit()
        conn.close()
        return {"mission_id": mission_id, "report_id": report["id"],
                "items_collected": total_items, "findings": findings}

    def _create_report(self, mission_id: str, team: str, title: str, summary: str,
                       findings: list[str], citations: list[dict], item_count: int,
                       domain: str) -> dict:
        report_id = str(uuid.uuid4())
        conn = get_connection()
        conn.execute(
            """INSERT INTO research_report
               (id, mission_id, team, title, summary, findings, citations, item_count, domain)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (report_id, mission_id, team, title, summary,
             json.dumps(findings), json.dumps(citations), item_count, domain),
        )
        conn.execute(
            "UPDATE research_team SET total_reports=total_reports+1 WHERE id=?", (team,)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM research_report WHERE id=?", (report_id,)).fetchone()
        conn.close()
        return self._fmt_report(row)

    def _fmt_report(self, row) -> dict:
        d = dict(row)
        for f in ("findings", "citations"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        return d

    def list_reports(self, mission_id: Optional[str] = None, team: Optional[str] = None,
                     limit: int = 20) -> list[dict]:
        conn = get_connection()
        clauses, params = [], []
        if mission_id:
            clauses.append("mission_id=?"); params.append(mission_id)
        if team:
            clauses.append("team=?"); params.append(team)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM research_report {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [self._fmt_report(r) for r in rows]

    def teams(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM research_team ORDER BY name").fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["connectors"] = json.loads(d["connectors"])
            except Exception:
                d["connectors"] = []
            result.append(d)
        return result

    def pause_mission(self, mission_id: str) -> Optional[dict]:
        conn = get_connection()
        conn.execute("UPDATE research_mission SET status='paused' WHERE id=?", (mission_id,))
        conn.commit()
        conn.close()
        return self.get_mission(mission_id)

    def stats(self) -> dict:
        conn = get_connection()
        missions = conn.execute("SELECT COUNT(*) FROM research_mission WHERE status='active'").fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM research_report").fetchone()[0]
        teams_active = conn.execute("SELECT COUNT(*) FROM research_team").fetchone()[0]
        total_items = conn.execute("SELECT SUM(item_count) FROM research_report").fetchone()[0] or 0
        conn.close()
        return {"active_missions": missions, "total_reports": reports,
                "teams": teams_active, "total_items_collected": total_items}


_instance: Optional[ResearchMissions] = None


def get_research_missions() -> ResearchMissions:
    global _instance
    if _instance is None:
        _instance = ResearchMissions()
    return _instance
