"""RoleManager — predefined and custom workspace roles with permission sets."""
from __future__ import annotations

import json
import uuid
from typing import Optional

from .db import get_connection, now

ALL_PERMISSIONS = [
    "accounting:read", "accounting:write", "vault:read", "vault:write",
    "security:admin", "reports:read", "reports:export", "settings:manage",
    "users:manage", "plugins:install", "api:manage", "audit:read",
]

PREDEFINED_ROLES: dict[str, set[str]] = {
    "owner": set(ALL_PERMISSIONS),
    "admin": {
        "accounting:read", "accounting:write", "vault:read", "vault:write",
        "reports:read", "reports:export", "settings:manage", "users:manage",
        "plugins:install", "api:manage", "audit:read",
    },
    "manager": {
        "accounting:read", "accounting:write", "vault:read", "reports:read",
        "reports:export", "users:manage", "audit:read",
    },
    "member": {
        "accounting:read", "accounting:write", "vault:read", "reports:read",
    },
    "viewer": {
        "accounting:read", "reports:read",
    },
    "auditor": {
        "accounting:read", "reports:read", "reports:export", "audit:read",
    },
}


class RoleManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path) if self._db_path else get_connection()

    def get_predefined_roles(self) -> list[dict]:
        return [
            {"name": name, "permissions": sorted(perms), "predefined": True}
            for name, perms in PREDEFINED_ROLES.items()
        ]

    def create_custom_role(self, org_id: str, name: str, permissions: list[str]) -> dict:
        invalid = [p for p in permissions if p not in ALL_PERMISSIONS]
        if invalid:
            raise ValueError(f"Unknown permissions: {invalid}")
        role_id = "role_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO workspace_role (id, org_id, name, permissions, created_at) VALUES (?,?,?,?,?)",
                (role_id, org_id, name, json.dumps(permissions), now()),
            )
            conn.commit()
            return {"id": role_id, "org_id": org_id, "name": name,
                    "permissions": permissions, "predefined": False}
        finally:
            conn.close()

    def list_custom_roles(self, org_id: str) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM workspace_role WHERE org_id=? ORDER BY created_at", (org_id,)
            ).fetchall()
            return [
                {"id": r["id"], "org_id": r["org_id"], "name": r["name"],
                 "permissions": json.loads(r["permissions"]), "predefined": False}
                for r in rows
            ]
        finally:
            conn.close()

    def get_role_permissions(self, role_name: str) -> set[str]:
        return set(PREDEFINED_ROLES.get(role_name, set()))

    def has_permission(self, role_name: str, permission: str) -> bool:
        return permission in PREDEFINED_ROLES.get(role_name, set())


_instance: Optional[RoleManager] = None


def get_role_manager() -> RoleManager:
    global _instance
    if _instance is None:
        _instance = RoleManager()
    return _instance
