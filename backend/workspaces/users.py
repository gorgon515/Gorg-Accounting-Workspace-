"""UserManager — workspace user invitations and lifecycle."""
from __future__ import annotations

import uuid
from typing import Optional

from .db import get_connection, now, record_audit


class UserManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path) if self._db_path else get_connection()

    def invite(self, org_id: str, email: str, name: Optional[str] = None,
               role: str = "member", invited_by: Optional[str] = None) -> dict:
        user_id = "usr_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO workspace_user (id, org_id, email, name, role, status, invited_by, created_at) "
                "VALUES (?,?,?,?,?, 'active', ?, ?)",
                (user_id, org_id, email, name, role, invited_by, now()),
            )
            conn.commit()
            record_audit(conn, "user.invite", org_id=org_id, user_id=user_id, detail=email)
            return self.get(user_id)
        finally:
            conn.close()

    def get(self, user_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM workspace_user WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_by_email(self, org_id: str, email: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM workspace_user WHERE org_id=? AND email=?", (org_id, email)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list(self, org_id: str, status: Optional[str] = None) -> list[dict]:
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM workspace_user WHERE org_id=? AND status=? ORDER BY created_at",
                    (org_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workspace_user WHERE org_id=? ORDER BY created_at", (org_id,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_role(self, user_id: str, role: str) -> Optional[dict]:
        conn = self._conn()
        try:
            conn.execute("UPDATE workspace_user SET role=? WHERE id=?", (role, user_id))
            conn.commit()
            record_audit(conn, "user.role_change", user_id=user_id, detail=role)
            return self.get(user_id)
        finally:
            conn.close()

    def _set_status(self, user_id: str, status: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("UPDATE workspace_user SET status=? WHERE id=?", (status, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def activate(self, user_id: str) -> bool:
        return self._set_status(user_id, "active")

    def deactivate(self, user_id: str) -> bool:
        return self._set_status(user_id, "inactive")

    def remove(self, user_id: str) -> bool:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM auth_session WHERE user_id=?", (user_id,))
            cur = conn.execute("DELETE FROM workspace_user WHERE id=?", (user_id,))
            conn.commit()
            record_audit(conn, "user.remove", user_id=user_id)
            return cur.rowcount > 0
        finally:
            conn.close()

    def record_login(self, user_id: str) -> None:
        conn = self._conn()
        try:
            conn.execute("UPDATE workspace_user SET last_login=? WHERE id=?", (now(), user_id))
            conn.commit()
        finally:
            conn.close()


_instance: Optional[UserManager] = None


def get_user_manager() -> UserManager:
    global _instance
    if _instance is None:
        _instance = UserManager()
    return _instance
