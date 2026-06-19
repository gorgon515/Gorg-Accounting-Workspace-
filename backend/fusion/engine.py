"""
Intelligence Fusion Engine: cross-source correlation engine.
Detects compound patterns across connectors, domains, and events.
Generates risk alerts and advisory opportunities from correlated signals.

Example:
  Fed announcement + sector weakness + company filing + portfolio exposure
  → Risk alert

  FASB update + client industry + open engagements
  → Advisory opportunity
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_DB = Path(".data/fusion.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fusion_event (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            pattern TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            confidence REAL DEFAULT 0.5,
            domains TEXT DEFAULT '[]',
            source_signals TEXT DEFAULT '[]',
            action_type TEXT DEFAULT 'alert',
            draft_action TEXT,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS fusion_rule (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            pattern TEXT NOT NULL,
            domains TEXT DEFAULT '[]',
            min_signals INTEGER DEFAULT 2,
            severity TEXT DEFAULT 'medium',
            action_type TEXT DEFAULT 'alert',
            enabled INTEGER DEFAULT 1,
            triggered_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


# Built-in fusion rules (patterns that trigger compound alerts)
_BUILT_IN_RULES = [
    {
        "id": "r_regulatory_client",
        "name": "Regulatory Change × Client Exposure",
        "description": "Tax/accounting regulation change that may affect current client engagements",
        "pattern": "regulatory+client",
        "domains": ["tax", "accounting"],
        "min_signals": 1,
        "severity": "high",
        "action_type": "advisory_opportunity",
    },
    {
        "id": "r_market_portfolio",
        "name": "Market Event × Portfolio Exposure",
        "description": "Market signal correlated with tracked portfolio positions",
        "pattern": "market+portfolio",
        "domains": ["markets", "finance"],
        "min_signals": 2,
        "severity": "high",
        "action_type": "risk_alert",
    },
    {
        "id": "r_macro_sector",
        "name": "Macro Signal × Sector Weakness",
        "description": "Federal Reserve or economic data correlated with sector performance",
        "pattern": "macro+sector",
        "domains": ["finance", "markets"],
        "min_signals": 2,
        "severity": "medium",
        "action_type": "signal",
    },
    {
        "id": "r_sec_filing_watchlist",
        "name": "SEC Filing × Watchlist Symbol",
        "description": "Material filing from a watchlisted company",
        "pattern": "filing+watchlist",
        "domains": ["markets"],
        "min_signals": 1,
        "severity": "medium",
        "action_type": "alert",
    },
    {
        "id": "r_fasb_engagement",
        "name": "FASB Update × Open Engagements",
        "description": "New accounting standard affecting industries in current client base",
        "pattern": "fasb+engagement",
        "domains": ["accounting"],
        "min_signals": 1,
        "severity": "high",
        "action_type": "advisory_opportunity",
    },
]


class FusionEngine:
    def __init__(self):
        conn = _conn()
        for rule in _BUILT_IN_RULES:
            existing = conn.execute("SELECT id FROM fusion_rule WHERE id=?", (rule["id"],)).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO fusion_rule(id, name, description, pattern, domains, min_signals,
                       severity, action_type) VALUES(?,?,?,?,?,?,?,?)""",
                    (rule["id"], rule["name"], rule["description"], rule["pattern"],
                     json.dumps(rule["domains"]), rule["min_signals"],
                     rule["severity"], rule["action_type"]),
                )
        conn.commit()
        conn.close()

    def run_fusion(self) -> list[dict]:
        """Evaluate all enabled rules against current intelligence and generate fusion events."""
        conn = _conn()
        rules = conn.execute(
            "SELECT * FROM fusion_rule WHERE enabled=1"
        ).fetchall()
        conn.close()
        events = []
        for rule in rules:
            rule_d = dict(rule)
            try:
                event = self._evaluate_rule(rule_d)
                if event:
                    events.append(event)
            except Exception:
                pass
        return events

    def _evaluate_rule(self, rule: dict) -> Optional[dict]:
        pattern = rule["pattern"]
        domains = json.loads(rule.get("domains", "[]"))
        # Pull recent intelligence items for these domains
        from live_intelligence.monitor import get_monitor
        monitor = get_monitor()
        recent_items = []
        for domain in domains:
            recent_items.extend(monitor.list_items(domain=domain, limit=10))
        if not recent_items:
            return None
        # Score the pattern match
        pattern_parts = pattern.split("+")
        matches = self._match_pattern(pattern_parts, recent_items)
        if not matches:
            return None
        title = rule["name"]
        description = self._build_description(rule, matches)
        confidence = min(0.5 + len(matches) * 0.1, 0.95)
        draft_action = self._draft_action(rule, matches)
        event = self.create_event(
            title=title, description=description,
            pattern=rule["pattern"], severity=rule["severity"],
            confidence=confidence, domains=domains,
            source_signals=[m["id"] for m in matches],
            action_type=rule["action_type"],
            draft_action=draft_action,
        )
        # update trigger count
        conn = _conn()
        conn.execute(
            "UPDATE fusion_rule SET triggered_count=triggered_count+1 WHERE id=?", (rule["id"],)
        )
        conn.commit()
        conn.close()
        return event

    def _match_pattern(self, parts: list[str], items: list[dict]) -> list[dict]:
        """Simple keyword-based pattern matching on item content."""
        PATTERN_KEYWORDS = {
            "regulatory": ["regulation", "rule", "irs", "fasb", "sec", "pcaob", "tax", "compliance"],
            "client": ["client", "engagement", "advisory", "consulting"],
            "market": ["market", "price", "equity", "stock", "sector", "etf"],
            "portfolio": ["portfolio", "holding", "position", "allocation"],
            "macro": ["gdp", "cpi", "fed", "federal reserve", "inflation", "rate", "unemployment"],
            "sector": ["sector", "industry", "technology", "finance", "healthcare", "energy"],
            "fasb": ["fasb", "gaap", "accounting standard", "asu", "asc"],
            "engagement": ["engagement", "client", "project", "advisory"],
            "filing": ["10-k", "10-q", "8-k", "filing", "form", "sec"],
            "watchlist": ["watchlist", "tracked", "monitor"],
        }
        matched = []
        for item in items:
            text = f"{item.get('title', '')} {item.get('content', '')}".lower()
            for part in parts:
                kws = PATTERN_KEYWORDS.get(part, [part])
                if any(kw in text for kw in kws):
                    matched.append(item)
                    break
        return matched[:5]

    def _build_description(self, rule: dict, matches: list[dict]) -> str:
        titles = [m.get("title", "")[:60] for m in matches[:3]]
        return (f"{rule['description']}. Correlated sources: " +
                "; ".join(f'"{t}"' for t in titles if t))

    def _draft_action(self, rule: dict, matches: list[dict]) -> str:
        action_type = rule.get("action_type", "alert")
        if action_type == "advisory_opportunity":
            return f"DRAFT: Review {rule['name']} impact on current engagements and generate advisory memo."
        elif action_type == "risk_alert":
            return f"DRAFT: Assess portfolio exposure to {rule['name']} and consider risk mitigation."
        return f"DRAFT: Review and assess {rule['name']} signals."

    def create_event(self, title: str, description: str, pattern: str,
                     severity: str = "medium", confidence: float = 0.5,
                     domains: list[str] | None = None,
                     source_signals: list[str] | None = None,
                     action_type: str = "alert",
                     draft_action: Optional[str] = None) -> dict:
        event_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO fusion_event
               (id, title, description, pattern, severity, confidence, domains,
                source_signals, action_type, draft_action)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (event_id, title, description, pattern, severity, confidence,
             json.dumps(domains or []), json.dumps(source_signals or []),
             action_type, draft_action),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM fusion_event WHERE id=?", (event_id,)).fetchone()
        conn.close()
        return self._fmt(row)

    def _fmt(self, row) -> dict:
        d = dict(row)
        for f in ("domains", "source_signals"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        return d

    def list_events(self, status: str = "new", severity: Optional[str] = None,
                    limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses = ["status=?"]; params: list = [status]
        if severity:
            clauses.append("severity=?"); params.append(severity)
        rows = conn.execute(
            f"SELECT * FROM fusion_event WHERE {' AND '.join(clauses)} ORDER BY confidence DESC, created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def acknowledge_event(self, event_id: str) -> Optional[dict]:
        conn = _conn()
        conn.execute("UPDATE fusion_event SET status='acknowledged' WHERE id=?", (event_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM fusion_event WHERE id=?", (event_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def list_rules(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM fusion_rule ORDER BY triggered_count DESC").fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["domains"] = json.loads(d["domains"])
            except Exception:
                d["domains"] = []
            result.append(d)
        return result

    def stats(self) -> dict:
        conn = _conn()
        events = conn.execute("SELECT COUNT(*) FROM fusion_event WHERE status='new'").fetchone()[0]
        total_events = conn.execute("SELECT COUNT(*) FROM fusion_event").fetchone()[0]
        rules = conn.execute("SELECT COUNT(*) FROM fusion_rule WHERE enabled=1").fetchone()[0]
        conn.close()
        return {"new_events": events, "total_events": total_events, "active_rules": rules}


_instance: Optional[FusionEngine] = None


def get_fusion_engine() -> FusionEngine:
    global _instance
    if _instance is None:
        _instance = FusionEngine()
    return _instance
