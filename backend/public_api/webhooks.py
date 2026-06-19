"""WebhookManager — outbound webhook registration and signed delivery."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Optional

from .db import get_connection, now

ALLOWED_EVENTS = [
    "accounting.updated", "backup.completed", "security.alert", "sync.completed",
    "incident.created", "license.activated", "report.generated",
]


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


class WebhookManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def create(self, name: str, url: str, events: list[str], secret: Optional[str] = None,
               owner_id: Optional[str] = None) -> dict:
        webhook_id = "wh_" + uuid.uuid4().hex[:12]
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO webhook (id, name, url, secret, events, status, owner_id, created_at) "
                "VALUES (?,?,?,?,?, 'active', ?, ?)",
                (webhook_id, name, url, secret, json.dumps(events), owner_id, now()),
            )
            conn.commit()
            return self.get(webhook_id)
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
                f"SELECT * FROM webhook {where} ORDER BY created_at DESC", tuple(params)
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, webhook_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM webhook WHERE id=?", (webhook_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def update(self, webhook_id: str, **kwargs) -> Optional[dict]:
        allowed = {"name", "url", "events", "status", "secret"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if "events" in fields:
            fields["events"] = json.dumps(fields["events"])
        if not fields:
            return self.get(webhook_id)
        conn = self._conn()
        try:
            sets = ", ".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE webhook SET {sets} WHERE id=?", (*fields.values(), webhook_id))
            conn.commit()
            return self.get(webhook_id)
        finally:
            conn.close()

    def delete(self, webhook_id: str) -> bool:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM webhook_delivery WHERE webhook_id=?", (webhook_id,))
            cur = conn.execute("DELETE FROM webhook WHERE id=?", (webhook_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def deliver(self, webhook_id: str, event_type: str, payload: dict) -> dict:
        conn0 = self._conn()
        try:
            raw = conn0.execute("SELECT * FROM webhook WHERE id=?", (webhook_id,)).fetchone()
        finally:
            conn0.close()
        if not raw:
            return {"success": False, "error": "webhook not found"}
        wh = self._row(raw)
        secret = raw["secret"]
        body = json.dumps({"event": event_type, "data": payload}, separators=(",", ":")).encode()
        signature = sign_payload(body, secret) if secret else None
        # Simulated transport: a registered, active webhook delivers with 200.
        start = time.time()
        success = wh["status"] == "active" and event_type in (wh["events"] or ALLOWED_EVENTS)
        response_status = 200 if success else 422
        response_body = "OK" if success else "event not subscribed"
        duration_ms = int((time.time() - start) * 1000) + 12
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO webhook_delivery (webhook_id, event_type, payload, response_status, "
                "response_body, duration_ms, success, delivered_at) VALUES (?,?,?,?,?,?,?,?)",
                (webhook_id, event_type, body.decode(), response_status, response_body,
                 duration_ms, 1 if success else 0, now()),
            )
            if success:
                conn.execute("UPDATE webhook SET last_delivery_at=? WHERE id=?", (now(), webhook_id))
            else:
                conn.execute(
                    "UPDATE webhook SET failure_count=failure_count+1 WHERE id=?", (webhook_id,)
                )
            conn.commit()
            return {
                "success": success, "delivery_id": cur.lastrowid, "webhook_id": webhook_id,
                "event_type": event_type, "response_status": response_status,
                "signature": signature, "duration_ms": duration_ms,
            }
        finally:
            conn.close()

    def deliveries(self, webhook_id: str, limit: int = 50) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM webhook_delivery WHERE webhook_id=? ORDER BY delivered_at DESC LIMIT ?",
                (webhook_id, limit),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["success"] = bool(d["success"])
                out.append(d)
            return out
        finally:
            conn.close()

    def stats(self, webhook_id: str) -> dict:
        conn = self._conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) c FROM webhook_delivery WHERE webhook_id=?", (webhook_id,)
            ).fetchone()["c"]
            ok = conn.execute(
                "SELECT COUNT(*) c FROM webhook_delivery WHERE webhook_id=? AND success=1", (webhook_id,)
            ).fetchone()["c"]
            wh = conn.execute("SELECT last_delivery_at FROM webhook WHERE id=?", (webhook_id,)).fetchone()
            return {
                "webhook_id": webhook_id, "total": total, "successful": ok,
                "failed": total - ok,
                "last_delivery_at": wh["last_delivery_at"] if wh else None,
            }
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        d["events"] = json.loads(d["events"])
        d["has_secret"] = bool(d.get("secret"))
        d.pop("secret", None)
        return d


_instance: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    global _instance
    if _instance is None:
        _instance = WebhookManager()
    return _instance
