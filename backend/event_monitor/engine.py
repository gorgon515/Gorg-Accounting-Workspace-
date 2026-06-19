"""
Event Monitoring Engine: continuous surveillance across accounting, tax, markets, operations.
Monitors deadlines, regulatory changes, SEC filings, earnings, portfolio events, system health.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_DB = Path(".data/event_monitor.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS monitored_event (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            severity TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'active',
            source TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            due_date TEXT,
            triggered_at TEXT DEFAULT (datetime('now')),
            acknowledged_at TEXT,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS event_rule (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            keywords TEXT DEFAULT '[]',
            severity TEXT DEFAULT 'medium',
            enabled INTEGER DEFAULT 1,
            check_interval_hours INTEGER DEFAULT 24,
            last_checked TEXT,
            trigger_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS deadline (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline_date TEXT NOT NULL,
            category TEXT DEFAULT 'tax',
            client_id TEXT DEFAULT '',
            recurrence TEXT DEFAULT 'none',
            status TEXT DEFAULT 'pending',
            reminder_days INTEGER DEFAULT 7,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS system_health_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            recorded_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


EVENT_CATEGORIES = {
    "accounting_standards": {
        "description": "FASB, GAAP, PCAOB updates and new standards",
        "keywords": ["fasb", "gaap", "asu", "asc", "pcaob", "audit standard", "accounting standard"],
        "severity": "high",
        "sources": ["federal_register", "sec_edgar"],
    },
    "tax_regulatory": {
        "description": "IRS guidance, tax legislation, regulatory changes",
        "keywords": ["irs", "tax", "revenue procedure", "revenue ruling", "notice", "treasury"],
        "severity": "high",
        "sources": ["federal_register"],
    },
    "sec_filings": {
        "description": "Material SEC filings from watchlisted companies",
        "keywords": ["10-k", "10-q", "8-k", "material event", "proxy", "s-1"],
        "severity": "medium",
        "sources": ["sec_edgar"],
    },
    "earnings": {
        "description": "Earnings releases and guidance updates",
        "keywords": ["earnings", "eps", "revenue", "guidance", "quarterly results", "annual results"],
        "severity": "medium",
        "sources": ["yahoo_finance"],
    },
    "macro_economic": {
        "description": "Fed decisions, economic data releases",
        "keywords": ["fed", "federal reserve", "fomc", "gdp", "cpi", "unemployment", "interest rate"],
        "severity": "medium",
        "sources": ["fred", "bls"],
    },
    "portfolio": {
        "description": "Portfolio position changes and risk events",
        "keywords": ["portfolio", "position", "allocation", "drawdown", "risk", "volatility"],
        "severity": "high",
        "sources": ["yahoo_finance"],
    },
    "deadline": {
        "description": "Tax filing, compliance, and engagement deadlines",
        "keywords": ["deadline", "due date", "filing date", "extension", "compliance"],
        "severity": "critical",
        "sources": ["internal"],
    },
    "system": {
        "description": "System health, connector failures, data quality issues",
        "keywords": ["error", "failure", "offline", "timeout", "quality"],
        "severity": "low",
        "sources": ["internal"],
    },
}

_BUILT_IN_RULES = [
    {
        "id": "er_fasb_update",
        "name": "FASB Standard Update",
        "category": "accounting_standards",
        "event_type": "standard_update",
        "description": "New FASB Accounting Standards Update detected",
        "keywords": ["fasb", "asu", "accounting standards update"],
        "severity": "high",
        "check_interval_hours": 24,
    },
    {
        "id": "er_irs_guidance",
        "name": "IRS Guidance Publication",
        "category": "tax_regulatory",
        "event_type": "irs_guidance",
        "description": "New IRS revenue procedure, ruling, or notice",
        "keywords": ["irs", "revenue procedure", "revenue ruling", "notice"],
        "severity": "high",
        "check_interval_hours": 24,
    },
    {
        "id": "er_material_filing",
        "name": "Material SEC Filing",
        "category": "sec_filings",
        "event_type": "material_filing",
        "description": "8-K or material event filing from tracked company",
        "keywords": ["8-k", "material event", "current report"],
        "severity": "medium",
        "check_interval_hours": 1,
    },
    {
        "id": "er_fed_decision",
        "name": "Federal Reserve Decision",
        "category": "macro_economic",
        "event_type": "fed_decision",
        "description": "FOMC rate decision or Fed policy statement",
        "keywords": ["fomc", "federal reserve", "rate decision", "basis points"],
        "severity": "high",
        "check_interval_hours": 6,
    },
    {
        "id": "er_deadline_approaching",
        "name": "Deadline Approaching",
        "category": "deadline",
        "event_type": "deadline_reminder",
        "description": "Tax or compliance deadline within reminder window",
        "keywords": ["deadline", "due date"],
        "severity": "critical",
        "check_interval_hours": 12,
    },
    {
        "id": "er_connector_failure",
        "name": "Connector Health Failure",
        "category": "system",
        "event_type": "connector_offline",
        "description": "Data connector health check failed",
        "keywords": ["error", "offline", "failure"],
        "severity": "medium",
        "check_interval_hours": 1,
    },
]


class EventMonitor:
    def __init__(self):
        conn = _conn()
        for rule in _BUILT_IN_RULES:
            existing = conn.execute("SELECT id FROM event_rule WHERE id=?", (rule["id"],)).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO event_rule(id, name, category, event_type, description,
                       keywords, severity, check_interval_hours)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (rule["id"], rule["name"], rule["category"], rule["event_type"],
                     rule["description"], json.dumps(rule["keywords"]),
                     rule["severity"], rule["check_interval_hours"]),
                )
        conn.commit()
        conn.close()

    def scan_intelligence(self) -> list[dict]:
        """Scan recent live intelligence for event triggers."""
        try:
            from live_intelligence.monitor import get_monitor
            monitor = get_monitor()
        except Exception:
            return []

        conn = _conn()
        rules = conn.execute("SELECT * FROM event_rule WHERE enabled=1").fetchall()
        conn.close()

        triggered = []
        for rule in rules:
            rule_d = dict(rule)
            keywords = json.loads(rule_d.get("keywords", "[]"))
            domain_map = {
                "accounting_standards": ["accounting"],
                "tax_regulatory": ["tax"],
                "sec_filings": ["markets"],
                "earnings": ["markets"],
                "macro_economic": ["finance"],
                "portfolio": ["markets"],
                "system": [],
                "deadline": [],
            }
            domains = domain_map.get(rule_d["category"], [])
            items = []
            for domain in domains:
                items.extend(monitor.list_items(domain=domain, limit=20))

            for item in items:
                text = f"{item.get('title', '')} {item.get('content', '')}".lower()
                if any(kw.lower() in text for kw in keywords):
                    event = self.create_event(
                        category=rule_d["category"],
                        event_type=rule_d["event_type"],
                        title=f"{rule_d['name']}: {item.get('title', '')[:80]}",
                        description=item.get("content", "")[:300],
                        severity=rule_d["severity"],
                        source=item.get("source", ""),
                        metadata={"item_id": item.get("id", ""), "rule_id": rule_d["id"]},
                    )
                    triggered.append(event)
                    break  # one event per rule per scan

            conn = _conn()
            conn.execute(
                "UPDATE event_rule SET last_checked=datetime('now'), trigger_count=trigger_count+? WHERE id=?",
                (1 if triggered and triggered[-1].get("metadata", {}).get("rule_id") == rule_d["id"] else 0,
                 rule_d["id"]),
            )
            conn.commit()
            conn.close()

        return triggered

    def check_deadlines(self) -> list[dict]:
        """Check for upcoming deadlines and create reminder events."""
        conn = _conn()
        today = datetime.utcnow().date()
        rows = conn.execute(
            "SELECT * FROM deadline WHERE status='pending' ORDER BY deadline_date"
        ).fetchall()
        conn.close()

        events = []
        for row in rows:
            d = dict(row)
            try:
                due = datetime.strptime(d["deadline_date"], "%Y-%m-%d").date()
                days_remaining = (due - today).days
                reminder_days = d.get("reminder_days", 7)
                if 0 <= days_remaining <= reminder_days:
                    event = self.create_event(
                        category="deadline",
                        event_type="deadline_reminder",
                        title=f"Deadline Approaching: {d['title']}",
                        description=f"{d['description']} — Due {d['deadline_date']} ({days_remaining} days)",
                        severity="critical" if days_remaining <= 2 else "high",
                        source="internal",
                        metadata={"deadline_id": d["id"], "days_remaining": days_remaining},
                        due_date=d["deadline_date"],
                    )
                    events.append(event)
            except Exception:
                pass
        return events

    def record_system_health(self, component: str, status: str, message: str = "",
                              metadata: dict | None = None):
        conn = _conn()
        conn.execute(
            """INSERT INTO system_health_event(component, status, message, metadata)
               VALUES(?,?,?,?)""",
            (component, status, message, json.dumps(metadata or {})),
        )
        conn.commit()
        conn.close()
        if status in ("error", "offline", "critical"):
            self.create_event(
                category="system",
                event_type="connector_offline",
                title=f"System Health: {component} — {status}",
                description=message,
                severity="medium" if status == "error" else "high",
                source="system",
                metadata={"component": component, **(metadata or {})},
            )

    def create_event(self, category: str, event_type: str, title: str,
                     description: str = "", severity: str = "medium",
                     source: str = "", metadata: dict | None = None,
                     due_date: str | None = None) -> dict:
        event_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO monitored_event
               (id, category, event_type, title, description, severity, source, metadata, due_date)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (event_id, category, event_type, title, description, severity, source,
             json.dumps(metadata or {}), due_date),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monitored_event WHERE id=?", (event_id,)).fetchone()
        conn.close()
        return self._fmt(row)

    def list_events(self, category: str | None = None, severity: str | None = None,
                    status: str = "active", limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses = ["status=?"]; params: list = [status]
        if category:
            clauses.append("category=?"); params.append(category)
        if severity:
            clauses.append("severity=?"); params.append(severity)
        rows = conn.execute(
            f"SELECT * FROM monitored_event WHERE {' AND '.join(clauses)} ORDER BY triggered_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def acknowledge_event(self, event_id: str) -> Optional[dict]:
        conn = _conn()
        conn.execute(
            "UPDATE monitored_event SET status='acknowledged', acknowledged_at=datetime('now') WHERE id=?",
            (event_id,),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monitored_event WHERE id=?", (event_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def resolve_event(self, event_id: str) -> Optional[dict]:
        conn = _conn()
        conn.execute(
            "UPDATE monitored_event SET status='resolved', resolved_at=datetime('now') WHERE id=?",
            (event_id,),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monitored_event WHERE id=?", (event_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def add_deadline(self, title: str, deadline_date: str, description: str = "",
                     category: str = "tax", client_id: str = "",
                     reminder_days: int = 7) -> dict:
        deadline_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO deadline(id, title, description, deadline_date, category,
               client_id, reminder_days) VALUES(?,?,?,?,?,?,?)""",
            (deadline_id, title, description, deadline_date, category, client_id, reminder_days),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM deadline WHERE id=?", (deadline_id,)).fetchone()
        conn.close()
        return dict(row)

    def list_deadlines(self, category: str | None = None, status: str = "pending",
                       limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses = ["status=?"]; params: list = [status]
        if category:
            clauses.append("category=?"); params.append(category)
        rows = conn.execute(
            f"SELECT * FROM deadline WHERE {' AND '.join(clauses)} ORDER BY deadline_date ASC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_rules(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM event_rule ORDER BY category, name").fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["keywords"] = json.loads(d["keywords"])
            except Exception:
                d["keywords"] = []
            result.append(d)
        return result

    def _fmt(self, row) -> dict:
        d = dict(row)
        try:
            d["metadata"] = json.loads(d["metadata"])
        except Exception:
            d["metadata"] = {}
        return d

    def stats(self) -> dict:
        conn = _conn()
        active = conn.execute(
            "SELECT COUNT(*) FROM monitored_event WHERE status='active'"
        ).fetchone()[0]
        critical = conn.execute(
            "SELECT COUNT(*) FROM monitored_event WHERE status='active' AND severity='critical'"
        ).fetchone()[0]
        deadlines = conn.execute(
            "SELECT COUNT(*) FROM deadline WHERE status='pending'"
        ).fetchone()[0]
        rules = conn.execute("SELECT COUNT(*) FROM event_rule WHERE enabled=1").fetchone()[0]
        conn.close()
        return {
            "active_events": active,
            "critical_events": critical,
            "pending_deadlines": deadlines,
            "active_rules": rules,
        }


_instance: Optional[EventMonitor] = None


def get_event_monitor() -> EventMonitor:
    global _instance
    if _instance is None:
        _instance = EventMonitor()
    return _instance
