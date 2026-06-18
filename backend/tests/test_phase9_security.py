"""Phase 9 — Vault, Encryption, Compliance, Permissions tests."""
from __future__ import annotations
import os
import pytest

# ---- Encryption primitives ----

def test_aes_encrypt_decrypt_roundtrip():
    from security.encryption.aes import encrypt, decrypt, derive_key, new_salt
    salt = new_salt()
    key = derive_key("testpassword123", salt)
    plaintext = b"HELIOS secret data"
    blob = encrypt(key, plaintext)
    assert decrypt(key, blob) == plaintext


def test_aes_str_roundtrip():
    from security.encryption.aes import encrypt_str, decrypt_str, derive_key, new_salt
    salt = new_salt()
    key = derive_key("another_password", salt)
    original = "API_KEY=abc123"
    enc = encrypt_str(key, original)
    assert decrypt_str(key, enc) == original


def test_aes_json_roundtrip():
    from security.encryption.aes import encrypt_json, decrypt_json, derive_key, new_salt
    salt = new_salt()
    key = derive_key("json_pass", salt)
    data = {"token": "xyz", "expires": "2025-12-31"}
    enc = encrypt_json(key, data)
    dec = decrypt_json(key, enc)
    assert dec == data


def test_wrong_key_fails():
    from security.encryption.aes import encrypt, decrypt, derive_key, new_salt
    from cryptography.exceptions import InvalidTag
    salt = new_salt()
    key1 = derive_key("correct_password", salt)
    key2 = derive_key("wrong_password", salt)
    blob = encrypt(key1, b"sensitive")
    with pytest.raises(Exception):  # InvalidTag or similar
        decrypt(key2, blob)


def test_sha256_hex():
    from security.encryption.aes import sha256_hex
    h = sha256_hex(b"hello")
    assert len(h) == 64
    assert h == sha256_hex(b"hello")  # deterministic


# ---- Vault ----

def test_vault_lifecycle(tmp_path):
    from security.vault.vault import Vault
    db = str(tmp_path / "vault.db")
    v = Vault(db)
    assert not v.is_initialized()
    v.initialize("masterpassword")
    assert v.is_initialized()
    assert v.is_unlocked()


def test_vault_store_retrieve(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("test_api_key", "sk-abc123", category="api_key")
    retrieved = v.retrieve("test_api_key")
    assert retrieved == "sk-abc123"


def test_vault_versioning(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("mykey", "version1", category="api_key")
    v.store("mykey", "version2", category="api_key")
    secrets = v.list_secrets()
    s = next(x for x in secrets if x["name"] == "mykey")
    assert s["version"] == 2
    history = v.get_history("mykey")
    assert len(history) >= 1


def test_vault_rotate(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("tok", "old_value", category="oauth_token")
    v.rotate("tok", "new_value")
    assert v.retrieve("tok") == "new_value"


def test_vault_delete(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("temp", "value", category="other")
    assert v.delete("temp")
    with pytest.raises(KeyError):
        v.retrieve("temp")


def test_vault_locked_blocks_access(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("secret", "value", category="api_key")
    v.lock()
    with pytest.raises(PermissionError):
        v.retrieve("secret")


def test_vault_unlock_and_access(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("k", "val", category="api_key")
    v.lock()
    v.unlock("masterpassword")
    assert v.retrieve("k") == "val"


def test_vault_audit_log(tmp_path):
    from security.vault.vault import Vault
    v = Vault(str(tmp_path / "vault.db"))
    v.initialize("masterpassword")
    v.store("x", "y", category="api_key")
    v.retrieve("x")
    log = v.audit_log()
    assert len(log) >= 3  # initialize + store + retrieve
    actions = [e["action"] for e in log]
    assert "vault_initialize" in actions


# ---- Compliance Logger ----

def test_compliance_log_basic(tmp_path):
    from security.compliance.logger import ImmutableComplianceLogger
    db = str(tmp_path / "compliance.db")
    logger = ImmutableComplianceLogger(db)
    entry_id = logger.log("login", "user_login", actor="testuser")
    assert isinstance(entry_id, int) and entry_id > 0


def test_compliance_integrity_valid(tmp_path):
    from security.compliance.logger import ImmutableComplianceLogger
    db = str(tmp_path / "compliance.db")
    logger = ImmutableComplianceLogger(db)
    eid = logger.log("vault_access", "retrieve:my_key", actor="system")
    assert logger.verify_integrity(eid) is True


def test_compliance_chain_verification(tmp_path):
    from security.compliance.logger import ImmutableComplianceLogger
    db = str(tmp_path / "compliance.db")
    logger = ImmutableComplianceLogger(db)
    for i in range(5):
        logger.log("admin_action", f"action_{i}", actor="admin")
    result = logger.verify_chain()
    assert result["total"] == 5
    assert result["invalid"] == 0


def test_compliance_query(tmp_path):
    from security.compliance.logger import ImmutableComplianceLogger
    db = str(tmp_path / "compliance.db")
    logger = ImmutableComplianceLogger(db)
    logger.log("login", "web_login", actor="alice")
    logger.log("vault_access", "retrieve:key", actor="bob")
    entries = logger.query(event_type="login")
    assert all(e["event_type"] == "login" for e in entries)


# ---- Role Permissions ----

def test_role_permissions_admin():
    from security.permissions.roles import RolePermissions
    rp = RolePermissions()
    assert rp.has_permission("admin", "vault", "admin")
    assert rp.has_permission("admin", "accounting", "close_period")


def test_role_permissions_viewer():
    from security.permissions.roles import RolePermissions
    rp = RolePermissions()
    assert rp.has_permission("viewer", "accounting", "read")
    assert not rp.has_permission("viewer", "accounting", "post")
    assert not rp.has_permission("viewer", "vault", "write")


def test_role_permissions_accountant():
    from security.permissions.roles import RolePermissions
    rp = RolePermissions()
    assert rp.has_permission("accountant", "accounting", "post")
    assert not rp.has_permission("accountant", "vault", "admin")


def test_role_validate_raises(tmp_path):
    from security.permissions.roles import RolePermissions
    rp = RolePermissions()
    with pytest.raises(PermissionError):
        rp.validate_action("viewer", "vault", "delete", raise_on_deny=True)


# ---- Agent Permissions ----

def test_agent_registry_lifecycle(tmp_path):
    from security.permissions.agent_permissions import AgentPermissionRegistry
    reg = AgentPermissionRegistry(str(tmp_path / "agents.db"))
    result = reg.register("research_agent", "analyst",
                          allowed_tools=["web_search", "quant_analyze"],
                          memory_scope="own", execution_scope="none")
    assert result["agent_name"] == "research_agent"
    perm = reg.get("research_agent")
    assert perm.role == "analyst"


def test_agent_tool_check(tmp_path):
    from security.permissions.agent_permissions import AgentPermissionRegistry
    reg = AgentPermissionRegistry(str(tmp_path / "agents.db"))
    reg.register("agent1", "analyst", allowed_tools=["search"], denied_tools=["delete"])
    assert reg.check_tool("agent1", "search") is True
    assert reg.check_tool("agent1", "delete") is False


def test_agent_audit_check(tmp_path):
    from security.permissions.agent_permissions import AgentPermissionRegistry
    reg = AgentPermissionRegistry(str(tmp_path / "agents.db"))
    reg.register("agent2", "viewer", memory_scope="own")
    result = reg.audit_check("agent2", "memory", "read")
    assert "allowed" in result
