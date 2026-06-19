"""Phase 10 — Workspaces, roles, and auth tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def org_mgr(tmp_path):
    from workspaces.organizations import OrganizationManager
    return OrganizationManager(str(tmp_path / "ws.db"))


@pytest.fixture
def user_mgr(tmp_path):
    from workspaces.users import UserManager
    return UserManager(str(tmp_path / "ws.db"))


def test_org_create_and_list(org_mgr):
    org = org_mgr.create("Acme CPA Firm", edition="firm", owner_email="a@b.com", max_seats=10)
    assert org["edition"] == "firm"
    orgs = org_mgr.list()
    assert any(o["id"] == org["id"] for o in orgs)


def test_org_get_by_slug(org_mgr):
    org = org_mgr.create("Gregorio & Co")
    fetched = org_mgr.get_by_slug(org["slug"])
    assert fetched is not None
    assert fetched["id"] == org["id"]
    assert "&" not in org["slug"]


def test_org_stats(org_mgr, tmp_path):
    from workspaces.users import UserManager
    org = org_mgr.create("Stat Firm", max_seats=4)
    um = UserManager(str(tmp_path / "ws.db"))
    um.invite(org["id"], "u1@x.com")
    um.invite(org["id"], "u2@x.com")
    stats = org_mgr.stats(org["id"])
    assert stats["user_count"] == 2
    assert stats["active_users"] == 2
    assert stats["seat_utilization"] == 50.0


def test_user_invite_and_list(org_mgr, user_mgr):
    org = org_mgr.create("Invite Firm")
    user_mgr.invite(org["id"], "new@user.com", name="New User", role="member")
    users = user_mgr.list(org["id"])
    assert len(users) == 1
    assert users[0]["email"] == "new@user.com"


def test_user_role_update(org_mgr, user_mgr):
    org = org_mgr.create("Role Firm")
    u = user_mgr.invite(org["id"], "x@y.com", role="member")
    updated = user_mgr.update_role(u["id"], "admin")
    assert updated["role"] == "admin"


def test_role_permissions():
    from workspaces.roles import get_role_manager
    rm = get_role_manager()
    owner = rm.get_role_permissions("owner")
    viewer = rm.get_role_permissions("viewer")
    assert len(owner) > len(viewer)
    assert rm.has_permission("owner", "security:admin")
    assert not rm.has_permission("viewer", "security:admin")


def test_auth_session_create_verify(org_mgr, user_mgr, tmp_path):
    from workspaces.auth import WorkspaceAuth
    org = org_mgr.create("Auth Firm")
    u = user_mgr.invite(org["id"], "auth@user.com")
    auth = WorkspaceAuth(str(tmp_path / "ws.db"))
    sess = auth.create_session(u["id"], ip_address="127.0.0.1")
    assert "token" in sess
    result = auth.verify_token(sess["token"])
    assert result["valid"] is True
    assert result["user_id"] == u["id"]


def test_auth_token_revoke(org_mgr, user_mgr, tmp_path):
    from workspaces.auth import WorkspaceAuth
    org = org_mgr.create("Revoke Firm")
    u = user_mgr.invite(org["id"], "rev@user.com")
    auth = WorkspaceAuth(str(tmp_path / "ws.db"))
    sess = auth.create_session(u["id"])
    assert auth.revoke_session(sess["session_id"]) is True
    result = auth.verify_token(sess["token"])
    assert result["valid"] is False


def test_auth_tampered_token(tmp_path):
    from workspaces.auth import WorkspaceAuth
    auth = WorkspaceAuth(str(tmp_path / "ws.db"))
    result = auth.verify_token("garbage.signature")
    assert result["valid"] is False


def test_workspace_auth_cleanup(org_mgr, user_mgr, tmp_path):
    from workspaces.auth import WorkspaceAuth
    org = org_mgr.create("Cleanup Firm")
    u = user_mgr.invite(org["id"], "c@user.com")
    auth = WorkspaceAuth(str(tmp_path / "ws.db"))
    auth.create_session(u["id"], ttl_hours=-1)  # already expired
    removed = auth.cleanup_expired()
    assert removed >= 1
