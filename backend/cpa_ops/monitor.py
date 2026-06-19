"""
CPA Operations Hub: monitors tax law, accounting standards, and regulatory changes.
Aggregates intelligence into actionable advisories for CPA workflows.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

_DB = Path(".data/cpa_ops.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS regulatory_update (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            effective_date TEXT,
            impact_areas TEXT DEFAULT '[]',
            action_required INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'normal',
            url TEXT DEFAULT '',
            raw_content TEXT DEFAULT '',
            ingested_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS client_advisory (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            advisory_type TEXT DEFAULT 'general',
            trigger_update_id TEXT,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now')),
            sent_at TEXT
        );

        CREATE TABLE IF NOT EXISTS compliance_item (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'tax',
            due_date TEXT,
            client_id TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'normal',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS digest_run (
            id TEXT PRIMARY KEY,
            period TEXT NOT NULL,
            summary TEXT DEFAULT '',
            update_count INTEGER DEFAULT 0,
            advisory_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


TAX_KEYWORDS = [
    "irs", "tax", "revenue procedure", "revenue ruling", "notice", "treasury",
    "internal revenue", "income tax", "estate tax", "gift tax", "excise tax",
    "tax credit", "deduction", "depreciation", "basis", "capital gain",
]

ACCOUNTING_KEYWORDS = [
    "fasb", "gaap", "asu", "asc", "accounting standard", "pcaob", "audit",
    "financial statement", "disclosure", "revenue recognition", "lease",
    "credit loss", "fair value", "consolidation",
]

REGULATORY_KEYWORDS = [
    "sec", "regulation", "rule", "compliance", "enforcement", "guidance",
    "federal register", "cfr", "requirement", "mandate",
]


class CPAMonitor:
    def __init__(self):
        _conn().close()

    def ingest_regulatory_updates(self) -> list[dict]:
        """Pull new regulatory items from live intelligence and classify them."""
        try:
            from live_intelligence.monitor import get_monitor
            monitor = get_monitor()
        except Exception:
            return []

        updates = []
        domain_map = [
            ("tax", "tax_regulatory"),
            ("accounting", "accounting_standards"),
        ]
        for domain, category in domain_map:
            items = monitor.list_items(domain=domain, limit=30)
            for item in items:
                text = f"{item.get('title', '')} {item.get('content', '')}".lower()
                priority = "high" if any(kw in text for kw in ["fasb", "irs", "revenue ruling"]) else "normal"
                action_required = any(kw in text for kw in ["effective", "required", "mandatory", "deadline"])
                update = self._store_update(
                    category=category,
                    source=item.get("source", ""),
                    title=item.get("title", "")[:200],
                    summary=item.get("content", "")[:500],
                    priority=priority,
                    action_required=action_required,
                    url=item.get("url", ""),
                )
                if update:
                    updates.append(update)
        return updates

    def _store_update(self, category: str, source: str, title: str, summary: str,
                      priority: str = "normal", action_required: bool = False,
                      url: str = "", effective_date: str = "") -> Optional[dict]:
        update_id = str(uuid.uuid4())
        conn = _conn()
        existing = conn.execute(
            "SELECT id FROM regulatory_update WHERE title=? AND source=?", (title, source)
        ).fetchone()
        if existing:
            conn.close()
            return None
        conn.execute(
            """INSERT INTO regulatory_update
               (id, category, source, title, summary, priority, action_required, url, effective_date)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (update_id, category, source, title, summary, priority,
             1 if action_required else 0, url, effective_date),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM regulatory_update WHERE id=?", (update_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_updates(self, category: str | None = None, priority: str | None = None,
                     limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if category:
            clauses.append("category=?"); params.append(category)
        if priority:
            clauses.append("priority=?"); params.append(priority)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM regulatory_update {where} ORDER BY ingested_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_advisory(self, title: str, body: str, advisory_type: str = "general",
                        trigger_update_id: str | None = None,
                        priority: str = "normal") -> dict:
        advisory_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO client_advisory(id, title, body, advisory_type, trigger_update_id, priority)
               VALUES(?,?,?,?,?,?)""",
            (advisory_id, title, body, advisory_type, trigger_update_id, priority),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM client_advisory WHERE id=?", (advisory_id,)).fetchone()
        conn.close()
        return dict(row)

    def list_advisories(self, status: str | None = None, advisory_type: str | None = None,
                        limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if status:
            clauses.append("status=?"); params.append(status)
        if advisory_type:
            clauses.append("advisory_type=?"); params.append(advisory_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM client_advisory {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def generate_auto_advisories(self, updates: list[dict]) -> list[dict]:
        """Auto-generate draft advisories for high-priority regulatory updates."""
        advisories = []
        for update in updates:
            if update.get("priority") != "high":
                continue
            title = f"Advisory: {update['title'][:100]}"
            body = (
                f"DRAFT ADVISORY\n\n"
                f"Subject: {update['title']}\n\n"
                f"Summary: {update.get('summary', '')}\n\n"
                f"Source: {update.get('source', '')}\n"
                f"Category: {update.get('category', '')}\n\n"
                f"Action Required: {'Yes' if update.get('action_required') else 'Review recommended'}\n\n"
                f"[REVIEW AND CUSTOMIZE BEFORE SENDING TO CLIENTS]"
            )
            adv = self.create_advisory(
                title=title, body=body,
                advisory_type=update.get("category", "general"),
                trigger_update_id=update.get("id"),
                priority="high",
            )
            advisories.append(adv)
        return advisories

    def add_compliance_item(self, title: str, description: str = "",
                             category: str = "tax", due_date: str = "",
                             client_id: str = "", priority: str = "normal") -> dict:
        item_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO compliance_item(id, title, description, category, due_date, client_id, priority)
               VALUES(?,?,?,?,?,?,?)""",
            (item_id, title, description, category, due_date, client_id, priority),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM compliance_item WHERE id=?", (item_id,)).fetchone()
        conn.close()
        return dict(row)

    def list_compliance(self, category: str | None = None, status: str = "open",
                        limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses = ["status=?"]; params: list = [status]
        if category:
            clauses.append("category=?"); params.append(category)
        rows = conn.execute(
            f"SELECT * FROM compliance_item WHERE {' AND '.join(clauses)} ORDER BY due_date ASC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def run_digest(self) -> dict:
        """Generate a research digest of recent regulatory activity."""
        updates = self.ingest_regulatory_updates()
        advisories = self.generate_auto_advisories(updates)
        period = datetime.utcnow().strftime("%Y-%m-%d")
        categories = {}
        for u in updates:
            cat = u.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1
        summary_parts = [f"{period} Regulatory Digest:"]
        for cat, count in categories.items():
            summary_parts.append(f"  {cat}: {count} update(s)")
        if advisories:
            summary_parts.append(f"  Auto-generated {len(advisories)} draft advisory/advisories")
        summary = "\n".join(summary_parts)
        digest_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO digest_run(id, period, summary, update_count, advisory_count)
               VALUES(?,?,?,?,?)""",
            (digest_id, period, summary, len(updates), len(advisories)),
        )
        conn.commit()
        conn.close()
        return {
            "digest_id": digest_id,
            "period": period,
            "summary": summary,
            "updates": updates,
            "advisories": advisories,
            "update_count": len(updates),
            "advisory_count": len(advisories),
        }

    def stats(self) -> dict:
        conn = _conn()
        updates = conn.execute("SELECT COUNT(*) FROM regulatory_update").fetchone()[0]
        advisories = conn.execute(
            "SELECT COUNT(*) FROM client_advisory WHERE status='draft'"
        ).fetchone()[0]
        compliance = conn.execute(
            "SELECT COUNT(*) FROM compliance_item WHERE status='open'"
        ).fetchone()[0]
        high_priority = conn.execute(
            "SELECT COUNT(*) FROM regulatory_update WHERE priority='high'"
        ).fetchone()[0]
        conn.close()
        return {
            "total_updates": updates,
            "draft_advisories": advisories,
            "open_compliance_items": compliance,
            "high_priority_updates": high_priority,
        }


_instance: Optional[CPAMonitor] = None


def get_cpa_monitor() -> CPAMonitor:
    global _instance
    if _instance is None:
        _instance = CPAMonitor()
    return _instance
