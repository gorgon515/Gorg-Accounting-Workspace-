"""
Alternative Data Platform — store and analyze alternative datasets: insider
activity, institutional ownership, short interest, options activity, analyst
revisions, congressional trades, ETF flows, sector rotation.

Provides data-quality scoring, historical storage, change detection, and signal
generation. Datasets are ingested from connectors (credential-gated) or manual
upload; the platform is fully functional with whatever data is present.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

_DB = Path(".data/altdata.db")

DATASETS = [
    "insider_activity", "institutional_ownership", "short_interest",
    "options_activity", "analyst_revisions", "congressional_trades",
    "etf_flows", "sector_rotation",
]


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS alt_observation (
            id TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            symbol TEXT DEFAULT '',
            metric TEXT DEFAULT 'value',
            value REAL,
            direction TEXT DEFAULT '',
            detail TEXT DEFAULT '{}',
            quality REAL DEFAULT 1.0,
            observed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(dataset, symbol, metric, observed_at)
        );

        CREATE TABLE IF NOT EXISTS alt_signal (
            id TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            symbol TEXT DEFAULT '',
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            direction TEXT DEFAULT 'neutral',
            strength REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class AltDataPlatform:
    def __init__(self):
        _conn().close()

    def ingest(self, dataset: str, observations: list[dict]) -> dict:
        """Store observations with data-quality scoring."""
        if dataset not in DATASETS:
            return {"error": f"unknown dataset '{dataset}'", "valid": DATASETS}
        conn = _conn()
        stored = 0
        for obs in observations:
            quality = self._score_quality(obs)
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO alt_observation
                       (id, dataset, symbol, metric, value, direction, detail, quality, observed_at)
                       VALUES(?,?,?,?,?,?,?,?,COALESCE(?, datetime('now')))""",
                    (str(uuid.uuid4()), dataset, obs.get("symbol", ""),
                     obs.get("metric", "value"), obs.get("value"),
                     obs.get("direction", ""), json.dumps(obs.get("detail", {})),
                     quality, obs.get("observed_at")))
                stored += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return {"dataset": dataset, "stored": stored}

    def _score_quality(self, obs: dict) -> float:
        score = 1.0
        if obs.get("value") is None:
            score -= 0.5
        if not obs.get("symbol"):
            score -= 0.2
        if not obs.get("observed_at"):
            score -= 0.1
        return round(max(0.0, score), 2)

    def get_observations(self, dataset: str, symbol: Optional[str] = None,
                         limit: int = 100) -> list[dict]:
        conn = _conn()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM alt_observation WHERE dataset=? AND symbol=? ORDER BY observed_at DESC LIMIT ?",
                (dataset, symbol, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alt_observation WHERE dataset=? ORDER BY observed_at DESC LIMIT ?",
                (dataset, limit)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["detail"] = json.loads(d["detail"])
            except Exception:
                d["detail"] = {}
            out.append(d)
        return out

    def detect_changes(self, dataset: str, symbol: str, threshold: float = 0.2) -> dict:
        """Change detection: compare latest observation to prior trend."""
        obs = self.get_observations(dataset, symbol, limit=10)
        values = [o["value"] for o in obs if o.get("value") is not None]
        if len(values) < 2:
            return {"dataset": dataset, "symbol": symbol, "change_detected": False,
                    "reason": "insufficient history"}
        latest = values[0]
        prior_mean = float(np.mean(values[1:]))
        if prior_mean == 0:
            pct_change = 0.0
        else:
            pct_change = (latest - prior_mean) / abs(prior_mean)
        detected = abs(pct_change) >= threshold
        return {"dataset": dataset, "symbol": symbol, "change_detected": detected,
                "latest": latest, "prior_mean": round(prior_mean, 4),
                "pct_change": round(pct_change, 4)}

    def generate_signals(self, dataset: str) -> list[dict]:
        """Derive trading signals from alternative data patterns."""
        conn = _conn()
        symbols = [r["symbol"] for r in conn.execute(
            "SELECT DISTINCT symbol FROM alt_observation WHERE dataset=? AND symbol!=''", (dataset,)).fetchall()]
        conn.close()
        signals = []
        for sym in symbols:
            change = self.detect_changes(dataset, sym, threshold=0.15)
            if change.get("change_detected"):
                direction = "bullish" if change["pct_change"] > 0 else "bearish"
                # Some datasets invert (e.g. short_interest up = bearish)
                if dataset in ("short_interest",):
                    direction = "bearish" if change["pct_change"] > 0 else "bullish"
                strength = min(abs(change["pct_change"]), 1.0)
                sig = self._create_signal(dataset, sym,
                    f"{dataset.replace('_', ' ').title()} change for {sym}",
                    f"{change['pct_change']:+.1%} vs recent trend", direction, strength)
                signals.append(sig)
        return signals

    def _create_signal(self, dataset, symbol, title, description, direction, strength) -> dict:
        sid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO alt_signal(id, dataset, symbol, title, description, direction, strength)
               VALUES(?,?,?,?,?,?,?)""",
            (sid, dataset, symbol, title, description, direction, round(strength, 3)))
        conn.commit()
        conn.close()
        return {"id": sid, "dataset": dataset, "symbol": symbol, "title": title,
                "direction": direction, "strength": round(strength, 3)}

    def list_signals(self, dataset: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        if dataset:
            rows = conn.execute(
                "SELECT * FROM alt_signal WHERE dataset=? ORDER BY strength DESC, created_at DESC LIMIT ?",
                (dataset, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alt_signal ORDER BY strength DESC, created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def datasets(self) -> list[dict]:
        conn = _conn()
        out = []
        for ds in DATASETS:
            cnt = conn.execute("SELECT COUNT(*) FROM alt_observation WHERE dataset=?", (ds,)).fetchone()[0]
            quality = conn.execute("SELECT AVG(quality) FROM alt_observation WHERE dataset=?", (ds,)).fetchone()[0]
            out.append({"id": ds, "name": ds.replace("_", " ").title(),
                        "observations": cnt, "avg_quality": round(quality, 3) if quality else None})
        conn.close()
        return out

    def stats(self) -> dict:
        conn = _conn()
        obs = conn.execute("SELECT COUNT(*) FROM alt_observation").fetchone()[0]
        sig = conn.execute("SELECT COUNT(*) FROM alt_signal").fetchone()[0]
        conn.close()
        return {"total_observations": obs, "total_signals": sig, "datasets": len(DATASETS)}


_instance: Optional[AltDataPlatform] = None


def get_altdata_platform() -> AltDataPlatform:
    global _instance
    if _instance is None:
        _instance = AltDataPlatform()
    return _instance
