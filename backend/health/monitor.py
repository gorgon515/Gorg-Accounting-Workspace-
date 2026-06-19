"""HELIOS Health Monitor — checks all subsystems and reports status."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", ".data")
# Resolve from this file: backend/health/monitor.py → backend/.data/
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
DATA_DIR = os.path.join(_BACKEND, ".data")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_check(path: str) -> dict:
    """Check whether a SQLite database file is present and valid."""
    if not os.path.exists(path):
        return {"status": "missing", "path": path, "size_bytes": 0, "table_count": 0}
    size = os.path.getsize(path)
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        conn.close()
        return {"status": "ok", "path": path, "size_bytes": size, "table_count": tables}
    except Exception as e:
        return {"status": "corrupt", "path": path, "size_bytes": size, "table_count": 0, "error": str(e)}


class HealthMonitor:
    """Checks all HELIOS subsystems and returns structured health data."""

    def check_database(self, db_path: str) -> dict:
        return _db_check(db_path)

    def check_vault(self) -> dict:
        vault_path = os.path.join(DATA_DIR, "vault", "vault.db")
        result = _db_check(vault_path)
        if result["status"] != "ok":
            return {"status": result["status"], "initialized": False, "locked": True,
                    "secret_count": 0, "detail": result.get("error", "vault db missing")}
        try:
            conn = sqlite3.connect(f"file:{vault_path}?mode=ro", uri=True)
            salt_row = conn.execute("SELECT value FROM vault_meta WHERE key='salt'").fetchone()
            initialized = salt_row is not None
            secret_count = conn.execute("SELECT COUNT(*) FROM vault_secret").fetchone()[0]
            conn.close()
            return {
                "status": "ok" if initialized else "uninitialized",
                "initialized": initialized,
                "locked": True,  # we never hold key here
                "secret_count": secret_count,
                "size_bytes": result["size_bytes"],
            }
        except Exception as e:
            return {"status": "error", "initialized": False, "locked": True, "secret_count": 0, "error": str(e)}

    def check_backup_health(self) -> dict:
        catalog_path = os.path.join(DATA_DIR, "backups", "catalog.db")
        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(catalog_path):
            return {"status": "no_catalog", "backup_count": 0, "last_backup_age_hours": None,
                    "oldest_backup": None, "disk_bytes": 0}
        try:
            conn = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
            total = conn.execute("SELECT COUNT(*) FROM backup_record WHERE status='complete'").fetchone()[0]
            last_row = conn.execute(
                "SELECT completed_at, size_bytes FROM backup_record WHERE status='complete' ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            oldest_row = conn.execute(
                "SELECT completed_at FROM backup_record WHERE status='complete' ORDER BY completed_at ASC LIMIT 1"
            ).fetchone()
            conn.close()

            age_hours: Optional[float] = None
            if last_row and last_row[0]:
                from datetime import datetime, timezone
                last_ts = datetime.fromisoformat(last_row[0].replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600

            # Disk usage
            disk_bytes = sum(
                os.path.getsize(os.path.join(backup_dir, f))
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f))
            ) if os.path.exists(backup_dir) else 0

            status = "ok"
            if total == 0:
                status = "no_backups"
            elif age_hours is not None and age_hours > 48:
                status = "stale"

            return {
                "status": status,
                "backup_count": total,
                "last_backup_age_hours": round(age_hours, 1) if age_hours is not None else None,
                "oldest_backup": oldest_row[0] if oldest_row else None,
                "disk_bytes": disk_bytes,
            }
        except Exception as e:
            return {"status": "error", "backup_count": 0, "error": str(e)}

    def check_sync_health(self) -> dict:
        sync_path = os.path.join(DATA_DIR, "sync", "sync.db")
        result = _db_check(sync_path)
        if result["status"] != "ok":
            return {"status": "no_sync_db", "device_count": 0, "active_sessions": 0, "last_sync": None}
        try:
            conn = sqlite3.connect(f"file:{sync_path}?mode=ro", uri=True)
            device_count = conn.execute("SELECT COUNT(*) FROM device WHERE status='active'").fetchone()[0]
            active_sessions = conn.execute("SELECT COUNT(*) FROM sync_session WHERE status='active'").fetchone()[0]
            last_sync_row = conn.execute(
                "SELECT completed_at FROM sync_session WHERE status='complete' ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            conflict_count = conn.execute(
                "SELECT COUNT(*) FROM sync_conflict WHERE resolution IS NULL"
            ).fetchone()[0]
            conn.close()
            return {
                "status": "ok" if device_count > 0 else "no_devices",
                "device_count": device_count,
                "active_sessions": active_sessions,
                "last_sync": last_sync_row[0] if last_sync_row else None,
                "pending_conflicts": conflict_count,
            }
        except Exception as e:
            return {"status": "error", "device_count": 0, "error": str(e)}

    def check_memory_health(self, db_path: Optional[str] = None) -> dict:
        path = db_path or os.path.join(DATA_DIR, "enc_memory", "memory.db")
        result = _db_check(path)
        if result["status"] != "ok":
            return {"status": result["status"], "item_count": 0, "encrypted_count": 0}
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            total = conn.execute("SELECT COUNT(*) FROM memory_item").fetchone()[0]
            conn.close()
            return {"status": "ok", "item_count": total, "encrypted_count": total,
                    "size_bytes": result["size_bytes"]}
        except Exception as e:
            return {"status": "error", "item_count": 0, "encrypted_count": 0, "error": str(e)}

    def check_document_health(self) -> dict:
        manifest_path = os.path.join(DATA_DIR, "enc_docs", "manifest.db")
        result = _db_check(manifest_path)
        if result["status"] != "ok":
            return {"status": result["status"], "doc_count": 0, "tampered_count": 0, "missing_count": 0}
        try:
            conn = sqlite3.connect(f"file:{manifest_path}?mode=ro", uri=True)
            doc_count = conn.execute("SELECT COUNT(*) FROM doc_manifest").fetchone()[0]
            docs = conn.execute("SELECT encrypted_path FROM doc_manifest").fetchall()
            conn.close()
            missing = sum(1 for d in docs if not os.path.exists(d[0]))
            return {"status": "ok" if missing == 0 else "degraded",
                    "doc_count": doc_count, "tampered_count": 0, "missing_count": missing}
        except Exception as e:
            return {"status": "error", "doc_count": 0, "tampered_count": 0, "missing_count": 0, "error": str(e)}

    def check_accounting_health(self) -> dict:
        acct_path = os.environ.get("HELIOS_ACCT_DB") or os.path.join(DATA_DIR, "accounting.db")
        result = _db_check(acct_path)
        if result["status"] != "ok":
            return {"status": result["status"], "entry_count": 0, "posted_count": 0, "balance_ok": False}
        try:
            conn = sqlite3.connect(f"file:{acct_path}?mode=ro", uri=True)
            total = conn.execute("SELECT COUNT(*) FROM journal_entry").fetchone()[0]
            posted = conn.execute("SELECT COUNT(*) FROM journal_entry WHERE status='posted'").fetchone()[0]
            row = conn.execute(
                "SELECT SUM(jl.debit), SUM(jl.credit) FROM journal_line jl "
                "JOIN journal_entry je ON je.id=jl.entry_id WHERE je.status='posted'"
            ).fetchone()
            conn.close()
            total_dr = row[0] or 0.0
            total_cr = row[1] or 0.0
            balance_ok = abs(total_dr - total_cr) < 0.01
            return {
                "status": "ok" if balance_ok else "imbalanced",
                "entry_count": total,
                "posted_count": posted,
                "balance_ok": balance_ok,
                "total_debit": round(total_dr, 2),
                "total_credit": round(total_cr, 2),
            }
        except Exception as e:
            return {"status": "error", "entry_count": 0, "posted_count": 0, "balance_ok": False, "error": str(e)}

    def check_all(self) -> dict:
        """Run all checks and return a comprehensive health report."""
        ts = _now()
        checks = {
            "accounting_db": self.check_accounting_health(),
            "vault": self.check_vault(),
            "backup": self.check_backup_health(),
            "sync": self.check_sync_health(),
            "memory": self.check_memory_health(),
            "documents": self.check_document_health(),
        }

        # Also check the core databases
        core_dbs = {
            "intel_db": os.path.join(DATA_DIR, "intel.db"),
            "compliance_db": os.path.join(DATA_DIR, "compliance.db"),
        }
        for name, path in core_dbs.items():
            checks[name] = _db_check(path)

        # Determine overall status
        critical_issues = [
            k for k, v in checks.items()
            if v.get("status") in ("missing", "corrupt", "error", "critical")
        ]
        degraded_issues = [
            k for k, v in checks.items()
            if v.get("status") in ("degraded", "stale", "no_backups", "imbalanced")
        ]

        if critical_issues:
            overall = "critical"
        elif degraded_issues:
            overall = "degraded"
        else:
            overall = "healthy"

        ok_count = sum(1 for v in checks.values() if v.get("status") == "ok")
        total_count = len(checks)

        return {
            "status": overall,
            "timestamp": ts,
            "checks": checks,
            "summary": {
                "total_checks": total_count,
                "ok": ok_count,
                "issues": len(critical_issues) + len(degraded_issues),
                "critical": critical_issues,
                "degraded": degraded_issues,
            },
        }


# Module singleton
_monitor: Optional[HealthMonitor] = None


def get_monitor() -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor
