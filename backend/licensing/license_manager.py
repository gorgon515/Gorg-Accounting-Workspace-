"""LicenseManager — signed license tokens with edition/seat/expiry enforcement."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .editions import get_edition

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
_DB_PATH = os.path.join(BASE_DIR, "licensing.db")
_SECRET = os.environ.get("HELIOS_LICENSE_SECRET", "helios-license-default-secret-change-me").encode()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sign(message: bytes) -> str:
    return hmac.new(_SECRET, message, hashlib.sha256).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class LicenseManager:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or _DB_PATH

    def _conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS license (
                license_id TEXT PRIMARY KEY, org_id TEXT, org_name TEXT,
                edition TEXT NOT NULL, seats INTEGER NOT NULL,
                license_key TEXT NOT NULL, issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'issued'
            );
            CREATE TABLE IF NOT EXISTS activation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_id TEXT NOT NULL, edition TEXT, machine_id TEXT,
                activated_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
            );
            """
        )
        conn.commit()
        return conn

    def generate(self, org_id: str, org_name: str, edition: str,
                 seats: int, valid_days: int = 365) -> str:
        ed = get_edition(edition)
        if seats > ed.max_seats:
            raise ValueError(f"{edition} edition allows max {ed.max_seats} seats")
        license_id = "lic_" + uuid.uuid4().hex[:16]
        issued = datetime.now(timezone.utc)
        expires = issued + timedelta(days=valid_days)
        payload = {
            "license_id": license_id, "org_id": org_id, "org_name": org_name,
            "edition": edition, "seats": seats, "features": sorted(ed.features),
            "issued_at": issued.isoformat(), "expires_at": expires.isoformat(),
        }
        body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        sig = _sign(body.encode())
        license_key = f"{body}.{sig}"
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO license (license_id, org_id, org_name, edition, seats, license_key, "
                "issued_at, expires_at, status) VALUES (?,?,?,?,?,?,?,?, 'issued')",
                (license_id, org_id, org_name, edition, seats, license_key,
                 issued.isoformat(), expires.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
        return license_key

    def verify(self, license_key: str) -> dict:
        try:
            body, sig = license_key.split(".", 1)
        except ValueError:
            return {"valid": False, "payload": None, "error": "malformed license"}
        if not hmac.compare_digest(sig, _sign(body.encode())):
            return {"valid": False, "payload": None, "error": "invalid signature"}
        try:
            payload = json.loads(_b64decode(body))
        except Exception:
            return {"valid": False, "payload": None, "error": "corrupt payload"}
        if payload.get("expires_at", "") < _now():
            return {"valid": False, "payload": payload, "error": "license expired"}
        return {"valid": True, "payload": payload, "error": None}

    def activate(self, license_key: str, machine_id: Optional[str] = None) -> dict:
        result = self.verify(license_key)
        if not result["valid"]:
            return {"success": False, "error": result["error"]}
        payload = result["payload"]
        conn = self._conn()
        try:
            # Deactivate previous active licenses (single active license per install).
            conn.execute("UPDATE license SET status='inactive' WHERE status='active'")
            conn.execute(
                "UPDATE license SET status='active' WHERE license_id=?",
                (payload["license_id"],),
            )
            # If this license was generated elsewhere, insert a record.
            exists = conn.execute(
                "SELECT 1 FROM license WHERE license_id=?", (payload["license_id"],)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO license (license_id, org_id, org_name, edition, seats, license_key, "
                    "issued_at, expires_at, status) VALUES (?,?,?,?,?,?,?,?, 'active')",
                    (payload["license_id"], payload.get("org_id"), payload.get("org_name"),
                     payload["edition"], payload["seats"], license_key,
                     payload["issued_at"], payload["expires_at"]),
                )
            conn.execute(
                "INSERT INTO activation (license_id, edition, machine_id, activated_at, status) "
                "VALUES (?,?,?,?, 'active')",
                (payload["license_id"], payload["edition"], machine_id, _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "success": True,
            "license_id": payload["license_id"],
            "edition": payload["edition"],
            "features": payload["features"],
            "expires_at": payload["expires_at"],
        }

    def get_active(self) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM license WHERE status='active' ORDER BY issued_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            v = self.verify(d["license_key"])
            d["features"] = v["payload"]["features"] if v["valid"] else []
            d["valid"] = v["valid"]
            return d
        finally:
            conn.close()

    def revoke(self, license_id: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE license SET status='revoked' WHERE license_id=?", (license_id,)
            )
            conn.execute(
                "UPDATE activation SET status='revoked' WHERE license_id=?", (license_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def list_activations(self) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM activation ORDER BY activated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


_instance: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    global _instance
    if _instance is None:
        _instance = LicenseManager()
    return _instance
