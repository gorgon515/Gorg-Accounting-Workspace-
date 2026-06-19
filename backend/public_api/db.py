"""Shared SQLite schema for the public API subsystem (keys + webhooks)."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
DB_PATH = os.path.join(BASE_DIR, "public_api.db")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(path: str | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS api_key (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE, key_prefix TEXT NOT NULL,
            owner_id TEXT, scopes TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active', rate_limit_rpm INTEGER DEFAULT 60,
            created_at TEXT NOT NULL, expires_at TEXT, last_used_at TEXT, use_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS webhook (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
            secret TEXT, events TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active', owner_id TEXT,
            created_at TEXT NOT NULL, last_delivery_at TEXT, failure_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS webhook_delivery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id TEXT NOT NULL REFERENCES webhook(id),
            event_type TEXT NOT NULL, payload TEXT NOT NULL,
            response_status INTEGER, response_body TEXT, duration_ms INTEGER,
            success INTEGER DEFAULT 0, delivered_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
