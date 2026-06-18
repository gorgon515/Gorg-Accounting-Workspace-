"""Shared SQLite schema for the Phase 11 intelligence subsystem.

Persists the cross-domain graph, detected opportunities and risks, autonomous
proposals, and the learning-engine accuracy ledger.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
DB_PATH = os.path.join(BASE_DIR, "intelligence.db")


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
        CREATE TABLE IF NOT EXISTS intel_node (
            id TEXT PRIMARY KEY, domain TEXT NOT NULL, label TEXT NOT NULL,
            attributes TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS intel_edge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL, target_id TEXT NOT NULL,
            relationship TEXT NOT NULL, weight REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity (
            id TEXT PRIMARY KEY, domain TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT, score REAL NOT NULL, expected_impact REAL,
            required_effort REAL, confidence REAL, evidence TEXT,
            status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS risk (
            id TEXT PRIMARY KEY, domain TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT, score REAL NOT NULL, severity TEXT,
            probability REAL, impact REAL, mitigation TEXT,
            status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS proposal (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
            detail TEXT, rationale TEXT, tier INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending', source TEXT,
            created_at TEXT NOT NULL, decided_at TEXT
        );
        CREATE TABLE IF NOT EXISTS learning_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL, subject_id TEXT, predicted REAL,
            actual REAL, error REAL, accuracy REAL, created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
