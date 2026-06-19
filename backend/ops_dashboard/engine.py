"""
Daily Operations Dashboard — the single pane of glass for running HELIOS every
day. Aggregates operational health, system/agent/connector/voice health, memory
and storage growth, knowledge growth, most-used features, recent failures, and
pending approvals. Defensive cross-module reads (every source wrapped) so the
dashboard always renders. SQLite persistence at ~/.helios/ops_dashboard.db.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "ops_dashboard.db"
_HELIOS_DIR = Path.home() / ".helios"


class OpsDashboardEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS snapshot (
                id TEXT PRIMARY KEY,
                overview_json TEXT,
                created_at REAL
            );
            """)

    # ── Individual health sections (all defensive) ─────────────────────────────
    def system_health(self) -> dict:
        try:
            from desktop.engine import get_desktop_engine
            info = get_desktop_engine().get_system_info()
            cpu = info.get("cpu_percent", 0.0)
            mem = info.get("memory_percent", 0.0)
            disk = info.get("disk_percent", 0.0)
            status = "ok"
            if cpu > 90 or mem > 90 or disk > 95:
                status = "critical"
            elif cpu > 75 or mem > 75 or disk > 85:
                status = "warning"
            return {"status": status, "cpu_percent": cpu,
                    "memory_percent": mem, "disk_percent": disk}
        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    def agent_health(self) -> dict:
        agents = []
        try:
            from voice_agents.agents import list_voice_agents
            agents = list_voice_agents()
        except Exception:
            agents = []
        reliability = []
        try:
            from stability.engine import get_stability_engine
            reliability = get_stability_engine().agent_reliability()
        except Exception:
            reliability = []
        return {"status": "ok" if agents else "idle",
                "agent_count": len(agents),
                "reliability": reliability}

    def connector_health(self) -> dict:
        connectors = []
        try:
            from connectors.registry import get_connector_registry
            reg = get_connector_registry()
            if hasattr(reg, "list_connectors"):
                connectors = reg.list_connectors()
        except Exception:
            connectors = []
        reliability = []
        try:
            from stability.engine import get_stability_engine
            reliability = get_stability_engine().connector_reliability()
        except Exception:
            reliability = []
        count = len(connectors) if isinstance(connectors, list) else 0
        return {"status": "ok" if count else "idle",
                "connector_count": count,
                "reliability": reliability}

    def voice_health(self) -> dict:
        try:
            from voice_os.engine import get_voice_os
            v = get_voice_os()
            return {"status": "ok", "mode": v.get_mode().get("mode", "idle"),
                    "stats": v.stats()}
        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    def storage_usage(self) -> dict:
        files = []
        total = 0
        try:
            if _HELIOS_DIR.exists():
                for p in _HELIOS_DIR.glob("*.db"):
                    try:
                        size = p.stat().st_size
                    except Exception:
                        size = 0
                    total += size
                    files.append({"name": p.name, "size_bytes": size})
        except Exception:
            pass
        files.sort(key=lambda f: f["size_bytes"], reverse=True)
        return {"total_bytes": total, "total_mb": round(total / 1_048_576, 3),
                "database_count": len(files), "databases": files}

    def memory_growth(self) -> dict:
        try:
            from stability.engine import get_stability_engine
            return get_stability_engine().detect_memory_leak()
        except Exception as e:
            return {"leak_suspected": False, "error": str(e)}

    def knowledge_growth(self) -> dict:
        try:
            from knowledge.engine import get_knowledge_engine
            s = get_knowledge_engine().stats()
            return {"status": "ok", "stats": s if isinstance(s, dict) else {}}
        except Exception:
            return {"status": "unavailable", "stats": {}}

    def most_used_features(self, limit: int = 10) -> list:
        # Prefer feature-flag evaluation analytics; fall back to feedback usage.
        out = []
        try:
            from feature_flags.engine import get_feature_flags
            ff = get_feature_flags()
            for f in ff.list_flags():
                a = ff.analytics(f["key"])
                out.append({"feature": f["key"], "evaluations": a.get("evaluations", 0)})
        except Exception:
            out = []
        if not out:
            try:
                from feedback.engine import get_feedback_engine
                for row in get_feedback_engine().list(kind="usage", limit=limit):
                    out.append({"feature": row.get("title", ""),
                                "evaluations": row.get("frequency", 0)})
            except Exception:
                out = []
        out.sort(key=lambda r: r["evaluations"], reverse=True)
        return out[:limit]

    def recent_failures(self, limit: int = 10) -> list:
        failures = []
        try:
            from stability.engine import get_stability_engine
            failures.extend(get_stability_engine().list_crashes(limit=limit))
        except Exception:
            pass
        try:
            from feedback.engine import get_feedback_engine
            for row in get_feedback_engine().top_failures(limit=limit):
                failures.append({"component": row.get("title", ""),
                                 "error": row.get("detail", ""),
                                 "severity": row.get("severity", "medium"),
                                 "frequency": row.get("frequency", 1)})
        except Exception:
            pass
        return failures[:limit]

    def pending_approvals(self) -> dict:
        desktop_pending = 0
        try:
            from desktop.engine import get_desktop_engine
            desktop_pending = len(get_desktop_engine().list_approvals())
        except Exception:
            desktop_pending = 0
        return {"desktop": desktop_pending, "total": desktop_pending}

    # ── Aggregate ──────────────────────────────────────────────────────────────
    def overview(self) -> dict:
        return {
            "generated_at": time.time(),
            "system_health": self.system_health(),
            "agent_health": self.agent_health(),
            "connector_health": self.connector_health(),
            "voice_health": self.voice_health(),
            "memory_growth": self.memory_growth(),
            "storage_usage": self.storage_usage(),
            "knowledge_growth": self.knowledge_growth(),
            "most_used_features": self.most_used_features(),
            "recent_failures": self.recent_failures(),
            "pending_approvals": self.pending_approvals(),
        }

    def snapshot(self) -> dict:
        ov = self.overview()
        sid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO snapshot VALUES (?,?,?)",
                      (sid, json.dumps(ov), time.time()))
        return {"id": sid, "overview": ov}

    def snapshot_history(self, limit: int = 20) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT id, created_at FROM snapshot ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"id": r[0], "created_at": r[1]} for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            snaps = c.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]
        storage = self.storage_usage()
        return {"snapshots": snaps,
                "tracked_databases": storage["database_count"],
                "storage_mb": storage["total_mb"]}


_instance: Optional[OpsDashboardEngine] = None


def get_ops_dashboard_engine() -> OpsDashboardEngine:
    global _instance
    if _instance is None:
        _instance = OpsDashboardEngine()
    return _instance
