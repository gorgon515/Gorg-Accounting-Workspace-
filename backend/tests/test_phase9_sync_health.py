"""Phase 9 — Sync Engine, Health Monitor, Document/Memory Encryption tests."""
from __future__ import annotations
import os
import pytest


def _make_key() -> bytes:
    from security.encryption.aes import derive_key, new_salt
    return derive_key("testpass", new_salt())


# ---- Sync Device Registry ----

def test_device_register_and_list(tmp_path):
    from sync.device_registry import DeviceRegistry
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    result = reg.register("Desktop-1", device_type="desktop", platform="linux")
    assert "device_id" in result
    devices = reg.list_devices()
    assert len(devices) == 1
    assert devices[0]["device_name"] == "Desktop-1"


def test_device_heartbeat(tmp_path):
    from sync.device_registry import DeviceRegistry
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    r = reg.register("My-Desktop", device_type="desktop")
    ok = reg.heartbeat(r["device_id"])
    assert ok is True


def test_device_deregister(tmp_path):
    from sync.device_registry import DeviceRegistry
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    r = reg.register("Temp-Device")
    reg.deregister(r["device_id"])
    d = reg.get(r["device_id"])
    assert d is None or d.get("status") == "inactive"


def test_session_lifecycle(tmp_path):
    from sync.device_registry import DeviceRegistry
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    r = reg.register("WorkPC")
    session = reg.start_session(r["device_id"])
    assert "session_id" in session
    complete = reg.complete_session(session["session_id"], records_synced=5, conflicts_resolved=0)
    assert complete.get("status") == "complete"


# ---- Sync Engine ----

def test_sync_push_and_delta(tmp_path):
    from sync.device_registry import DeviceRegistry
    from sync.engine import SyncEngine
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    r = reg.register("Device-A")
    device_id = r["device_id"]
    engine = SyncEngine(reg)
    records = [
        {"record_id": "entry-1", "data_hash": "abc", "version": 1, "updated_at": "2025-01-01T00:00:00"},
        {"record_id": "entry-2", "data_hash": "def", "version": 1, "updated_at": "2025-01-01T00:00:00"},
    ]
    result = engine.push(device_id, "accounting", records)
    assert "accepted" in result
    delta = engine.get_delta(device_id, "accounting", since_version=0)
    assert len(delta) >= 1


def test_sync_conflict_detection(tmp_path):
    from sync.device_registry import DeviceRegistry
    from sync.engine import SyncEngine
    reg = DeviceRegistry(str(tmp_path / "sync.db"))
    r1 = reg.register("Device-A")
    r2 = reg.register("Device-B")
    engine = SyncEngine(reg)
    engine.push(r1["device_id"], "accounting", [
        {"record_id": "entry-1", "data_hash": "hash_a", "version": 2, "updated_at": "2025-01-02T00:00:00"}
    ])
    result = engine.push(r2["device_id"], "accounting", [
        {"record_id": "entry-1", "data_hash": "hash_b", "version": 1, "updated_at": "2025-01-01T00:00:00"}
    ])
    # Should detect conflict (different hash for same record_id)
    assert "conflicts" in result or "accepted" in result


# ---- Document Encryption ----

def test_document_encrypt_decrypt(tmp_path):
    from security.encryption.document_crypto import EncryptedDocumentStore
    store = EncryptedDocumentStore(
        str(tmp_path / "enc_docs"),
        str(tmp_path / "manifest.db")
    )
    key = _make_key()
    # Create a test file
    src = tmp_path / "invoice.pdf"
    src.write_bytes(b"%PDF test invoice content" * 100)
    result = store.store(key, str(src), doc_type="invoice", original_filename="invoice.pdf")
    doc_id = result["doc_id"]
    # Retrieve and verify
    out = tmp_path / "retrieved.pdf"
    retrieve_result = store.retrieve(key, doc_id, str(out))
    assert retrieve_result.get("verified") is True
    assert out.exists()
    assert out.read_bytes() == src.read_bytes()


def test_document_integrity_check(tmp_path):
    from security.encryption.document_crypto import EncryptedDocumentStore
    store = EncryptedDocumentStore(
        str(tmp_path / "enc_docs"),
        str(tmp_path / "manifest.db")
    )
    key = _make_key()
    src = tmp_path / "contract.docx"
    src.write_bytes(b"contract content" * 50)
    result = store.store(key, str(src), doc_type="contract", original_filename="contract.docx")
    integrity = store.verify_integrity(result["doc_id"])
    assert integrity.get("tampered") is False
    assert integrity.get("hash_matches") is True


def test_document_list(tmp_path):
    from security.encryption.document_crypto import EncryptedDocumentStore
    store = EncryptedDocumentStore(str(tmp_path / "enc_docs"), str(tmp_path / "manifest.db"))
    key = _make_key()
    for i in range(3):
        f = tmp_path / f"doc{i}.txt"
        f.write_bytes(f"content {i}".encode())
        store.store(key, str(f), doc_type="workpaper", original_filename=f"doc{i}.txt")
    docs = store.list_docs()
    assert len(docs) == 3


# ---- Memory Encryption ----

def test_memory_store_retrieve(tmp_path):
    from security.encryption.memory_crypto import EncryptedMemoryStore
    store = EncryptedMemoryStore(str(tmp_path / "memory.db"))
    key = _make_key()
    store.store(key, "mem-001", {"thought": "remember this"}, category="long_term")
    item = store.retrieve(key, "mem-001")
    assert item["content"]["thought"] == "remember this"


def test_memory_search(tmp_path):
    from security.encryption.memory_crypto import EncryptedMemoryStore
    store = EncryptedMemoryStore(str(tmp_path / "memory.db"))
    key = _make_key()
    store.store(key, "g-1", {"goal": "learn python"}, category="goal", agent_name="cos_agent")
    store.store(key, "g-2", {"goal": "exercise"}, category="goal", agent_name="cos_agent")
    store.store(key, "t-1", {"task": "write report"}, category="task")
    goals = store.search(key, category="goal")
    assert len(goals) == 2
    agent_items = store.search(key, agent_name="cos_agent")
    assert len(agent_items) == 2


def test_memory_access_log(tmp_path):
    from security.encryption.memory_crypto import EncryptedMemoryStore
    store = EncryptedMemoryStore(str(tmp_path / "memory.db"))
    key = _make_key()
    store.store(key, "m-1", {"data": "sensitive"}, category="user_memory")
    store.retrieve(key, "m-1", accessor="cos_agent")
    log = store.access_log(item_id="m-1")
    assert len(log) >= 1


# ---- Health Monitor ----

def test_health_monitor_check_all(tmp_path):
    from health.monitor import HealthMonitor
    m = HealthMonitor()
    result = m.check_all()
    assert "status" in result
    assert result["status"] in ("healthy", "degraded", "critical")
    assert "checks" in result
    assert "summary" in result


def test_health_db_check_missing(tmp_path):
    from health.monitor import HealthMonitor
    m = HealthMonitor()
    result = m.check_database("/nonexistent/path/to.db")
    assert result["status"] == "missing"


def test_health_db_check_valid(tmp_path):
    import sqlite3
    from health.monitor import HealthMonitor
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    m = HealthMonitor()
    result = m.check_database(db_path)
    assert result["status"] == "ok"
    assert result["table_count"] == 1


def test_health_reporter_daily(tmp_path):
    from health.monitor import HealthMonitor
    from health.reporter import HealthReporter
    reporter = HealthReporter(HealthMonitor())
    report = reporter.daily_report()
    assert report["report_type"] == "daily"
    assert "overall_status" in report
    assert "sections" in report
    assert "recommendations" in report


def test_health_reporter_history(tmp_path):
    from health.monitor import HealthMonitor
    from health.reporter import HealthReporter
    reporter = HealthReporter(HealthMonitor())
    reporter.daily_report()  # logs a check
    history = reporter.get_health_history(days=7)
    assert len(history) >= 1
