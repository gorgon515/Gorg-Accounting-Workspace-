"""Security service facade — wires the vault, encrypted stores, backup/restore,
recovery, sync, compliance, and health into one lifecycle for the API layer.

The vault is the root of trust. On unlock it derives (or mints) a single 256-bit
*data key* — stored as a vault secret — that keys the encrypted memory/document
store and the sync engine. Locking tears those down. A read-only status surface
works whether locked or unlocked so the HUD always has something to show.
"""
from __future__ import annotations

from typing import Optional

from . import compliance, crypto, health
from .encrypted_store import EncryptedStore
from .vault import Vault, VaultLocked

DATA_KEY_REF = "helios:data-key"


class SecurityService:
    def __init__(self, *, vault: Optional[Vault] = None, compliance_log: Optional[compliance.ComplianceLog] = None):
        self.vault = vault or Vault()
        self.compliance = compliance_log or compliance.ComplianceLog()
        self.store: Optional[EncryptedStore] = None
        self._data_key: Optional[bytes] = None

    # ---- lifecycle ----
    def initialize(self, master_password: str) -> dict:
        out = self.vault.initialize(master_password)
        self._provision_data_key()
        self.compliance.record("vault_access", "initialize", actor="user")
        return out

    def unlock(self, master_password: str) -> dict:
        ok = self.vault.unlock(master_password)
        self.compliance.record("vault_access", "unlock" if ok else "unlock_failed", actor="user")
        if not ok:
            return {"unlocked": False}
        self._provision_data_key()
        return {"unlocked": True}

    def lock(self) -> dict:
        self.vault.lock()
        if self.store:
            self.store.close()
        self.store = None
        self._data_key = None
        self.compliance.record("vault_access", "lock", actor="user")
        return {"locked": True}

    def _provision_data_key(self):
        """Fetch the data key from the vault, minting it on first use."""
        existing = self.vault.get_secret(DATA_KEY_REF, actor="security-service")
        if existing is None:
            self._data_key = crypto.generate_key()
            import base64
            self.vault.set_secret(DATA_KEY_REF, base64.b64encode(self._data_key).decode(),
                                  category="encryption-key", actor="security-service")
        else:
            import base64
            self._data_key = base64.b64decode(existing)
        self.store = EncryptedStore(self._data_key)

    def _require_store(self) -> EncryptedStore:
        if not self.store:
            raise VaultLocked("unlock the vault before accessing encrypted data")
        return self.store

    @property
    def data_key(self) -> bytes:
        if not self._data_key:
            raise VaultLocked("vault is locked")
        return self._data_key

    # ---- encrypted memory / documents ----
    def put_memory(self, key: str, value, *, actor: str = "user") -> dict:
        self.compliance.record("memory_access", "write", actor=actor, detail={"key": key})
        return self._require_store().put("memory", key, value, actor=actor)

    def get_memory(self, key: str, *, actor: str = "user"):
        self.compliance.record("memory_access", "read", actor=actor, detail={"key": key})
        return self._require_store().get("memory", key, actor=actor)

    def put_document(self, doc_id: str, payload, *, meta: str = "", actor: str = "user") -> dict:
        self.compliance.record("document_access", "write", actor=actor, detail={"doc_id": doc_id})
        return self._require_store().put("document", doc_id, payload, meta=meta, actor=actor)

    def get_document(self, doc_id: str, *, actor: str = "user"):
        self.compliance.record("document_access", "read", actor=actor, detail={"doc_id": doc_id})
        return self._require_store().get("document", doc_id, actor=actor)

    # ---- aggregate status ----
    def status(self) -> dict:
        st = {
            "vault": self.vault.status(),
            "compliance": self.compliance.stats(),
            "health": health.system_health(),
        }
        if self.store:
            st["encrypted_store"] = self.store.stats()
        return st

    def close(self):
        if self.store:
            self.store.close()
        self.vault.close()
        self.compliance.close()
