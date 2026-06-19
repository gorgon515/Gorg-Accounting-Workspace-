"""Shared SQLite schema for the Universal Connector Framework."""
from __future__ import annotations
import sqlite3
from pathlib import Path

_DB = Path(".data/connectors.db")


def get_connection() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS connector (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            version TEXT DEFAULT '1.0.0',
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'registered',
            auth_type TEXT DEFAULT 'none',
            requires_credential INTEGER DEFAULT 0,
            credential_key TEXT,
            permissions TEXT DEFAULT '[]',
            config TEXT DEFAULT '{}',
            health_status TEXT DEFAULT 'unknown',
            last_health_check TEXT,
            last_used TEXT,
            poll_interval_sec INTEGER DEFAULT 3600,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS connector_credential (
            connector_id TEXT NOT NULL,
            vault_key TEXT NOT NULL,
            masked_preview TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (connector_id)
        );

        CREATE TABLE IF NOT EXISTS connector_poll_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL,
            status TEXT NOT NULL,
            items_fetched INTEGER DEFAULT 0,
            error TEXT,
            duration_ms REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS connector_health_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL,
            healthy INTEGER NOT NULL,
            latency_ms REAL,
            error TEXT,
            checked_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
