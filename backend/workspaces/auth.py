"""WorkspaceAuth — HMAC-signed session tokens for workspace users."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import get_connection, now

_SECRET = os.environ.get(
    "HELIOS_WORKSPACE_SECRET", "helios-workspace-default-secret-change-me"
).encode()


def _sign(message: bytes) -> str:
    return hmac.new(_SECRET, message, hashlib.sha256).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class WorkspaceAuth:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path) if self._db_path else get_connection()

    def create_session(self, user_id: str, ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None, ttl_hours: int = 24) -> dict:
        session_id = "ses_" + uuid.uuid4().hex[:16]
        issued = datetime.now(timezone.utc)
        expires = issued + timedelta(hours=ttl_hours)
        payload = {"user_id": user_id, "session_id": session_id,
                   "ts": issued.isoformat()}
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        sig = _sign(body.encode())
        token = f"{body}.{sig}"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO auth_session (id, user_id, token_hash, expires_at, created_at, ip_address, user_agent) "
                "VALUES (?,?,?,?,?,?,?)",
                (session_id, user_id, token_hash, expires.isoformat(), issued.isoformat(),
                 ip_address, user_agent),
            )
            conn.commit()
        finally:
            conn.close()
        return {"token": token, "session_id": session_id, "expires_at": expires.isoformat()}

    def verify_token(self, token: str) -> dict:
        try:
            body, sig = token.split(".", 1)
        except ValueError:
            return {"valid": False, "error": "malformed token"}
        if not hmac.compare_digest(sig, _sign(body.encode())):
            return {"valid": False, "error": "bad signature"}
        try:
            payload = json.loads(_b64decode(body))
        except Exception:
            return {"valid": False, "error": "bad payload"}
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM auth_session WHERE token_hash=?", (token_hash,)
            ).fetchone()
            if not row:
                return {"valid": False, "error": "session not found"}
            if row["revoked"]:
                return {"valid": False, "error": "session revoked"}
            if row["expires_at"] < now():
                return {"valid": False, "error": "session expired"}
            return {
                "valid": True,
                "session_id": row["id"],
                "user_id": row["user_id"],
                "expires_at": row["expires_at"],
            }
        finally:
            conn.close()

    def revoke_session(self, session_id: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute("UPDATE auth_session SET revoked=1 WHERE id=?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def revoke_all_user_sessions(self, user_id: str) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE auth_session SET revoked=1 WHERE user_id=? AND revoked=0", (user_id,)
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        conn = self._conn()
        try:
            cur = conn.execute("DELETE FROM auth_session WHERE expires_at < ?", (now(),))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()


_instance: Optional[WorkspaceAuth] = None


def get_workspace_auth() -> WorkspaceAuth:
    global _instance
    if _instance is None:
        _instance = WorkspaceAuth()
    return _instance
