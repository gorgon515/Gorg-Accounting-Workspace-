"""HELIOS Team Workspaces & Multi-User API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateOrgRequest(BaseModel):
    name: str
    edition: str = "professional"
    owner_email: Optional[str] = None
    max_seats: int = 5


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    edition: Optional[str] = None
    max_seats: Optional[int] = None
    status: Optional[str] = None


class InviteUserRequest(BaseModel):
    org_id: str
    email: str
    name: Optional[str] = None
    role: str = "member"
    invited_by: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: str


class CustomRoleRequest(BaseModel):
    org_id: str
    name: str
    permissions: list[str]


class CreateSessionRequest(BaseModel):
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class VerifyTokenRequest(BaseModel):
    token: str


class RevokeSessionRequest(BaseModel):
    session_id: str


@router.post("/organizations")
def create_org(req: CreateOrgRequest):
    try:
        from workspaces.organizations import get_org_manager
        return get_org_manager().create(req.name, req.edition, req.owner_email, req.max_seats)
    except Exception as e:
        return {"error": str(e)}


@router.get("/organizations")
def list_orgs(status: Optional[str] = None):
    try:
        from workspaces.organizations import get_org_manager
        return {"organizations": get_org_manager().list(status)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/organizations/{org_id}")
def get_org(org_id: str):
    try:
        from workspaces.organizations import get_org_manager
        org = get_org_manager().get(org_id)
        return org or {"error": "not found"}
    except Exception as e:
        return {"error": str(e)}


@router.put("/organizations/{org_id}")
def update_org(org_id: str, req: UpdateOrgRequest):
    try:
        from workspaces.organizations import get_org_manager
        return get_org_manager().update(org_id, **req.model_dump(exclude_none=True))
    except Exception as e:
        return {"error": str(e)}


@router.delete("/organizations/{org_id}")
def delete_org(org_id: str):
    try:
        from workspaces.organizations import get_org_manager
        return {"deleted": get_org_manager().delete(org_id)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/organizations/{org_id}/stats")
def org_stats(org_id: str):
    try:
        from workspaces.organizations import get_org_manager
        return get_org_manager().stats(org_id)
    except Exception as e:
        return {"error": str(e)}


@router.post("/users/invite")
def invite_user(req: InviteUserRequest):
    try:
        from workspaces.users import get_user_manager
        return get_user_manager().invite(req.org_id, req.email, req.name, req.role, req.invited_by)
    except Exception as e:
        return {"error": str(e)}


@router.get("/organizations/{org_id}/users")
def list_users(org_id: str, status: Optional[str] = None):
    try:
        from workspaces.users import get_user_manager
        return {"users": get_user_manager().list(org_id, status)}
    except Exception as e:
        return {"error": str(e)}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, req: UpdateRoleRequest):
    try:
        from workspaces.users import get_user_manager
        return get_user_manager().update_role(user_id, req.role)
    except Exception as e:
        return {"error": str(e)}


@router.delete("/users/{user_id}")
def remove_user(user_id: str):
    try:
        from workspaces.users import get_user_manager
        return {"removed": get_user_manager().remove(user_id)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/roles")
def get_roles():
    try:
        from workspaces.roles import get_role_manager
        return {"roles": get_role_manager().get_predefined_roles()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/roles/custom")
def create_custom_role(req: CustomRoleRequest):
    try:
        from workspaces.roles import get_role_manager
        return get_role_manager().create_custom_role(req.org_id, req.name, req.permissions)
    except Exception as e:
        return {"error": str(e)}


@router.post("/auth/session")
def create_session(req: CreateSessionRequest):
    try:
        from workspaces.auth import get_workspace_auth
        return get_workspace_auth().create_session(req.user_id, req.ip_address, req.user_agent)
    except Exception as e:
        return {"error": str(e)}


@router.post("/auth/verify")
def verify_token(req: VerifyTokenRequest):
    try:
        from workspaces.auth import get_workspace_auth
        return get_workspace_auth().verify_token(req.token)
    except Exception as e:
        return {"error": str(e)}


@router.post("/auth/revoke")
def revoke_session(req: RevokeSessionRequest):
    try:
        from workspaces.auth import get_workspace_auth
        return {"revoked": get_workspace_auth().revoke_session(req.session_id)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/audit")
def audit_log(org_id: Optional[str] = None, limit: int = 100):
    try:
        from workspaces.db import get_connection
        conn = get_connection()
        try:
            if org_id:
                rows = conn.execute(
                    "SELECT * FROM audit_event WHERE org_id=? ORDER BY created_at DESC LIMIT ?",
                    (org_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit_event ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return {"events": [dict(r) for r in rows]}
        finally:
            conn.close()
    except Exception as e:
        return {"error": str(e)}
