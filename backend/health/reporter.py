"""HELIOS Health Reporter — generates daily/weekly health reports and persists history."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional

from .monitor import HealthMonitor, get_monitor, DATA_DIR

HEALTH_DB_PATH = os.path.join(DATA_DIR, "health_log.db")

HEALTH_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS health_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  overall_status TEXT NOT NULL,
  checks_ok INTEGER NOT NULL DEFAULT 0,
  checks_total INTEGER NOT NULL DEFAULT 0,
  critical_issues TEXT NOT NULL DEFAULT '[]',
  degraded_issues TEXT NOT NULL DEFAULT '[]',
  raw_result TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_log_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(HEALTH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(HEALTH_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(HEALTH_LOG_SCHEMA)
    conn.commit()
    return conn


class HealthReporter:
    """Generates structured health reports and logs check history."""

    def __init__(self, monitor: Optional[HealthMonitor] = None):
        self.monitor = monitor or get_monitor()

    def log_health_check(self, result: dict) -> None:
        """Persist a health check result to the history log."""
        conn = _get_log_conn()
        summary = result.get("summary", {})
        conn.execute(
            "INSERT INTO health_log (ts,overall_status,checks_ok,checks_total,critical_issues,degraded_issues,raw_result) VALUES (?,?,?,?,?,?,?)",
            (
                result.get("timestamp", _now()),
                result.get("status", "unknown"),
                summary.get("ok", 0),
                summary.get("total_checks", 0),
                json.dumps(summary.get("critical", [])),
                json.dumps(summary.get("degraded", [])),
                json.dumps(result),
            ),
        )
        conn.commit()
        conn.close()

    def get_health_history(self, days: int = 7) -> list[dict]:
        """Return health check history for the last N days."""
        conn = _get_log_conn()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT id,ts,overall_status,checks_ok,checks_total,critical_issues,degraded_issues FROM health_log "
            "WHERE ts >= ? ORDER BY id DESC",
            (since,),
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["critical_issues"] = json.loads(d["critical_issues"])
            d["degraded_issues"] = json.loads(d["degraded_issues"])
            result.append(d)
        return result

    def daily_report(self) -> dict:
        """Run all health checks and format as a structured daily report."""
        result = self.monitor.check_all()
        self.log_health_check(result)
        checks = result["checks"]
        summary = result["summary"]

        def _section(check: dict) -> dict:
            return {
                "status": check.get("status", "unknown"),
                "ok": check.get("status") == "ok",
                "details": {k: v for k, v in check.items() if k != "status"},
            }

        recommendations = []
        if checks.get("backup", {}).get("status") in ("no_backups", "stale"):
            recommendations.append("No recent backup found. Run a full backup immediately.")
        if checks.get("vault", {}).get("status") == "uninitialized":
            recommendations.append("HELIOS Vault is not initialized. Set a master password to protect credentials.")
        if checks.get("accounting_db", {}).get("balance_ok") is False:
            recommendations.append("Accounting ledger is imbalanced. Run a ledger consistency check.")
        if checks.get("documents", {}).get("missing_count", 0) > 0:
            recommendations.append(f"{checks['documents']['missing_count']} encrypted document(s) are missing from disk.")
        if not recommendations:
            recommendations.append("All systems nominal. No action required.")

        return {
            "report_type": "daily",
            "generated_at": _now(),
            "overall_status": result["status"],
            "sections": {
                "executive_summary": {
                    "status": result["status"],
                    "checks_passed": summary["ok"],
                    "checks_total": summary["total_checks"],
                    "critical_issues": summary["critical"],
                    "degraded_issues": summary["degraded"],
                },
                "system_health": {
                    "accounting": _section(checks.get("accounting_db", {})),
                    "intel_db": _section(checks.get("intel_db", {})),
                    "compliance_db": _section(checks.get("compliance_db", {})),
                },
                "security_health": {
                    "vault": _section(checks.get("vault", {})),
                },
                "data_health": {
                    "memory": _section(checks.get("memory", {})),
                    "documents": _section(checks.get("documents", {})),
                },
                "backup_health": {
                    "backup": _section(checks.get("backup", {})),
                },
                "sync_health": {
                    "sync": _section(checks.get("sync", {})),
                },
            },
            "recommendations": recommendations,
        }

    def weekly_report(self) -> dict:
        """Same as daily but includes 7-day trend data."""
        daily = self.daily_report()
        history = self.get_health_history(days=7)

        trend = {"healthy": 0, "degraded": 0, "critical": 0, "unknown": 0}
        for h in history:
            status = h.get("overall_status", "unknown")
            trend[status] = trend.get(status, 0) + 1

        avg_ok = (
            sum(h["checks_ok"] for h in history) / len(history)
            if history else 0
        )

        daily["report_type"] = "weekly"
        daily["trend_7d"] = {
            "check_count": len(history),
            "status_counts": trend,
            "avg_checks_ok": round(avg_ok, 1),
            "history": history[:20],
        }
        return daily
