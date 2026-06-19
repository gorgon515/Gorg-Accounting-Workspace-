from __future__ import annotations

"""Role-based access control system for HELIOS."""

from typing import Optional

ROLES = {"admin", "accountant", "analyst", "viewer", "agent_supervisor", "system"}

# All categories and actions
PERMISSION_CATEGORIES = {
    "vault": {"read", "write", "delete", "rotate", "admin"},
    "accounting": {"read", "post", "void", "close_period", "admin"},
    "documents": {"read", "write", "delete", "admin"},
    "memory": {"read", "write", "delete", "admin"},
    "execution": {"read", "execute", "approve", "admin"},
    "backup": {"read", "create", "restore", "admin"},
    "sync": {"read", "write", "admin"},
    "agents": {"read", "execute", "admin"},
    "audit": {"read", "export", "admin"},
}


class RolePermissions:
    ROLE_PERMISSIONS: dict[str, set[str]] = {
        "admin": {
            "vault:read", "vault:write", "vault:delete", "vault:rotate", "vault:admin",
            "accounting:read", "accounting:post", "accounting:void", "accounting:close_period", "accounting:admin",
            "documents:read", "documents:write", "documents:delete", "documents:admin",
            "memory:read", "memory:write", "memory:delete", "memory:admin",
            "execution:read", "execution:execute", "execution:approve", "execution:admin",
            "backup:read", "backup:create", "backup:restore", "backup:admin",
            "sync:read", "sync:write", "sync:admin",
            "agents:read", "agents:execute", "agents:admin",
            "audit:read", "audit:export", "audit:admin",
        },
        "accountant": {
            "vault:read",
            "accounting:read", "accounting:post", "accounting:void", "accounting:close_period",
            "documents:read", "documents:write",
            "memory:read",
            "execution:read", "execution:execute", "execution:approve",
            "backup:read",
            "sync:read", "sync:write",
            "agents:read",
            "audit:read",
        },
        "analyst": {
            "vault:read",
            "accounting:read",
            "documents:read",
            "memory:read",
            "execution:read",
            "backup:read",
            "sync:read",
            "agents:read",
            "audit:read",
        },
        "viewer": {
            "accounting:read",
            "documents:read",
            "execution:read",
            "audit:read",
        },
        "agent_supervisor": {
            "vault:read",
            "accounting:read",
            "documents:read", "documents:write",
            "memory:read", "memory:write",
            "execution:read", "execution:execute", "execution:approve",
            "backup:read",
            "sync:read", "sync:write",
            "agents:read", "agents:execute",
            "audit:read",
        },
        "system": {
            "vault:read", "vault:write", "vault:delete", "vault:rotate", "vault:admin",
            "accounting:read", "accounting:post", "accounting:void", "accounting:close_period", "accounting:admin",
            "documents:read", "documents:write", "documents:delete", "documents:admin",
            "memory:read", "memory:write", "memory:delete", "memory:admin",
            "execution:read", "execution:execute", "execution:approve", "execution:admin",
            "backup:read", "backup:create", "backup:restore", "backup:admin",
            "sync:read", "sync:write", "sync:admin",
            "agents:read", "agents:execute", "agents:admin",
            "audit:read", "audit:export", "audit:admin",
        },
    }

    @classmethod
    def has_permission(cls, role: str, category: str, action: str) -> bool:
        if role not in cls.ROLE_PERMISSIONS:
            return False
        return f"{category}:{action}" in cls.ROLE_PERMISSIONS[role]

    @classmethod
    def get_role_permissions(cls, role: str) -> list[str]:
        return sorted(cls.ROLE_PERMISSIONS.get(role, set()))

    @classmethod
    def validate_action(cls, role: str, category: str, action: str, raise_on_deny: bool = True) -> bool:
        allowed = cls.has_permission(role, category, action)
        if not allowed and raise_on_deny:
            raise PermissionError(f"Role '{role}' does not have permission '{category}:{action}'")
        return allowed
