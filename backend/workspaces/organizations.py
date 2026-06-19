"""OrganizationManager — multi-tenant organization records."""
from __future__ import annotations

import re
import uuid
from typing import Optional

from .db import get_connection, now, record_audit


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "org"


class OrganizationManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path) if self._db_path else get_connection()

    def create(self, name: str, edition: str = "professional",
               owner_email: Optional[str] = None, max_seats: int = 5) -> dict:
        org_id = "org_" + uuid.uuid4().hex[:12]
        base_slug = _slugify(name)
        conn = self._conn()
        try:
            slug = base_slug
            n = 1
            while conn.execute("SELECT 1 FROM organization WHERE slug=?", (slug,)).fetchone():
                n += 1
                slug = f"{base_slug}-{n}"
            ts = now()
            conn.execute(
                "INSERT INTO organization (id, name, slug, edition, max_seats, owner_id, status, created_at) "
                "VALUES (?,?,?,?,?,?, 'active', ?)",
                (org_id, name, slug, edition, max_seats, owner_email, ts),
            )
            conn.commit()
            record_audit(conn, "org.create", org_id=org_id, detail=name)
            return self.get(org_id)
        finally:
            conn.close()

    def get(self, org_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM organization WHERE id=?", (org_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_by_slug(self, slug: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM organization WHERE slug=?", (slug,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list(self, status: Optional[str] = None) -> list[dict]:
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM organization WHERE status=? ORDER BY created_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM organization ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update(self, org_id: str, **kwargs) -> Optional[dict]:
        allowed = {"name", "edition", "max_seats", "owner_id", "status"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return self.get(org_id)
        conn = self._conn()
        try:
            sets = ", ".join(f"{k}=?" for k in fields)
            conn.execute(
                f"UPDATE organization SET {sets}, updated_at=? WHERE id=?",
                (*fields.values(), now(), org_id),
            )
            conn.commit()
            record_audit(conn, "org.update", org_id=org_id, detail=",".join(fields))
            return self.get(org_id)
        finally:
            conn.close()

    def delete(self, org_id: str) -> bool:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM auth_session WHERE user_id IN "
                         "(SELECT id FROM workspace_user WHERE org_id=?)", (org_id,))
            conn.execute("DELETE FROM workspace_user WHERE org_id=?", (org_id,))
            conn.execute("DELETE FROM workspace_role WHERE org_id=?", (org_id,))
            cur = conn.execute("DELETE FROM organization WHERE id=?", (org_id,))
            conn.commit()
            record_audit(conn, "org.delete", org_id=org_id)
            return cur.rowcount > 0
        finally:
            conn.close()

    def stats(self, org_id: str) -> dict:
        conn = self._conn()
        try:
            org = conn.execute("SELECT * FROM organization WHERE id=?", (org_id,)).fetchone()
            total = conn.execute(
                "SELECT COUNT(*) c FROM workspace_user WHERE org_id=?", (org_id,)
            ).fetchone()["c"]
            active = conn.execute(
                "SELECT COUNT(*) c FROM workspace_user WHERE org_id=? AND status='active'", (org_id,)
            ).fetchone()["c"]
            max_seats = org["max_seats"] if org else 0
            util = round((active / max_seats) * 100, 1) if max_seats else 0.0
            return {
                "org_id": org_id,
                "user_count": total,
                "active_users": active,
                "max_seats": max_seats,
                "seat_utilization": util,
            }
        finally:
            conn.close()


_instance: Optional[OrganizationManager] = None


def get_org_manager() -> OrganizationManager:
    global _instance
    if _instance is None:
        _instance = OrganizationManager()
    return _instance
