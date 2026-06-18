"""Shared SQLite schema for the Knowledge Engine."""
import sqlite3
from pathlib import Path

_DB_PATH = Path(".data/knowledge.db")


def get_connection() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge_item (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            domain TEXT NOT NULL DEFAULT 'general',
            kind TEXT NOT NULL DEFAULT 'document',
            source TEXT DEFAULT '',
            author TEXT DEFAULT '',
            confidence REAL DEFAULT 1.0,
            authority REAL DEFAULT 0.5,
            freshness REAL DEFAULT 1.0,
            completeness REAL DEFAULT 1.0,
            quality_score REAL DEFAULT 0.5,
            version INTEGER DEFAULT 1,
            parent_id TEXT,
            embed_id TEXT,
            status TEXT DEFAULT 'active',
            tags TEXT DEFAULT '[]',
            citations TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS knowledge_link (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(source_id, target_id, relation)
        );

        CREATE TABLE IF NOT EXISTS knowledge_conflict (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_a TEXT NOT NULL,
            item_b TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            description TEXT,
            resolved INTEGER DEFAULT 0,
            resolution TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS institutional_memory (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            decision TEXT,
            rationale TEXT,
            outcome TEXT,
            confidence REAL DEFAULT 1.0,
            who TEXT DEFAULT '',
            domain TEXT DEFAULT 'general',
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS knowledge_gap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            description TEXT NOT NULL,
            priority REAL DEFAULT 0.5,
            status TEXT DEFAULT 'open',
            identified_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
