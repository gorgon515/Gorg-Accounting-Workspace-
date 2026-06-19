"""
Live Intelligence Monitor: poll connectors, detect events, generate alerts and signals.
"""
from __future__ import annotations
import json
import uuid
import hashlib
from typing import Optional
from .db import get_connection, init_schema


def _importance(item: dict) -> float:
    """Heuristic importance scoring from metadata."""
    score = 0.5
    title = (item.get("title") or "").lower()
    high_kw = ["urgent", "critical", "warning", "amendment", "final rule",
                "enforcement", "penalty", "deadline", "material", "restatement"]
    for kw in high_kw:
        if kw in title:
            score += 0.1
    return min(score, 1.0)


class LiveIntelligenceMonitor:
    def __init__(self):
        init_schema()

    def ingest_from_connector(self, connector_id: str, items: list[dict],
                              domain: str = "general") -> dict:
        """Ingest fetched items into the intel store, deduplicate, embed."""
        conn = get_connection()
        source_id = f"src_{connector_id}"
        # ensure source exists
        conn.execute(
            """INSERT OR IGNORE INTO intel_source(id, connector_id, name, domain)
               VALUES(?,?,?,?)""",
            (source_id, connector_id, connector_id.replace("_", " ").title(), domain),
        )
        new_count = 0
        for item in items:
            item_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{connector_id}:{item.get('title', '')}:{item.get('url', '')}:{item.get('document_number', '')}",
            ))
            existing = conn.execute("SELECT id FROM intel_item WHERE id=?", (item_id,)).fetchone()
            if existing:
                continue
            title = item.get("title") or item.get("form", "") or item.get("series_id", "")
            content = (item.get("abstract") or item.get("description") or
                       item.get("content") or json.dumps(item)[:500])
            importance = _importance({"title": title})
            conn.execute(
                """INSERT INTO intel_item
                   (id, source_id, connector_id, title, content, domain, importance,
                    url, published_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (item_id, source_id, connector_id, title[:500], content[:2000],
                 domain, importance,
                 item.get("url") or item.get("html_url", ""),
                 item.get("publication_date") or item.get("filing_date") or item.get("date", "")),
            )
            new_count += 1
        conn.execute(
            """UPDATE intel_source SET last_polled=datetime('now'),
               item_count=(SELECT COUNT(*) FROM intel_item WHERE source_id=?)
               WHERE id=?""",
            (source_id, source_id),
        )
        conn.commit()
        conn.close()
        # async-style: embed new items in the background (non-blocking attempt)
        if new_count > 0:
            try:
                self._embed_new_items(connector_id, domain)
            except Exception:
                pass
        return {"connector_id": connector_id, "new_items": new_count, "domain": domain}

    def _embed_new_items(self, connector_id: str, domain: str):
        """Embed unprocessed items into the knowledge engine."""
        from knowledge.engine import get_knowledge_engine
        ke = get_knowledge_engine()
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM intel_item WHERE connector_id=? AND processed=0 LIMIT 20",
            (connector_id,),
        ).fetchall()
        for row in rows:
            try:
                ke.ingest(
                    title=row["title"],
                    content=row["content"],
                    domain=domain,
                    kind="insight",
                    source=connector_id,
                    confidence=row["importance"],
                )
                conn.execute("UPDATE intel_item SET processed=1 WHERE id=?", (row["id"],))
            except Exception:
                pass
        conn.commit()
        conn.close()

    def list_items(self, domain: Optional[str] = None, connector_id: Optional[str] = None,
                   source: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[dict]:
        connector_id = connector_id or source
        conn = get_connection()
        clauses, params = [], []
        if domain:
            clauses.append("domain=?"); params.append(domain)
        if connector_id:
            clauses.append("connector_id=?"); params.append(connector_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM intel_item {where} ORDER BY importance DESC, ingested_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_alert(self, title: str, description: str, severity: str = "info",
                     domain: str = "general", source_item_ids: list[str] | None = None) -> dict:
        alert_id = str(uuid.uuid4())
        conn = get_connection()
        conn.execute(
            """INSERT INTO intel_alert(id, title, description, severity, domain, source_item_ids)
               VALUES(?,?,?,?,?,?)""",
            (alert_id, title, description, severity, domain,
             json.dumps(source_item_ids or [])),
        )
        conn.commit()
        conn.close()
        return self.get_alert(alert_id)

    def get_alert(self, alert_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM intel_alert WHERE id=?", (alert_id,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        try:
            d["source_item_ids"] = json.loads(d["source_item_ids"])
        except Exception:
            d["source_item_ids"] = []
        return d

    def list_alerts(self, status: str = "new", domain: Optional[str] = None,
                    limit: int = 50) -> list[dict]:
        conn = get_connection()
        clauses = ["status=?"]; params: list = [status]
        if domain:
            clauses.append("domain=?"); params.append(domain)
        rows = conn.execute(
            f"SELECT * FROM intel_alert WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["source_item_ids"] = json.loads(d["source_item_ids"])
            except Exception:
                d["source_item_ids"] = []
            result.append(d)
        return result

    def acknowledge_alert(self, alert_id: str) -> Optional[dict]:
        conn = get_connection()
        conn.execute(
            "UPDATE intel_alert SET status='acknowledged', acknowledged_at=datetime('now') WHERE id=?",
            (alert_id,),
        )
        conn.commit()
        conn.close()
        return self.get_alert(alert_id)

    def create_signal(self, signal_type: str = "general", title: str = "",
                      description: str = "", confidence: float = 0.5,
                      strength: float | None = None, impact: float = 0.5,
                      domain: str = "general", item_ids: list[str] | None = None) -> dict:
        confidence = strength if strength is not None else confidence
        sig_id = str(uuid.uuid4())
        conn = get_connection()
        conn.execute(
            """INSERT INTO intel_signal
               (id, signal_type, title, description, confidence, impact, domain, supporting_item_ids)
               VALUES(?,?,?,?,?,?,?,?)""",
            (sig_id, signal_type, title, description, confidence, impact, domain,
             json.dumps(item_ids or [])),
        )
        conn.commit()
        conn.close()
        return self._get_signal(sig_id)

    def _get_signal(self, sig_id: str) -> dict:
        conn = get_connection()
        row = conn.execute("SELECT * FROM intel_signal WHERE id=?", (sig_id,)).fetchone()
        conn.close()
        d = dict(row) if row else {}
        try:
            d["supporting_item_ids"] = json.loads(d.get("supporting_item_ids", "[]"))
        except Exception:
            d["supporting_item_ids"] = []
        return d

    def list_signals(self, domain: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = get_connection()
        if domain:
            rows = conn.execute(
                "SELECT * FROM intel_signal WHERE domain=? AND status='active' ORDER BY confidence*impact DESC LIMIT ?",
                (domain, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM intel_signal WHERE status='active' ORDER BY confidence*impact DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["supporting_item_ids"] = json.loads(d.get("supporting_item_ids", "[]"))
            except Exception:
                d["supporting_item_ids"] = []
            result.append(d)
        return result

    def add_monitor(self, name: str, domain: str = "general",
                    keywords: list[str] | None = None,
                    connectors: list[str] | None = None,
                    check_interval_hours: int = 24,
                    connector_id: str = "",
                    watch_type: str = "") -> dict:
        mon_id = str(uuid.uuid4())
        actual_connector = connector_id or (connectors[0] if connectors else "general")
        actual_watch_type = watch_type or domain
        config = {
            "domain": domain,
            "keywords": keywords or [],
            "connectors": connectors or [],
            "check_interval_hours": check_interval_hours,
        }
        conn = get_connection()
        conn.execute(
            """INSERT INTO monitor_config(id, name, connector_id, watch_type, config)
               VALUES(?,?,?,?,?)""",
            (mon_id, name, actual_connector, actual_watch_type, json.dumps(config)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM monitor_config WHERE id=?", (mon_id,)).fetchone()
        conn.close()
        d = dict(row)
        try:
            d["config"] = json.loads(d["config"])
        except Exception:
            d["config"] = {}
        return d

    def list_monitors(self, enabled: bool = True) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM monitor_config WHERE enabled=? ORDER BY name",
            (1 if enabled else 0,),
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["config"] = json.loads(d["config"])
            except Exception:
                d["config"] = {}
            result.append(d)
        return result

    def poll_connector(self, connector_id: str, domain: str = "general", **kwargs) -> dict:
        """Poll a connector and ingest results."""
        from connectors.registry import get_registry
        registry = get_registry()
        result = registry.fetch(connector_id, **kwargs)
        if result.status == "ok" and result.items:
            return self.ingest_from_connector(connector_id, result.items, domain)
        return {"connector_id": connector_id, "status": result.status,
                "error": result.error, "new_items": 0}

    def sources(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM intel_source ORDER BY last_polled DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        conn = get_connection()
        items = conn.execute("SELECT COUNT(*) FROM intel_item").fetchone()[0]
        alerts = conn.execute("SELECT COUNT(*) FROM intel_alert WHERE status='new'").fetchone()[0]
        signals = conn.execute("SELECT COUNT(*) FROM intel_signal WHERE status='active'").fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM intel_source").fetchone()[0]
        by_domain = {}
        for r in conn.execute("SELECT domain, COUNT(*) as c FROM intel_item GROUP BY domain").fetchall():
            by_domain[r[0]] = r[1]
        conn.close()
        return {
            "total_items": items, "active_alerts": alerts,
            "active_signals": signals, "sources": sources, "by_domain": by_domain,
        }


_instance: Optional[LiveIntelligenceMonitor] = None


def get_monitor() -> LiveIntelligenceMonitor:
    global _instance
    if _instance is None:
        _instance = LiveIntelligenceMonitor()
    return _instance
