"""Workspaces database — SQLite schema for multi-tenant team workspaces."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
_DB_PATH = os.path.join(BASE_DIR, "workspaces.db")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(path: str = _DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS organization (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
            edition TEXT NOT NULL DEFAULT 'professional', max_seats INTEGER DEFAULT 5,
            owner_id TEXT, status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS workspace_user (
            id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organization(id),
            email TEXT NOT NULL, name TEXT, role TEXT NOT NULL DEFAULT 'member',
            status TEXT DEFAULT 'active', invited_by TEXT,
            created_at TEXT NOT NULL, last_login TEXT,
            UNIQUE(org_id, email)
        );
        CREATE TABLE IF NOT EXISTS workspace_role (
            id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organization(id),
            name TEXT NOT NULL, permissions TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auth_session (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES workspace_user(id),
            token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL, ip_address TEXT, user_agent TEXT,
            revoked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS audit_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id TEXT, user_id TEXT, action TEXT NOT NULL,
            resource TEXT, detail TEXT, ip_address TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def record_audit(conn: sqlite3.Connection, action: str, *, org_id: str | None = None,
                 user_id: str | None = None, resource: str | None = None,
                 detail: str | None = None, ip_address: str | None = None) -> None:
    conn.execute(
        "INSERT INTO audit_event (org_id, user_id, action, resource, detail, ip_address, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (org_id, user_id, action, resource, detail, ip_address, now()),
    )
    conn.commit()
