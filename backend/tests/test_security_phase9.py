"""Phase 9 — security, vault, backup, recovery, sync, compliance, integrity tests.

These exercise *real* cryptography (AES-256-GCM + scrypt), not mocks: wrong keys
and tampered ciphertext must fail authentication, and chains/checksums must catch
corruption.
"""
import base64
import os

import pytest

from security import crypto, compliance, permissions, integrity, health
from security.vault import Vault, VaultLocked
from security.encrypted_store import EncryptedStore
from security.service import SecurityService
from backup.engine import BackupEngine
from backup.restore import RestoreEngine, RestoreError
from backup.recovery import RecoveryManager
from sync.engine import SyncEngine

from accounting_platform import db, coa, gl


# ----------------------------- crypto -----------------------------
def test_crypto_roundtrip_and_authentication():
    key = crypto.generate_key()
    assert len(key) == 32
    blob = crypto.encrypt(key, b"top secret", aad=b"ctx")
    assert crypto.decrypt(key, blob, aad=b"ctx") == b"top secret"
    # wrong key fails authentication
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(crypto.generate_key(), blob, aad=b"ctx")
    # wrong AAD fails authentication
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(key, blob, aad=b"other")


def test_crypto_tamper_detected():
    key = crypto.generate_key()
    blob = crypto.encrypt(key, b"data")
    raw = bytearray(base64.b64decode(blob))
    raw[-1] ^= 0x01  # flip a tag bit
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(key, base64.b64encode(bytes(raw)).decode())


def test_scrypt_kdf_and_password_verify():
    salt = crypto.new_salt()
    k1 = crypto.derive_key("hunter2", salt)
    k2 = crypto.derive_key("hunter2", salt)
    assert k1 == k2 and len(k1) == 32
    assert crypto.derive_key("hunter2", crypto.new_salt()) != k1  # salt matters
    check = crypto.sha256(k1)
    assert crypto.verify_password("hunter2", salt, check) is True
    assert crypto.verify_password("wrong", salt, check) is False


# ----------------------------- vault -----------------------------
def test_vault_lifecycle_and_versioning():
    v = Vault(path=":memory:")
    assert not v.initialized
    v.initialize("master-pw")
    assert v.initialized and v.unlocked
    v.set_secret("broker:apikey", "abc123", category="broker")
    assert v.get_secret("broker:apikey") == "abc123"
    # versioning on update
    out = v.set_secret("broker:apikey", "def456")
    assert out["version"] == 2
    assert v.get_secret("broker:apikey") == "def456"
    # listing never exposes plaintext
    refs = v.list_refs()
    assert refs and all("blob" not in r and "abc" not in str(r) for r in refs)
    v.close()


def test_vault_unlock_and_locked_guard():
    v = Vault(path=":memory:")
    v.initialize("correct-horse")
    v.set_secret("k", "v")
    v.lock()
    assert not v.unlocked
    with pytest.raises(VaultLocked):
        v.get_secret("k")
    assert v.unlock("wrong") is False
    assert v.unlock("correct-horse") is True
    assert v.get_secret("k") == "v"
    v.close()


def test_vault_rotate_master_rekeys_all():
    v = Vault(path=":memory:")
    v.initialize("old-pw")
    v.set_secret("a", "alpha")
    v.set_secret("b", "beta")
    v.rotate_master("old-pw", "new-pw")
    v.lock()
    assert v.unlock("old-pw") is False
    assert v.unlock("new-pw") is True
    assert v.get_secret("a") == "alpha" and v.get_secret("b") == "beta"
    v.close()


# ----------------------------- compliance -----------------------------
def test_compliance_chain_verifies_and_detects_tamper():
    log = compliance.ComplianceLog(path=":memory:")
    log.record("login", "user_login", actor="vincent")
    log.record("approval", "approve_payment", actor="vincent", detail={"amount": 100})
    log.record("execution", "post_entry", actor="system")
    assert log.verify() == {"valid": True, "events_checked": 3}
    # tamper with a record directly → chain breaks
    log.conn.execute("UPDATE compliance_event SET action='hacked' WHERE id=2")
    log.conn.commit()
    v = log.verify()
    assert v["valid"] is False and v["broken_at"] == 2
    log.close()


def test_compliance_query_and_stats():
    log = compliance.ComplianceLog(path=":memory:")
    for _ in range(3):
        log.record("vault_access", "read")
    log.record("backup", "create")
    assert len(log.query("vault_access")) == 3
    stats = log.stats()
    assert stats["total"] == 4 and stats["by_category"]["vault_access"] == 3
    assert stats["chain"]["valid"] is True
    log.close()


# ----------------------------- permissions -----------------------------
def test_permissions_agents_never_approve():
    for agent in permissions.MATRIX:
        assert permissions.can_approve(agent) is False
    with pytest.raises(permissions.PermissionDenied):
        permissions.enforce("accounting", "approve")


def test_permissions_memory_and_documents():
    assert permissions.can_access_memory("chief_of_staff", permissions.MEM_RW) is True
    assert permissions.can_access_memory("accounting", permissions.MEM_RW) is False
    assert permissions.can_access_memory("accounting", permissions.MEM_READ) is True
    assert permissions.can_access_documents("quant") is False
    permissions.enforce("accounting", "documents")  # no raise
    with pytest.raises(permissions.PermissionDenied):
        permissions.enforce("quant", "documents")


# ----------------------------- integrity -----------------------------
def _seed_ledger(tmp_path):
    conn = db.connect(str(tmp_path / "acct.db"))
    coa.seed_template(conn)
    gl.create_entry(conn, "2026-01-15",
                    [{"account": "1000", "debit": 500}, {"account": "4000", "credit": 500}],
                    memo="service revenue", post=True)
    return conn


def test_ledger_integrity_valid(tmp_path):
    conn = _seed_ledger(tmp_path)
    result = integrity.ledger_integrity(conn)
    assert result["valid"] is True
    assert result["entries_checked"] == 1
    assert result["global_balanced"] and result["trial_balance_balanced"]
    conn.close()


def test_audit_verification(tmp_path):
    conn = _seed_ledger(tmp_path)
    result = integrity.audit_verification(conn)
    assert result["valid"] is True
    assert result["posted_entries"] == 1 and not result["missing_audit"]
    conn.close()


# ----------------------------- encrypted store -----------------------------
def test_encrypted_store_roundtrip_and_no_plaintext(tmp_path):
    key = crypto.generate_key()
    store = EncryptedStore(key, path=str(tmp_path / "enc.db"))
    store.put("memory", "fact:1", {"text": "vincent prefers concise reports"})
    assert store.get("memory", "fact:1")["text"] == "vincent prefers concise reports"
    # the stored blob must not contain plaintext
    row = store.conn.execute("SELECT blob FROM enc_item WHERE key='fact:1'").fetchone()
    assert "vincent" not in row["blob"] and "concise" not in row["blob"]
    # metadata listing exposes no plaintext
    keys = store.keys("memory")
    assert keys[0]["key"] == "fact:1" and "blob" not in keys[0]
    # access log records read + write
    actions = {a["action"] for a in store.access_log()}
    assert {"read", "write"} <= actions
    store.close()


def test_encrypted_store_reencrypt(tmp_path):
    key = crypto.generate_key()
    store = EncryptedStore(key, path=str(tmp_path / "enc.db"))
    store.put("document", "d1", {"v": 1})
    new_key = crypto.generate_key()
    assert store.reencrypt(new_key) == 1
    assert store.get("document", "d1") == {"v": 1}
    store.close()


# ----------------------------- backup + restore -----------------------------
def _backup_engine(tmp_path, src_db):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_db_source("accounting", src_db)
    eng.add_source("config", b'{"setting": "value"}')
    return eng


def test_backup_create_and_verify(tmp_path):
    conn = _seed_ledger(tmp_path)
    src = conn.execute("PRAGMA database_list").fetchone()[2]
    conn.close()
    eng = _backup_engine(tmp_path, src)
    b = eng.create_backup("backup-pw", kind="full")
    assert b["members_written"] == 2
    v = eng.verify(b["backup_id"])
    assert v["valid"] is True
    # corrupt the archive → verify fails
    rec = eng.get_record(b["backup_id"])
    with open(rec["archive_path"], "ab") as f:
        f.write(b"corruption")
    assert eng.verify(b["backup_id"])["valid"] is False
    eng.close()


def test_backup_incremental_skips_unchanged(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_source("a", b"alpha")
    eng.add_source("b", b"beta")
    eng.create_backup("pw", kind="full")
    inc = eng.create_backup("pw", kind="incremental")
    assert inc["members_written"] == 0  # nothing changed
    eng.add_source("a", b"alpha-changed")
    inc2 = eng.create_backup("pw", kind="incremental")
    assert inc2["members_written"] == 1
    eng.close()


def test_backup_retention(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_source("a", b"x")
    ids = [eng.create_backup("pw", kind="full")["backup_id"] for _ in range(4)]
    out = eng.apply_retention(keep=2)
    assert len(out["removed"]) == 2
    remaining = {b["backup_id"] for b in eng.list_backups()}
    assert ids[-1] in remaining and ids[0] not in remaining
    eng.close()


def test_restore_full_rebuilds_db(tmp_path):
    conn = _seed_ledger(tmp_path)
    src = conn.execute("PRAGMA database_list").fetchone()[2]
    conn.close()
    eng = _backup_engine(tmp_path, src)
    b = eng.create_backup("backup-pw", kind="full")
    restorer = RestoreEngine(eng)
    dest = str(tmp_path / "restored_acct.db")
    out = restorer.restore(b["backup_id"], "backup-pw", {"accounting": dest})
    assert out["restored_count"] == 1
    # the restored DB has the posted entry
    rconn = db.connect(dest)
    n = rconn.execute("SELECT COUNT(*) c FROM journal_entry WHERE status='posted'").fetchone()["c"]
    assert n == 1
    rconn.close()
    eng.close()


def test_restore_wrong_password_fails(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_source("a", b"secret-bytes")
    b = eng.create_backup("right-pw", kind="full")
    restorer = RestoreEngine(eng)
    assert restorer.validate(b["backup_id"], "wrong-pw")["valid"] is False
    with pytest.raises(RestoreError):
        restorer.restore(b["backup_id"], "wrong-pw", {})
    eng.close()


def test_point_in_time_restore(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_source("a", b"v1")
    full = eng.create_backup("pw", kind="full")
    eng.add_source("a", b"v2")
    eng.create_backup("pw", kind="incremental")
    restorer = RestoreEngine(eng)
    # PIT at the full backup's timestamp → only sees v1
    rec = eng.get_record(full["backup_id"])
    pit = restorer.restore_point_in_time("pw", rec["created_at"], {})
    assert pit["base_backup"] == full["backup_id"]
    eng.close()


# ----------------------------- recovery -----------------------------
def test_recovery_plan_and_drill(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    eng.add_source("store", b"important data")
    eng.create_backup("dr-pw", kind="full")
    mgr = RecoveryManager(eng)
    plan = mgr.recovery_plan()
    assert plan["ready"] is True and plan["steps"]
    points = mgr.recovery_points()
    assert points and points[0]["recoverable"] is True
    drill = mgr.simulate_recovery("dr-pw")
    assert drill["success"] is True
    report = mgr.report("dr-pw")
    assert report["readiness"] == "ready" and report["plan_ready"] is True
    eng.close()


def test_recovery_not_ready_without_backups(tmp_path):
    eng = BackupEngine(catalog_path=str(tmp_path / "catalog.db"),
                       archive_dir=str(tmp_path / "archives"))
    mgr = RecoveryManager(eng)
    assert mgr.recovery_plan()["ready"] is False
    assert mgr.report()["readiness"] == "not_ready"
    eng.close()


# ----------------------------- sync -----------------------------
def test_sync_delta_push_pull(tmp_path):
    key = crypto.generate_key()
    s = SyncEngine(key, path=str(tmp_path / "sync.db"))
    laptop = s.register_device("laptop")["device_id"]
    phone = s.register_device("phone")["device_id"]
    s.push(laptop, [{"key": "note:1", "value": {"text": "hello"}, "base_version": 0}])
    pulled = s.pull(phone)
    assert len(pulled["changes"]) == 1
    assert pulled["changes"][0]["value"] == {"text": "hello"}
    # encrypted at rest — blob holds no plaintext
    row = s.conn.execute("SELECT blob FROM record WHERE key='note:1'").fetchone()
    assert "hello" not in row["blob"]
    # second pull on phone gets nothing new
    assert s.pull(phone)["changes"] == []
    s.close()


def test_sync_conflict_resolution(tmp_path):
    key = crypto.generate_key()
    s = SyncEngine(key, path=str(tmp_path / "sync.db"))
    a = s.register_device("a")["device_id"]
    b = s.register_device("b")["device_id"]
    r = s.push(a, [{"key": "doc", "value": "from-a", "base_version": 0}])
    v = r["applied"][0]["version"]
    # device b writes the same key with a stale base_version → conflict
    r2 = s.push(b, [{"key": "doc", "value": "from-b", "base_version": 0}])
    assert r2["conflicts"] and r2["conflicts"][0]["key"] == "doc"
    assert len(s.conflicts()) == 1
    # last-write-wins: b's value is current
    pulled = s.pull(s.register_device("c")["device_id"])
    assert pulled["changes"][-1]["value"] == "from-b"
    s.close()


# ----------------------------- service facade -----------------------------
def test_security_service_encrypted_memory(tmp_path):
    svc = SecurityService(
        vault=Vault(path=str(tmp_path / "vault.db")),
        compliance_log=compliance.ComplianceLog(path=str(tmp_path / "comp.db")))
    os.environ["HELIOS_ENCSTORE_DB"] = str(tmp_path / "enc.db")
    svc.initialize("master")
    svc.put_memory("pref", {"tone": "concise"})
    assert svc.get_memory("pref") == {"tone": "concise"}
    svc.put_document("doc:1", {"summary": "Q1 financials"}, meta="pdf")
    assert svc.get_document("doc:1") == {"summary": "Q1 financials"}
    # locking blocks encrypted access
    svc.lock()
    with pytest.raises(VaultLocked):
        svc.get_memory("pref")
    # unlock restores access with the same data key
    svc.unlock("master")
    assert svc.get_memory("pref") == {"tone": "concise"}
    status = svc.status()
    assert status["vault"]["algorithm"] == "AES-256-GCM"
    assert status["compliance"]["chain"]["valid"] is True
    svc.close()


# ----------------------------- health -----------------------------
def test_system_health_reports_stores():
    h = health.system_health()
    assert h["status"] in ("healthy", "degraded")
    assert "vault" in h["stores"] and "accounting" in h["stores"]
    assert isinstance(h["total_data_bytes"], int)
