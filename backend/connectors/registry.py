"""
Connector Registry: register, list, enable/disable, configure, and manage
the lifecycle of all HELIOS connectors.
"""
from __future__ import annotations
import json
import time
import uuid
from typing import Optional
from .db import get_connection, init_schema
from .base import BaseConnector, ConnectorMeta, FetchResult

_CONNECTORS: dict[str, type[BaseConnector]] = {}


def register_provider(cls: type[BaseConnector]):
    """Decorator that registers a connector class by its meta.id."""
    _CONNECTORS[cls.meta.id] = cls
    return cls


class ConnectorRegistry:
    def __init__(self):
        init_schema()
        # trigger provider registration before seeding DB
        try:
            from . import providers as _providers  # noqa: F401
        except Exception:
            pass
        self._seed_built_ins()

    def _seed_built_ins(self):
        """Register all known connectors into the DB if not already present."""
        conn = get_connection()
        for meta in _get_all_metas():
            existing = conn.execute("SELECT id FROM connector WHERE id=?", (meta.id,)).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO connector
                       (id, name, kind, category, version, description, auth_type,
                        requires_credential, permissions, poll_interval_sec)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (meta.id, meta.name, meta.kind, meta.category, meta.version,
                     meta.description, meta.auth_type, int(meta.requires_credential),
                     json.dumps(meta.permissions), meta.poll_interval_sec),
                )
        conn.commit()
        conn.close()

    def get(self, connector_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM connector WHERE id=?", (connector_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def list(self, category: Optional[str] = None, status: Optional[str] = None,
             kind: Optional[str] = None) -> list[dict]:
        conn = get_connection()
        clauses, params = [], []
        if category:
            clauses.append("category=?"); params.append(category)
        if status:
            clauses.append("status=?"); params.append(status)
        if kind:
            clauses.append("kind=?"); params.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM connector {where} ORDER BY category, name", params
        ).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def _fmt(self, row) -> dict:
        d = dict(row)
        for f in ("permissions", "config"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = [] if f == "permissions" else {}
        return d

    def set_status(self, connector_id: str, status: str) -> Optional[dict]:
        conn = get_connection()
        conn.execute(
            "UPDATE connector SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, connector_id),
        )
        conn.commit()
        conn.close()
        return self.get(connector_id)

    def update_config(self, connector_id: str, config: dict) -> Optional[dict]:
        conn = get_connection()
        existing = conn.execute("SELECT config FROM connector WHERE id=?", (connector_id,)).fetchone()
        if not existing:
            conn.close()
            return None
        try:
            current = json.loads(existing["config"])
        except Exception:
            current = {}
        current.update(config)
        conn.execute(
            "UPDATE connector SET config=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(current), connector_id),
        )
        conn.commit()
        conn.close()
        return self.get(connector_id)

    def store_credential(self, connector_id: str, vault_key: str, masked_preview: str = "***"):
        conn = get_connection()
        conn.execute(
            """INSERT INTO connector_credential(connector_id, vault_key, masked_preview)
               VALUES(?,?,?) ON CONFLICT(connector_id) DO UPDATE SET
               vault_key=excluded.vault_key, masked_preview=excluded.masked_preview""",
            (connector_id, vault_key, masked_preview),
        )
        conn.execute(
            "UPDATE connector SET status='active', updated_at=datetime('now') WHERE id=?",
            (connector_id,),
        )
        conn.commit()
        conn.close()

    def health_check(self, connector_id: str) -> dict:
        cls = _CONNECTORS.get(connector_id)
        if not cls:
            return {"connector_id": connector_id, "healthy": False, "error": "Provider not loaded"}
        result = cls().health_check()
        conn = get_connection()
        conn.execute(
            "INSERT INTO connector_health_log(connector_id, healthy, latency_ms, error) VALUES(?,?,?,?)",
            (connector_id, int(result["healthy"]), result.get("latency_ms"), result.get("error")),
        )
        health_status = "healthy" if result["healthy"] else "degraded"
        conn.execute(
            "UPDATE connector SET health_status=?, last_health_check=datetime('now') WHERE id=?",
            (health_status, connector_id),
        )
        conn.commit()
        conn.close()
        return {"connector_id": connector_id, **result}

    def fetch(self, connector_id: str, **kwargs) -> FetchResult:
        cls = _CONNECTORS.get(connector_id)
        if not cls:
            return FetchResult(connector_id=connector_id, status="error",
                               error="Provider class not registered")
        connector = cls()
        result = connector.fetch(**kwargs)
        conn = get_connection()
        conn.execute(
            "INSERT INTO connector_poll_log(connector_id, status, items_fetched, error, duration_ms) VALUES(?,?,?,?,?)",
            (connector_id, result.status, len(result.items), result.error, result.duration_ms),
        )
        conn.execute("UPDATE connector SET last_used=datetime('now') WHERE id=?", (connector_id,))
        conn.commit()
        conn.close()
        return result

    def poll_log(self, connector_id: str, status: str = "ok",
                 items_fetched: int = 0, error: str | None = None,
                 duration_ms: int = 0):
        """Write a manual poll log entry."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO connector_poll_log(connector_id, status, items_fetched, error, duration_ms) VALUES(?,?,?,?,?)",
            (connector_id, status, items_fetched, error, duration_ms),
        )
        conn.commit()
        conn.close()

    def poll_logs(self, connector_id: str, limit: int = 20) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM connector_poll_log WHERE connector_id=? ORDER BY created_at DESC LIMIT ?",
            (connector_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def health_log(self, connector_id: str, limit: int = 20) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM connector_health_log WHERE connector_id=? ORDER BY checked_at DESC LIMIT ?",
            (connector_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) FROM connector").fetchone()[0]
        by_status = {}
        for r in conn.execute("SELECT status, COUNT(*) as c FROM connector GROUP BY status").fetchall():
            by_status[r[0]] = r[1]
        by_cat = {}
        for r in conn.execute("SELECT category, COUNT(*) as c FROM connector GROUP BY category").fetchall():
            by_cat[r[0]] = r[1]
        healthy = conn.execute("SELECT COUNT(*) FROM connector WHERE health_status='healthy'").fetchone()[0]
        conn.close()
        return {"total": total, "by_status": by_status, "by_category": by_cat, "healthy": healthy}


def _get_all_metas() -> list[ConnectorMeta]:
    """Collect ConnectorMeta from all registered provider classes."""
    return [cls.meta for cls in _CONNECTORS.values()]


_instance: Optional[ConnectorRegistry] = None


def get_registry() -> ConnectorRegistry:
    global _instance
    if _instance is None:
        _instance = ConnectorRegistry()
    return _instance
