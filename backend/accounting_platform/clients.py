"""Client & engagement management — for tax/advisory/bookkeeping firms."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .db import audit, now_iso


def add_client(conn, name: str, *, kind: str = "", email: str = "", notes: str = "", user: str = "system") -> dict:
    cur = conn.execute("INSERT INTO client (name,kind,email,notes,created_at) VALUES (?,?,?,?,?)",
                       (name, kind, email, notes, now_iso()))
    conn.commit()
    audit(conn, entity="client", entity_id=cur.lastrowid, action="create", new={"name": name}, user=user)
    conn.commit()
    return dict(conn.execute("SELECT * FROM client WHERE id=?", (cur.lastrowid,)).fetchone())


def list_clients(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM client ORDER BY name")]


def add_engagement(conn, client_id: int, name: str, *, due_date: Optional[str] = None,
                   deliverable: str = "", notes: str = "", user: str = "system") -> dict:
    cur = conn.execute(
        "INSERT INTO engagement (client_id,name,status,due_date,deliverable,notes,created_at) "
        "VALUES (?,?, 'active', ?,?,?,?)", (client_id, name, due_date, deliverable, notes, now_iso()))
    conn.commit()
    audit(conn, entity="engagement", entity_id=cur.lastrowid, action="create",
          new={"client_id": client_id, "name": name, "due": due_date}, user=user)
    conn.commit()
    return dict(conn.execute("SELECT * FROM engagement WHERE id=?", (cur.lastrowid,)).fetchone())


def list_engagements(conn, client_id: Optional[int] = None) -> list[dict]:
    sql, args = "SELECT e.*, c.name AS client FROM engagement e JOIN client c ON c.id=e.client_id", []
    if client_id:
        sql += " WHERE e.client_id=?"; args.append(client_id)
    sql += " ORDER BY COALESCE(e.due_date,'9999')"
    return [dict(r) for r in conn.execute(sql, args)]


def upcoming_deadlines(conn, days: int = 30) -> list[dict]:
    horizon = (date.today() + timedelta(days=days)).isoformat()
    return [dict(r) for r in conn.execute(
        "SELECT e.*, c.name AS client FROM engagement e JOIN client c ON c.id=e.client_id "
        "WHERE e.status='active' AND e.due_date IS NOT NULL AND e.due_date <= ? ORDER BY e.due_date", (horizon,))]
