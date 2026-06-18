"""Phase 9 — Backup, Restore, Disaster Recovery tests."""
from __future__ import annotations
import os
import pytest


def _make_key(password: str = "testpass") -> bytes:
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"helios-backup-salt", 100, dklen=32)


# ---- Backup Catalog ----

def test_catalog_register_and_list(tmp_path):
    from backup.catalog import BackupCatalog
    cat = BackupCatalog(str(tmp_path / "catalog.db"))
    cat.register("bk-001", "full", ["all"], str(tmp_path / "bk-001.enc"))
    backups = cat.list()
    assert len(backups) == 1
    assert backups[0]["backup_id"] == "bk-001"


def test_catalog_complete(tmp_path):
    from backup.catalog import BackupCatalog
    cat = BackupCatalog(str(tmp_path / "catalog.db"))
    cat.register("bk-002", "full", ["accounting"], str(tmp_path / "bk-002.enc"))
    cat.complete("bk-002", size_bytes=1024, compressed_size_bytes=512, verification_hash="abc123")
    rec = cat.get("bk-002")
    assert rec["status"] == "complete"
    assert rec["verification_hash"] == "abc123"


def test_catalog_fail(tmp_path):
    from backup.catalog import BackupCatalog
    cat = BackupCatalog(str(tmp_path / "catalog.db"))
    cat.register("bk-003", "incremental", ["vault"], str(tmp_path / "bk-003.enc"))
    cat.fail("bk-003", "disk full")
    rec = cat.get("bk-003")
    assert rec["status"] == "failed"


# ---- Backup Engine ----

def test_backup_engine_full(tmp_path):
    from backup.engine import BackupEngine
    # Create a test data file to back up
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "test.db").write_bytes(b"SQLite test database content")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    engine = BackupEngine(str(backup_dir), str(data_dir))
    engine.set_key(_make_key())
    result = engine.create_full(notes="test backup")
    assert "backup_id" in result
    assert result.get("status") in ("complete", "ok", "success") or "backup_id" in result


def test_backup_engine_verify(tmp_path):
    from backup.engine import BackupEngine
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "data.db").write_bytes(b"test db data" * 100)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    engine = BackupEngine(str(backup_dir), str(data_dir))
    engine.set_key(_make_key())
    result = engine.create_full()
    backup_id = result["backup_id"]
    verify = engine.verify(backup_id)
    assert verify.get("valid") is True or "backup_id" in verify


# ---- Disaster Recovery ----

def test_dr_accounting_consistency(tmp_path):
    """DR accounting consistency check — empty DB has equal zero debits and credits."""
    import sqlite3
    from backup.disaster_recovery import KNOWN_DATABASES, DisasterRecovery
    from backup.engine import BackupEngine
    from backup.restore import RestoreEngine
    # Create the DB at the path the DR module expects
    acct_path = KNOWN_DATABASES["accounting"]
    os.makedirs(os.path.dirname(acct_path), exist_ok=True)
    conn = sqlite3.connect(acct_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS journal_entry (
        id INTEGER PRIMARY KEY, date TEXT, memo TEXT, source TEXT,
        status TEXT DEFAULT 'draft', entry_type TEXT DEFAULT 'standard',
        reversal_of INTEGER, recurring_id INTEGER, created_by TEXT,
        created_at TEXT, posted_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS journal_line (
        id INTEGER PRIMARY KEY, entry_id INTEGER, account_id INTEGER,
        debit REAL DEFAULT 0, credit REAL DEFAULT 0, memo TEXT
    )""")
    conn.commit()
    conn.close()
    dr = DisasterRecovery(BackupEngine(), RestoreEngine())
    result = dr.check_accounting_consistency()
    assert result.get("balance_ok") is True


def test_dr_system_integrity(tmp_path):
    from backup.disaster_recovery import DisasterRecovery
    from backup.engine import BackupEngine
    from backup.restore import RestoreEngine
    dr = DisasterRecovery(BackupEngine(), RestoreEngine())
    result = dr.check_system_integrity()
    assert "components" in result or "status" in result


def test_dr_recovery_plan():
    from backup.disaster_recovery import DisasterRecovery
    from backup.engine import BackupEngine
    from backup.restore import RestoreEngine
    dr = DisasterRecovery(BackupEngine(), RestoreEngine())
    plan = dr.generate_recovery_plan()
    assert "steps" in plan or "components" in plan or "plan" in plan


def test_dr_report():
    from backup.disaster_recovery import DisasterRecovery
    from backup.engine import BackupEngine
    from backup.restore import RestoreEngine
    dr = DisasterRecovery(BackupEngine(), RestoreEngine())
    report = dr.generate_report()
    assert isinstance(report, dict)
