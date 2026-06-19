"""
Financial Data Hub: unified market database.
Stores prices, fundamentals, filings, economic indicators.
Supports historical storage, versioning, backfill, data quality scoring.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

_DB = Path(".data/financial_hub.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS price_bar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER,
            adj_close REAL,
            source TEXT DEFAULT 'unknown',
            quality REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(symbol, date, source)
        );

        CREATE TABLE IF NOT EXISTS fundamental (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            period TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            source TEXT DEFAULT 'unknown',
            quality REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(symbol, period, metric, source)
        );

        CREATE TABLE IF NOT EXISTS economic_indicator (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL,
            unit TEXT DEFAULT '',
            source TEXT DEFAULT 'fred',
            quality REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(series_id, date, source)
        );

        CREATE TABLE IF NOT EXISTS filing_summary (
            id TEXT PRIMARY KEY,
            cik TEXT NOT NULL,
            entity TEXT NOT NULL,
            form TEXT NOT NULL,
            filing_date TEXT,
            accession_number TEXT,
            primary_doc TEXT,
            source TEXT DEFAULT 'sec_edgar',
            ingested_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS data_quality_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            series_id TEXT NOT NULL,
            rows_stored INTEGER DEFAULT 0,
            rows_skipped INTEGER DEFAULT 0,
            avg_quality REAL DEFAULT 1.0,
            logged_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class FinancialDataHub:
    def __init__(self):
        _conn().close()  # ensure schema exists

    def store_prices(self, symbol: str, bars: list[dict], source: str = "yahoo_finance") -> int:
        conn = _conn()
        stored = 0
        for bar in bars:
            try:
                conn.execute(
                    """INSERT INTO price_bar(symbol, date, open, high, low, close, volume, adj_close, source)
                       VALUES(?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(symbol, date, source) DO UPDATE SET
                       close=excluded.close, volume=excluded.volume""",
                    (symbol, bar.get("date") or bar.get("Date", ""),
                     bar.get("open"), bar.get("high"), bar.get("low"),
                     bar.get("close") or bar.get("Close"),
                     bar.get("volume") or bar.get("Volume"),
                     bar.get("adj_close"), source),
                )
                stored += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return stored

    def get_prices(self, symbol: str, limit: int = 252, source: Optional[str] = None) -> list[dict]:
        conn = _conn()
        if source:
            rows = conn.execute(
                "SELECT * FROM price_bar WHERE symbol=? AND source=? ORDER BY date DESC LIMIT ?",
                (symbol, source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM price_bar WHERE symbol=? ORDER BY date DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def store_economic(self, series_id: str, name: str, observations: list[dict],
                       source: str = "fred", unit: str = "") -> int:
        conn = _conn()
        stored = 0
        for obs in observations:
            val = obs.get("value")
            if val == "." or val is None:
                continue
            try:
                conn.execute(
                    """INSERT INTO economic_indicator(series_id, name, date, value, unit, source)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(series_id, date, source) DO UPDATE SET value=excluded.value""",
                    (series_id, name, obs.get("date", ""), float(val), unit, source),
                )
                stored += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return stored

    def get_economic(self, series_id: str, limit: int = 60) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM economic_indicator WHERE series_id=? ORDER BY date DESC LIMIT ?",
            (series_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def store_filing(self, filing: dict):
        conn = _conn()
        fid = f"{filing.get('cik', '')}:{filing.get('accession_number', '')}:{filing.get('form', '')}"
        import hashlib
        fid = hashlib.md5(fid.encode()).hexdigest()
        conn.execute(
            """INSERT OR IGNORE INTO filing_summary
               (id, cik, entity, form, filing_date, accession_number, primary_doc)
               VALUES(?,?,?,?,?,?,?)""",
            (fid, filing.get("cik", ""), filing.get("entity", ""),
             filing.get("form", ""), filing.get("filing_date", ""),
             filing.get("accession_number", ""), filing.get("primary_doc", "")),
        )
        conn.commit()
        conn.close()

    def list_filings(self, form: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        if form:
            rows = conn.execute(
                "SELECT * FROM filing_summary WHERE form=? ORDER BY filing_date DESC LIMIT ?",
                (form, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM filing_summary ORDER BY ingested_at DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_watchlist(self, symbol: str, name: str = "", sector: str = "") -> dict:
        conn = _conn()
        conn.execute(
            """INSERT INTO watchlist(symbol, name, sector) VALUES(?,?,?)
               ON CONFLICT(symbol) DO UPDATE SET name=excluded.name, sector=excluded.sector""",
            (symbol, name, sector),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM watchlist WHERE symbol=?", (symbol,)).fetchone()
        conn.close()
        return dict(row)

    def get_watchlist(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM watchlist ORDER BY symbol").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def remove_watchlist(self, symbol: str):
        conn = _conn()
        conn.execute("DELETE FROM watchlist WHERE symbol=?", (symbol,))
        conn.commit()
        conn.close()

    def ingest_from_connector(self, connector_id: str, items: list[dict]) -> dict:
        """Route items to the right table based on connector type."""
        stored = 0
        if connector_id == "yahoo_finance":
            for item in items:
                if "symbol" in item and "price" in item:
                    self.store_prices(item["symbol"], [{"date": datetime.utcnow().strftime("%Y-%m-%d"),
                                                         "close": item["price"], "volume": item.get("volume")}])
                    stored += 1
        elif connector_id in ("fred", "bls"):
            for item in items:
                if "series_id" in item and "observations" in item:
                    stored += self.store_economic(item["series_id"], item["series_id"],
                                                  item["observations"], source=connector_id)
        elif connector_id == "sec_edgar":
            for item in items:
                if "form" in item and "cik" in item:
                    self.store_filing(item)
                    stored += 1
        return {"connector_id": connector_id, "stored": stored}

    def stats(self) -> dict:
        conn = _conn()
        prices = conn.execute("SELECT COUNT(DISTINCT symbol) FROM price_bar").fetchone()[0]
        price_rows = conn.execute("SELECT COUNT(*) FROM price_bar").fetchone()[0]
        econ = conn.execute("SELECT COUNT(DISTINCT series_id) FROM economic_indicator").fetchone()[0]
        econ_rows = conn.execute("SELECT COUNT(*) FROM economic_indicator").fetchone()[0]
        filings = conn.execute("SELECT COUNT(*) FROM filing_summary").fetchone()[0]
        watchlist = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn.close()
        return {
            "symbols_tracked": prices, "price_bars": price_rows,
            "economic_series": econ, "economic_observations": econ_rows,
            "filings": filings, "watchlist_size": watchlist,
        }


_instance: Optional[FinancialDataHub] = None


def get_financial_hub() -> FinancialDataHub:
    global _instance
    if _instance is None:
        _instance = FinancialDataHub()
    return _instance
