"""Shared SQLite schema for Research Automation Network."""
from __future__ import annotations
import sqlite3
from pathlib import Path

_DB = Path(".data/research.db")


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
        CREATE TABLE IF NOT EXISTS research_mission (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            team TEXT DEFAULT 'general',
            topics TEXT DEFAULT '[]',
            connectors TEXT DEFAULT '[]',
            domain TEXT DEFAULT 'general',
            schedule TEXT DEFAULT 'daily',
            status TEXT DEFAULT 'active',
            run_count INTEGER DEFAULT 0,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS research_report (
            id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            team TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            findings TEXT DEFAULT '[]',
            citations TEXT DEFAULT '[]',
            item_count INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.5,
            domain TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS research_team (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT NOT NULL,
            description TEXT DEFAULT '',
            connectors TEXT DEFAULT '[]',
            active_missions INTEGER DEFAULT 0,
            total_reports INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
