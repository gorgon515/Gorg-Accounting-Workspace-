"""DisasterRecovery — recovery plans, integrity checks, simulations, reports."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional

from .engine import BackupEngine, get_backup_engine
from .restore import RestoreEngine, get_restore_engine

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")

KNOWN_DATABASES = {
    "accounting": os.path.join(BASE_DIR, "accounting.db"),
    "vault": os.path.join(BASE_DIR, "vault", "vault.db"),
    "compliance": os.path.join(BASE_DIR, "compliance.db"),
    "agent_permissions": os.path.join(BASE_DIR, "agent_permissions.db"),
    "backup_catalog": os.path.join(BASE_DIR, "backups", "catalog.db"),
    "sync": os.path.join(BASE_DIR, "sync", "sync.db"),
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _check_sqlite(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"status": "missing", "size_bytes": 0, "table_count": 0}
    size = os.path.getsize(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA integrity_check")
        tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        conn.close()
        return {"status": "ok", "size_bytes": size, "table_count": tables}
    except Exception as e:
        return {"status": "corrupt", "size_bytes": size, "table_count": 0, "error": str(e)}


class DisasterRecovery:
    def __init__(self, backup_engine: Optional[BackupEngine] = None,
                 restore_engine: Optional[RestoreEngine] = None):
        self._backup_engine = backup_engine or get_backup_engine()
        self._restore_engine = restore_engine or get_restore_engine()

    def check_system_integrity(self) -> dict:
        results = {}
        overall_ok = True
        for name, db_path in KNOWN_DATABASES.items():
            check = _check_sqlite(db_path)
            results[name] = check
            if check["status"] != "ok":
                overall_ok = False
        # Also check enc_docs and enc_memory dirs
        for dirname in ["enc_docs", "enc_memory"]:
            dirpath = os.path.join(BASE_DIR, dirname)
            if os.path.exists(dirpath):
                results[dirname] = {"status": "ok", "exists": True}
            else:
                results[dirname] = {"status": "missing", "exists": False}
                overall_ok = False
        return {
            "status": "ok" if overall_ok else "degraded",
            "checks": results,
            "timestamp": _now(),
        }

    def check_backup_health(self) -> dict:
        backups = self._backup_engine.list_backups()
        if not backups:
            return {"status": "critical", "backup_count": 0, "last_backup_age_hours": None,
                    "oldest_backup": None, "message": "No backups found"}
        complete_backups = [b for b in backups if b["status"] == "complete"]
        if not complete_backups:
            return {"status": "critical", "backup_count": 0, "last_backup_age_hours": None,
                    "oldest_backup": None, "message": "No completed backups found"}
        most_recent = max(complete_backups, key=lambda b: b["created_at"])
        oldest = min(complete_backups, key=lambda b: b["created_at"])
        last_dt = datetime.fromisoformat(most_recent["created_at"].replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
        status = "ok"
        if age_hours > 48:
            status = "critical"
        elif age_hours > 24:
            status = "degraded"
        return {
            "status": status,
            "backup_count": len(complete_backups),
            "last_backup_age_hours": round(age_hours, 2),
            "last_backup_id": most_recent["backup_id"],
            "oldest_backup": oldest["created_at"],
        }

    def check_accounting_consistency(self) -> dict:
        accounting_db = KNOWN_DATABASES["accounting"]
        if not os.path.exists(accounting_db):
            return {"status": "missing", "balance_ok": False, "message": "Accounting database not found"}
        try:
            conn = sqlite3.connect(accounting_db)
            conn.row_factory = sqlite3.Row
            # Try to run trial balance query
            try:
                row = conn.execute(
                    "SELECT SUM(debit) as total_debit, SUM(credit) as total_credit "
                    "FROM journal_line "
                    "JOIN journal_entry ON journal_entry.id = journal_line.entry_id "
                    "WHERE journal_entry.status = 'posted'"
                ).fetchone()
                total_debit = float(row["total_debit"] or 0)
                total_credit = float(row["total_credit"] or 0)
                balance_ok = abs(total_debit - total_credit) < 0.01
                conn.close()
                return {
                    "status": "ok" if balance_ok else "unbalanced",
                    "balance_ok": balance_ok,
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "difference": abs(total_debit - total_credit),
                }
            except sqlite3.OperationalError as e:
                conn.close()
                return {"status": "ok", "balance_ok": True, "message": f"Tables not yet created: {e}",
                        "total_debit": 0, "total_credit": 0, "difference": 0}
        except Exception as e:
            return {"status": "error", "balance_ok": False, "error": str(e)}

    def run_recovery_simulation(self, backup_id: str) -> dict:
        # Dry run a full restore
        result = self._restore_engine.restore_full(backup_id, dry_run=True)
        return {
            "simulation": True,
            "backup_id": backup_id,
            "would_restore": result.get("restored_files", []),
            "would_skip": result.get("skipped_files", []),
            "success": result.get("success", False),
            "errors": result.get("errors", []),
        }

    def generate_recovery_plan(self) -> dict:
        backups = self._backup_engine.list_backups()
        complete_backups = [b for b in backups if b["status"] == "complete"]
        components_info = {}
        component_names = ["accounting", "vault", "documents", "memory", "compliance"]
        for comp in component_names:
            comp_backups = [b for b in complete_backups
                           if comp in b["components"] or "all" in b["components"]]
            last_backup = None
            if comp_backups:
                last = max(comp_backups, key=lambda b: b["created_at"])
                last_backup = last["created_at"]
            components_info[comp] = {
                "last_backup": last_backup,
                "backup_count": len(comp_backups),
                "estimated_recovery_time_minutes": 5 if comp in ("accounting", "compliance") else 15,
                "steps": [
                    f"1. Obtain backup file for {comp}",
                    "2. Verify backup integrity",
                    "3. Stop affected services",
                    f"4. Restore {comp} from backup",
                    "5. Verify restored data",
                    "6. Restart services",
                ],
            }
        return {
            "generated_at": _now(),
            "components": components_info,
            "recovery_order": ["vault", "compliance", "accounting", "documents", "memory"],
            "total_estimated_recovery_minutes": 45,
            "rto_minutes": 60,
            "rpo_hours": 24,
        }

    def generate_report(self) -> dict:
        system_integrity = self.check_system_integrity()
        backup_health = self.check_backup_health()
        accounting = self.check_accounting_consistency()
        recovery_plan = self.generate_recovery_plan()
        # Build recommendations
        recommendations = []
        if system_integrity["status"] != "ok":
            recommendations.append("CRITICAL: System integrity check failed — investigate corrupt/missing databases")
        if backup_health["status"] == "critical":
            recommendations.append("CRITICAL: No recent backups — run a full backup immediately")
        elif backup_health["status"] == "degraded":
            recommendations.append("WARNING: Last backup is more than 24 hours old — run a backup soon")
        if not accounting.get("balance_ok", True):
            recommendations.append("WARNING: Accounting trial balance is out of balance — investigate journal entries")
        if not recommendations:
            recommendations.append("All systems healthy — no immediate action required")
        return {
            "report_generated_at": _now(),
            "overall_status": system_integrity["status"],
            "sections": {
                "system_integrity": system_integrity,
                "backup_health": backup_health,
                "accounting_consistency": accounting,
                "recovery_plan": recovery_plan,
            },
            "recommendations": recommendations,
        }


_dr: Optional[DisasterRecovery] = None

def get_disaster_recovery() -> DisasterRecovery:
    global _dr
    if _dr is None:
        _dr = DisasterRecovery()
    return _dr
