"""APIKeyManager — issue, verify, and manage public REST API keys."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import get_connection, now


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class APIKeyManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def create(self, name: str, owner_id: Optional[str] = None,
               scopes: Optional[list[str]] = None, rate_limit_rpm: int = 60,
               expires_days: Optional[int] = None) -> dict:
        import json
        key_id = "key_" + uuid.uuid4().hex[:12]
        raw = "hk_" + secrets.token_urlsafe(32)
        prefix = raw[:11]
        expires_at = None
        if expires_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO api_key (id, name, key_hash, key_prefix, owner_id, scopes, status, "
                "rate_limit_rpm, created_at, expires_at) VALUES (?,?,?,?,?,?, 'active', ?,?,?)",
                (key_id, name, _hash(raw), prefix, owner_id, json.dumps(scopes or []),
                 rate_limit_rpm, now(), expires_at),
            )
            conn.commit()
        finally:
            conn.close()
        return {"key_id": key_id, "api_key": raw, "key_prefix": prefix, "name": name,
                "scopes": scopes or [], "rate_limit_rpm": rate_limit_rpm, "expires_at": expires_at}

    def verify(self, api_key: str) -> dict:
        import json
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_key WHERE key_hash=?", (_hash(api_key),)
            ).fetchone()
            if not row:
                return {"valid": False, "error": "unknown key"}
            if row["status"] != "active":
                return {"valid": False, "error": "key revoked"}
            if row["expires_at"] and row["expires_at"] < now():
                return {"valid": False, "error": "key expired"}
            return {
                "valid": True, "key_id": row["id"], "owner_id": row["owner_id"],
                "scopes": json.loads(row["scopes"]), "rate_limit_rpm": row["rate_limit_rpm"],
            }
        finally:
            conn.close()

    def get(self, key_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM api_key WHERE id=?", (key_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def list(self, owner_id: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        clauses, params = [], []
        if owner_id:
            clauses.append("owner_id=?")
            params.append(owner_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT * FROM api_key {where} ORDER BY created_at DESC", tuple(params)
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def revoke(self, key_id: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("UPDATE api_key SET status='revoked' WHERE id=?", (key_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def record_use(self, key_id: str) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE api_key SET last_used_at=?, use_count=use_count+1 WHERE id=?",
                (now(), key_id),
            )
            conn.commit()
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) c FROM api_key").fetchone()["c"]
            active = conn.execute(
                "SELECT COUNT(*) c FROM api_key WHERE status='active'"
            ).fetchone()["c"]
            requests = conn.execute(
                "SELECT COALESCE(SUM(use_count),0) c FROM api_key"
            ).fetchone()["c"]
            return {"total_keys": total, "active_keys": active, "total_requests": requests}
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        import json
        d = dict(r)
        d.pop("key_hash", None)
        d["scopes"] = json.loads(d["scopes"])
        return d


_instance: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    global _instance
    if _instance is None:
        _instance = APIKeyManager()
    return _instance
