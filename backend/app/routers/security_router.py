"""HELIOS Security API — vault, compliance logging, agent permissions."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/security", tags=["security"])


# ---- Pydantic models ----

class VaultInitRequest(BaseModel):
    master_password: str

class VaultUnlockRequest(BaseModel):
    master_password: str

class SecretStoreRequest(BaseModel):
    name: str
    value: str
    category: str = "other"
    description: str = ""
    expires_at: Optional[str] = None

class SecretRotateRequest(BaseModel):
    new_value: str

class ComplianceQueryParams(BaseModel):
    event_type: Optional[str] = None
    actor: Optional[str] = None
    resource: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    limit: int = 100

class AgentPermissionRequest(BaseModel):
    agent_name: str
    role: str = "analyst"
    allowed_tools: list[str] = []
    denied_tools: list[str] = []
    memory_scope: str = "own"
    document_scope: str = "read"
    execution_scope: str = "none"
    max_concurrent_tasks: int = 3
    can_approve: bool = False

class PermissionCheckRequest(BaseModel):
    agent_name: str
    resource: str
    action: str


def _vault():
    from security.vault.vault import get_vault
    return get_vault()


def _logger():
    from security.compliance.logger import get_logger
    return get_logger()


def _registry():
    from security.permissions.agent_permissions import get_agent_registry
    return get_agent_registry()


# ---- Status ----

@router.get("/status")
def security_status() -> dict:
    try:
        vault = _vault()
        vs = vault.status()
    except Exception as e:
        vs = {"error": str(e)}
    try:
        log = _logger()
        log_count = log.count()
    except Exception:
        log_count = 0
    return {
        "vault": vs,
        "compliance_log_entries": log_count,
        "encryption": {"algorithm": "AES-256-GCM", "kdf": "PBKDF2-HMAC-SHA256"},
    }


# ---- Vault ----

@router.post("/vault/init")
def vault_init(req: VaultInitRequest) -> dict:
    try:
        return _vault().initialize(req.master_password)
    except ValueError as e:
        return {"error": str(e)}


@router.post("/vault/unlock")
def vault_unlock(req: VaultUnlockRequest) -> dict:
    try:
        _vault().unlock(req.master_password)
        return {"status": "unlocked"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/vault/lock")
def vault_lock() -> dict:
    _vault().lock()
    return {"status": "locked"}


@router.get("/vault/status")
def vault_status() -> dict:
    try:
        return _vault().status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/vault/secrets")
def list_secrets(category: Optional[str] = None) -> dict:
    try:
        secrets = _vault().list_secrets(category=category)
        return {"secrets": secrets}
    except PermissionError as e:
        return {"error": str(e), "locked": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/vault/secrets")
def store_secret(req: SecretStoreRequest) -> dict:
    try:
        result = _vault().store(req.name, req.value, req.category, req.description, req.expires_at)
        _logger().log("vault_access", f"store:{req.name}", category=req.category)
        return result
    except PermissionError as e:
        return {"error": str(e), "locked": True}
    except Exception as e:
        return {"error": str(e)}


@router.get("/vault/secrets/{name}")
def retrieve_secret(name: str) -> dict:
    try:
        value = _vault().retrieve(name)
        _logger().log("vault_access", f"retrieve:{name}")
        return {"name": name, "value": value}
    except KeyError as e:
        return {"error": str(e)}
    except PermissionError as e:
        return {"error": str(e), "locked": True}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/vault/secrets/{name}")
def delete_secret(name: str) -> dict:
    try:
        ok = _vault().delete(name)
        if ok:
            _logger().log("vault_access", f"delete:{name}")
        return {"deleted": ok}
    except PermissionError as e:
        return {"error": str(e), "locked": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/vault/secrets/{name}/rotate")
def rotate_secret(name: str, req: SecretRotateRequest) -> dict:
    try:
        result = _vault().rotate(name, req.new_value)
        _logger().log("vault_access", f"rotate:{name}")
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/vault/secrets/{name}/history")
def secret_history(name: str) -> dict:
    try:
        return {"history": _vault().get_history(name)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/vault/audit")
def vault_audit(limit: int = 100) -> dict:
    try:
        return {"events": _vault().audit_log(limit)}
    except Exception as e:
        return {"error": str(e)}


# ---- Compliance ----

@router.get("/compliance/log")
def compliance_log(
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    resource: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100,
) -> dict:
    try:
        log = _logger()
        entries = log.query(event_type=event_type, actor=actor, resource=resource,
                            start=start, end=end, limit=limit)
        return {"entries": entries, "total": len(entries)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/compliance/verify/{entry_id}")
def verify_entry(entry_id: int) -> dict:
    try:
        valid = _logger().verify_integrity(entry_id)
        return {"entry_id": entry_id, "valid": valid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/compliance/chain")
def verify_chain(limit: int = 1000) -> dict:
    try:
        return _logger().verify_chain(limit)
    except Exception as e:
        return {"error": str(e)}


# ---- Agent Permissions ----

@router.get("/permissions/agents")
def list_agents() -> dict:
    try:
        return {"agents": _registry().list_agents()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/permissions/agents")
def register_agent(req: AgentPermissionRequest) -> dict:
    try:
        return _registry().register(
            req.agent_name, req.role, allowed_tools=req.allowed_tools,
            denied_tools=req.denied_tools, memory_scope=req.memory_scope,
            document_scope=req.document_scope, execution_scope=req.execution_scope,
            max_concurrent_tasks=req.max_concurrent_tasks, can_approve=req.can_approve,
        )
    except Exception as e:
        return {"error": str(e)}


@router.get("/permissions/agents/{name}")
def get_agent_permissions(name: str) -> dict:
    try:
        perm = _registry().get(name)
        return perm.__dict__ if hasattr(perm, "__dict__") else perm
    except KeyError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/permissions/check")
def check_permission(req: PermissionCheckRequest) -> dict:
    try:
        return _registry().audit_check(req.agent_name, req.resource, req.action)
    except Exception as e:
        return {"error": str(e)}
