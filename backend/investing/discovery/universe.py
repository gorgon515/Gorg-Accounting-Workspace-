"""Market Universe Builder — persistent store of the investable equity universe.

Holds every fundamental field from the seed snapshot (or live ingestion) in a
SQLite table. Fundamentals are stored as columns; the two 3-year series
(revenue_3y, eps_3y) are stored as JSON columns. Supports seeding from the
static snapshot and live ``ingest()`` of arbitrary securities.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional

from . import seed_data

_DB = Path(".data/discovery_universe.db")

# Numeric fundamental columns (everything except symbol/text fields and the
# two JSON series columns).
_NUMERIC_FIELDS = [
    "market_cap", "revenue", "net_income", "fcf", "total_debt", "equity",
    "ebitda", "enterprise_value", "revenue_growth", "earnings_growth",
    "gross_margin", "operating_margin", "roic", "roe", "pe", "ev_ebitda",
    "price_to_fcf", "fcf_yield", "dividend_yield", "insider_ownership",
]
_TEXT_FIELDS = ["name", "exchange", "sector", "industry"]
_INT_FIELDS = ["analyst_coverage"]
_JSON_FIELDS = ["revenue_3y", "eps_3y"]
_ALL_FIELDS = _TEXT_FIELDS + _NUMERIC_FIELDS + _INT_FIELDS + _JSON_FIELDS


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS security (
            symbol TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            exchange TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            industry TEXT DEFAULT '',
            market_cap REAL DEFAULT 0,
            revenue REAL DEFAULT 0,
            net_income REAL DEFAULT 0,
            fcf REAL DEFAULT 0,
            total_debt REAL DEFAULT 0,
            equity REAL DEFAULT 0,
            ebitda REAL DEFAULT 0,
            enterprise_value REAL DEFAULT 0,
            revenue_growth REAL DEFAULT 0,
            earnings_growth REAL DEFAULT 0,
            gross_margin REAL DEFAULT 0,
            operating_margin REAL DEFAULT 0,
            roic REAL DEFAULT 0,
            roe REAL DEFAULT 0,
            pe REAL DEFAULT 0,
            ev_ebitda REAL DEFAULT 0,
            price_to_fcf REAL DEFAULT 0,
            fcf_yield REAL DEFAULT 0,
            dividend_yield REAL DEFAULT 0,
            insider_ownership REAL DEFAULT 0,
            analyst_coverage INTEGER DEFAULT 0,
            revenue_3y TEXT DEFAULT '[]',
            eps_3y TEXT DEFAULT '[]',
            source TEXT DEFAULT 'seed',
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_security_sector ON security(sector);
        CREATE INDEX IF NOT EXISTS idx_security_exchange ON security(exchange);
    """)
    return conn


class UniverseBuilder:
    def __init__(self):
        _conn().close()  # ensure schema

    # ── cap-tier helper ──────────────────────────────────────────────────────
    @staticmethod
    def cap_tier(market_cap: float) -> str:
        """Classify a market cap (USD millions) into a tier.

        micro < 300M, small 300M-2B, mid 2B-10B, large > 10B.
        """
        mc = float(market_cap or 0.0)
        if mc < 300:
            return "micro"
        if mc < 2000:
            return "small"
        if mc < 10000:
            return "mid"
        return "large"

    # ── writes ───────────────────────────────────────────────────────────────
    def _upsert(self, conn: sqlite3.Connection, sec: dict, source: str) -> None:
        cols = ["symbol"] + _ALL_FIELDS + ["source"]
        vals = [sec.get("symbol")]
        for f in _TEXT_FIELDS:
            vals.append(str(sec.get(f, "")))
        for f in _NUMERIC_FIELDS:
            v = sec.get(f)
            vals.append(float(v) if v is not None else 0.0)
        for f in _INT_FIELDS:
            v = sec.get(f)
            vals.append(int(v) if v is not None else 0)
        for f in _JSON_FIELDS:
            vals.append(json.dumps(sec.get(f) or []))
        vals.append(source)

        placeholders = ",".join("?" for _ in cols)
        update_cols = [c for c in cols if c != "symbol"]
        set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
        set_clause += ", updated_at=datetime('now')"
        conn.execute(
            f"INSERT INTO security({','.join(cols)}) VALUES({placeholders}) "
            f"ON CONFLICT(symbol) DO UPDATE SET {set_clause}",
            vals,
        )

    def seed(self) -> dict:
        """Upsert all securities from the static snapshot."""
        conn = _conn()
        n = 0
        for sec in seed_data.SECURITIES:
            if not sec.get("symbol"):
                continue
            self._upsert(conn, sec, source="seed")
            n += 1
        conn.commit()
        conn.close()
        return {"added": n}

    def ingest(self, securities: list[dict]) -> dict:
        """Upsert arbitrary securities (live data path)."""
        conn = _conn()
        n = 0
        for sec in securities or []:
            if not sec.get("symbol"):
                continue
            self._upsert(conn, sec, source="live")
            n += 1
        conn.commit()
        conn.close()
        return {"upserted": n}

    # ── reads ────────────────────────────────────────────────────────────────
    def _fmt(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        for f in _JSON_FIELDS:
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        d["cap_tier"] = self.cap_tier(d.get("market_cap", 0.0))
        return d

    def get(self, symbol: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM security WHERE symbol=?", (symbol,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def list(self, sector: Optional[str] = None, cap_tier: Optional[str] = None,
             exchange: Optional[str] = None, limit: int = 200) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if sector:
            clauses.append("sector=?")
            params.append(sector)
        if exchange:
            clauses.append("exchange=?")
            params.append(exchange)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM security{where} ORDER BY market_cap DESC", params
        ).fetchall()
        conn.close()
        out = [self._fmt(r) for r in rows]
        if cap_tier:
            out = [s for s in out if s["cap_tier"] == cap_tier]
        return out[: max(0, int(limit))]

    def all(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT * FROM security").fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def all_symbols(self) -> list[str]:
        conn = _conn()
        rows = conn.execute("SELECT symbol FROM security ORDER BY symbol").fetchall()
        conn.close()
        return [r["symbol"] for r in rows]

    def stats(self) -> dict:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM security").fetchone()[0]
        sector_rows = conn.execute(
            "SELECT sector, COUNT(*) c FROM security GROUP BY sector ORDER BY c DESC"
        ).fetchall()
        exch_rows = conn.execute(
            "SELECT exchange, COUNT(*) c FROM security GROUP BY exchange ORDER BY c DESC"
        ).fetchall()
        caps = conn.execute("SELECT market_cap FROM security").fetchall()
        conn.close()
        by_tier: dict[str, int] = {"micro": 0, "small": 0, "mid": 0, "large": 0}
        for r in caps:
            by_tier[self.cap_tier(r["market_cap"])] += 1
        return {
            "total": total,
            "by_sector": {r["sector"]: r["c"] for r in sector_rows},
            "by_exchange": {r["exchange"]: r["c"] for r in exch_rows},
            "by_cap_tier": by_tier,
        }


_instance: Optional[UniverseBuilder] = None


def get_universe_builder() -> UniverseBuilder:
    global _instance
    if _instance is None:
        _instance = UniverseBuilder()
    return _instance
