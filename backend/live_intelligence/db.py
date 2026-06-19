"""Shared SQLite schema for the Live Intelligence Platform."""
from __future__ import annotations
import sqlite3
from pathlib import Path

_DB = Path(".data/live_intelligence.db")


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
        CREATE TABLE IF NOT EXISTS intel_source (
            id TEXT PRIMARY KEY,
            connector_id TEXT NOT NULL,
            name TEXT NOT NULL,
            domain TEXT DEFAULT 'general',
            reliability_score REAL DEFAULT 0.7,
            last_polled TEXT,
            item_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS intel_item (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            connector_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            domain TEXT DEFAULT 'general',
            category TEXT DEFAULT 'general',
            item_type TEXT DEFAULT 'update',
            importance REAL DEFAULT 0.5,
            url TEXT DEFAULT '',
            published_at TEXT,
            ingested_at TEXT DEFAULT (datetime('now')),
            processed INTEGER DEFAULT 0,
            embed_id TEXT
        );

        CREATE TABLE IF NOT EXISTS intel_alert (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            domain TEXT DEFAULT 'general',
            source_item_ids TEXT DEFAULT '[]',
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT (datetime('now')),
            acknowledged_at TEXT
        );

        CREATE TABLE IF NOT EXISTS intel_signal (
            id TEXT PRIMARY KEY,
            signal_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            impact REAL DEFAULT 0.5,
            domain TEXT DEFAULT 'general',
            supporting_item_ids TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS monitor_config (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            connector_id TEXT NOT NULL,
            watch_type TEXT NOT NULL,
            config TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            run_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
