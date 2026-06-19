"""
Schema/data migration engine.
SQLite persistence at ~/.helios/migrations.db.
Migrations operate on a target sqlite db file.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "migrations.db"

_MIG_COLS = [
    "id", "name", "version", "mtype", "up_sql", "down_sql", "status",
    "checksum", "applied_at", "rolled_back_at", "created_at",
]


class MigrationEngine:

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS migration (
                id TEXT PRIMARY KEY,
                name TEXT,
                version INTEGER,
                mtype TEXT,
                up_sql TEXT,
                down_sql TEXT,
                status TEXT,
                checksum TEXT,
                applied_at REAL,
                rolled_back_at REAL,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS migration_backup (
                id TEXT PRIMARY KEY,
                migration_id TEXT,
                target_db TEXT,
                backup_path TEXT,
                created_at REAL
            );
            """)

    def _checksum(self, up_sql: str, down_sql: str) -> str:
        return hashlib.sha256(
            ((up_sql or "") + (down_sql or "")).encode("utf-8")
        ).hexdigest()

    def _row_to_dict(self, row) -> dict:
        return dict(zip(_MIG_COLS, row))

    def register_migration(self, name: str, version: int, up_sql: str,
                           down_sql: str = "", mtype: str = "schema") -> dict:
        now = time.time()
        mid = str(uuid.uuid4())
        checksum = self._checksum(up_sql, down_sql)
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO migration VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (mid, name, int(version), mtype, up_sql, down_sql, "pending",
                 checksum, None, None, now)
            )
        return self.get_migration(mid)

    def get_migration(self, mig_id: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT * FROM migration WHERE id=?", (mig_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_migrations(self, status: str = None) -> list:
        with sqlite3.connect(self._db) as c:
            if status:
                rows = c.execute(
                    "SELECT * FROM migration WHERE status=? "
                    "ORDER BY version ASC, created_at ASC", (status,)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM migration ORDER BY version ASC, created_at ASC"
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def pending(self) -> list:
        return self.list_migrations("pending")

    def applied(self) -> list:
        return self.list_migrations("applied")

    def _default_target(self) -> str:
        target = Path.home() / ".helios" / "migration_target.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        return str(target)

    def backup_before(self, mig_id: str, target_db: str = None) -> dict:
        target = target_db or self._default_target()
        now = time.time()
        backup_path = ""
        if Path(target).exists():
            backup_path = f"{target}.bak.{int(now)}"
            shutil.copy2(target, backup_path)
        bid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO migration_backup VALUES (?,?,?,?,?)",
                (bid, mig_id, target, backup_path, now)
            )
        return {"migration_id": mig_id, "backup_path": backup_path, "target_db": target}

    def apply_migration(self, mig_id: str, target_db: str = None) -> dict:
        m = self.get_migration(mig_id)
        if m is None:
            raise ValueError(f"Migration not found: {mig_id}")
        if m["status"] == "applied":
            return {"id": mig_id, "status": "applied", "skipped": True}
        target = target_db or self._default_target()
        self.backup_before(mig_id, target)
        try:
            with sqlite3.connect(target) as c:
                c.executescript(m["up_sql"] or "")
        except Exception as e:
            return {"id": mig_id, "status": "failed", "error": str(e)}
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE migration SET status=?, applied_at=? WHERE id=?",
                ("applied", now, mig_id)
            )
        integrity_ok = self.verify_integrity(target)
        return {"id": mig_id, "status": "applied",
                "integrity_ok": integrity_ok, "target_db": target}

    def rollback_migration(self, mig_id: str, target_db: str = None) -> dict:
        m = self.get_migration(mig_id)
        if m is None:
            raise ValueError(f"Migration not found: {mig_id}")
        if m["status"] != "applied":
            return {"id": mig_id, "status": m["status"], "skipped": True}
        target = target_db or self._default_target()
        if m["down_sql"]:
            with sqlite3.connect(target) as c:
                c.executescript(m["down_sql"])
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE migration SET status=?, rolled_back_at=? WHERE id=?",
                ("rolled_back", now, mig_id)
            )
        return {"id": mig_id, "status": "rolled_back", "target_db": target}

    def validate_migration(self, mig_id: str) -> dict:
        m = self.get_migration(mig_id)
        if m is None:
            raise ValueError(f"Migration not found: {mig_id}")
        issues = []
        up_sql = m["up_sql"] or ""
        if not up_sql.strip():
            issues.append("up_sql is empty")
            valid = False
        else:
            try:
                with sqlite3.connect(":memory:") as c:
                    c.executescript(up_sql)
                valid = True
            except Exception as e:
                issues.append(f"up_sql syntax error: {e}")
                valid = False
        has_rollback = bool((m["down_sql"] or "").strip())
        if not has_rollback:
            issues.append("no down_sql (rollback) provided")
        return {"id": mig_id, "valid": valid,
                "has_rollback": has_rollback, "issues": issues}

    def verify_integrity(self, target_db: str) -> bool:
        try:
            with sqlite3.connect(target_db) as c:
                row = c.execute("PRAGMA integrity_check").fetchone()
            return bool(row) and row[0] == "ok"
        except Exception:
            return False

    def current_version(self, target_db: str = None) -> int:
        applied = self.applied()
        if not applied:
            return 0
        return max(int(m["version"]) for m in applied)

    def history(self, limit: int = 50) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM migration "
                "ORDER BY COALESCE(applied_at, created_at) DESC, created_at DESC "
                "LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total = c.execute("SELECT COUNT(*) FROM migration").fetchone()[0]
            pending = c.execute(
                "SELECT COUNT(*) FROM migration WHERE status='pending'"
            ).fetchone()[0]
            applied = c.execute(
                "SELECT COUNT(*) FROM migration WHERE status='applied'"
            ).fetchone()[0]
            rolled_back = c.execute(
                "SELECT COUNT(*) FROM migration WHERE status='rolled_back'"
            ).fetchone()[0]
            failed = c.execute(
                "SELECT COUNT(*) FROM migration WHERE status='failed'"
            ).fetchone()[0]
            backups = c.execute(
                "SELECT COUNT(*) FROM migration_backup"
            ).fetchone()[0]
        return {
            "total": total,
            "pending": pending,
            "applied": applied,
            "rolled_back": rolled_back,
            "failed": failed,
            "current_version": self.current_version(),
            "backups": backups,
        }


_instance: Optional[MigrationEngine] = None


def get_migration_engine() -> MigrationEngine:
    global _instance
    if _instance is None:
        _instance = MigrationEngine()
    return _instance
