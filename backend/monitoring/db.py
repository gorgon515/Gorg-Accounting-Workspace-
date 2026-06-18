"""Shared SQLite schema for the monitoring subsystem (errors, performance, incidents)."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
DB_PATH = os.path.join(BASE_DIR, "monitoring.db")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(path: str | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS error_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT NOT NULL, message TEXT NOT NULL,
            stack_trace TEXT, component TEXT, severity TEXT NOT NULL DEFAULT 'error',
            context TEXT, resolved INTEGER DEFAULT 0, resolved_by TEXT, resolved_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS perf_sample (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL, value REAL NOT NULL, unit TEXT DEFAULT 'ms',
            component TEXT, tags TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_perf_metric ON perf_sample(metric_name, created_at);
        CREATE TABLE IF NOT EXISTS incident (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
            severity TEXT NOT NULL DEFAULT 'medium', component TEXT,
            status TEXT NOT NULL DEFAULT 'open', detected_by TEXT,
            resolution TEXT, resolved_by TEXT,
            created_at TEXT NOT NULL, resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS incident_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL REFERENCES incident(id),
            event_type TEXT NOT NULL, description TEXT, actor TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
