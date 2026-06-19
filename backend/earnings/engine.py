"""
Earnings Intelligence System — monitor earnings dates, guidance changes,
estimate revisions, surprises, post-earnings drift, and management sentiment.
Generates earnings scorecards combining the available signals.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

_DB = Path(".data/earnings.db")

_POSITIVE = ["beat", "raised", "strong", "record", "exceeded", "growth", "accelerating",
             "robust", "outperform", "upgrade", "momentum", "confident"]
_NEGATIVE = ["miss", "missed", "lowered", "cut", "weak", "decline", "headwind",
             "softness", "downgrade", "disappointing", "challenging", "cautious"]


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS earnings_event (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            period TEXT DEFAULT '',
            earnings_date TEXT DEFAULT '',
            eps_estimate REAL,
            eps_actual REAL,
            revenue_estimate REAL,
            revenue_actual REAL,
            guidance TEXT DEFAULT '',
            transcript TEXT DEFAULT '',
            status TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS estimate_revision (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            metric TEXT DEFAULT 'eps',
            old_value REAL,
            new_value REAL,
            analyst TEXT DEFAULT '',
            revised_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS earnings_scorecard (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            period TEXT DEFAULT '',
            score REAL DEFAULT 0.0,
            grade TEXT DEFAULT '',
            components TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class EarningsEngine:
    def __init__(self):
        _conn().close()

    def add_event(self, symbol: str, period: str = "", earnings_date: str = "",
                  eps_estimate: Optional[float] = None, eps_actual: Optional[float] = None,
                  revenue_estimate: Optional[float] = None, revenue_actual: Optional[float] = None,
                  guidance: str = "", transcript: str = "") -> dict:
        eid = str(uuid.uuid4())
        status = "reported" if eps_actual is not None else "scheduled"
        conn = _conn()
        conn.execute(
            """INSERT INTO earnings_event(id, symbol, period, earnings_date, eps_estimate,
               eps_actual, revenue_estimate, revenue_actual, guidance, transcript, status)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, symbol, period, earnings_date, eps_estimate, eps_actual,
             revenue_estimate, revenue_actual, guidance, transcript, status))
        conn.commit()
        conn.close()
        return self.get_event(eid)

    def get_event(self, eid: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM earnings_event WHERE id=?", (eid,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_events(self, symbol: Optional[str] = None, status: Optional[str] = None,
                    limit: int = 50) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if symbol:
            clauses.append("symbol=?"); params.append(symbol)
        if status:
            clauses.append("status=?"); params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM earnings_event {where} ORDER BY earnings_date DESC LIMIT ?",
            params + [limit]).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_revision(self, symbol: str, metric: str, old_value: float, new_value: float,
                     analyst: str = "") -> dict:
        rid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO estimate_revision(id, symbol, metric, old_value, new_value, analyst)
               VALUES(?,?,?,?,?,?)""",
            (rid, symbol, metric, old_value, new_value, analyst))
        conn.commit()
        conn.close()
        return {"id": rid, "symbol": symbol, "metric": metric,
                "direction": "up" if new_value > old_value else "down",
                "change_pct": round((new_value - old_value) / abs(old_value), 4) if old_value else None}

    def revision_trend(self, symbol: str, metric: str = "eps") -> dict:
        conn = _conn()
        rows = conn.execute(
            "SELECT old_value, new_value FROM estimate_revision WHERE symbol=? AND metric=? ORDER BY revised_at",
            (symbol, metric)).fetchall()
        conn.close()
        if not rows:
            return {"symbol": symbol, "metric": metric, "revisions": 0, "net_direction": "neutral"}
        ups = sum(1 for r in rows if r["new_value"] > r["old_value"])
        downs = sum(1 for r in rows if r["new_value"] < r["old_value"])
        direction = "up" if ups > downs else "down" if downs > ups else "neutral"
        return {"symbol": symbol, "metric": metric, "revisions": len(rows),
                "upgrades": ups, "downgrades": downs, "net_direction": direction}

    def surprise(self, eid: str) -> dict:
        ev = self.get_event(eid)
        if not ev:
            return {"error": "event not found"}
        out = {"symbol": ev["symbol"], "period": ev["period"]}
        if ev.get("eps_actual") is not None and ev.get("eps_estimate"):
            est = ev["eps_estimate"]
            out["eps_surprise"] = round((ev["eps_actual"] - est) / abs(est), 4) if est else None
            out["eps_beat"] = ev["eps_actual"] > est
        if ev.get("revenue_actual") is not None and ev.get("revenue_estimate"):
            est = ev["revenue_estimate"]
            out["revenue_surprise"] = round((ev["revenue_actual"] - est) / abs(est), 4) if est else None
            out["revenue_beat"] = ev["revenue_actual"] > est
        return out

    def analyze_sentiment(self, text: str) -> dict:
        """Lexicon-based management sentiment from guidance/transcript text."""
        if not text:
            return {"sentiment": "neutral", "score": 0.0, "positive": 0, "negative": 0}
        t = text.lower()
        pos = sum(t.count(w) for w in _POSITIVE)
        neg = sum(t.count(w) for w in _NEGATIVE)
        total = pos + neg
        score = (pos - neg) / total if total else 0.0
        sentiment = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        return {"sentiment": sentiment, "score": round(score, 3), "positive": pos, "negative": neg}

    def post_earnings_drift(self, symbol: str, earnings_date: str, window: int = 10) -> dict:
        """Measure price drift in the window following an earnings date."""
        from financial_hub.store import get_financial_hub
        bars = get_financial_hub().get_prices(symbol, limit=252)
        ordered = list(reversed(bars))
        dates = [b.get("date") for b in ordered]
        if earnings_date not in dates:
            return {"symbol": symbol, "drift": None, "reason": "earnings date not in price history"}
        idx = dates.index(earnings_date)
        closes = [b.get("close") for b in ordered]
        if idx + window >= len(closes) or closes[idx] in (None, 0):
            return {"symbol": symbol, "drift": None, "reason": "insufficient post-earnings data"}
        drift = (closes[idx + window] - closes[idx]) / closes[idx]
        return {"symbol": symbol, "earnings_date": earnings_date, "window": window,
                "drift": round(float(drift), 4), "direction": "up" if drift > 0 else "down"}

    def scorecard(self, eid: str) -> dict:
        """Generate an earnings scorecard combining surprise, revisions, sentiment."""
        ev = self.get_event(eid)
        if not ev:
            return {"error": "event not found"}
        components = {}
        score = 50.0

        surp = self.surprise(eid)
        if surp.get("eps_surprise") is not None:
            components["eps_surprise"] = surp["eps_surprise"]
            score += np.clip(surp["eps_surprise"] * 100, -25, 25)
        if surp.get("revenue_surprise") is not None:
            components["revenue_surprise"] = surp["revenue_surprise"]
            score += np.clip(surp["revenue_surprise"] * 100, -15, 15)

        sent = self.analyze_sentiment(ev.get("guidance", "") + " " + ev.get("transcript", ""))
        components["sentiment"] = sent
        score += sent["score"] * 20

        rev = self.revision_trend(ev["symbol"])
        components["revision_trend"] = rev["net_direction"]
        if rev["net_direction"] == "up":
            score += 10
        elif rev["net_direction"] == "down":
            score -= 10

        score = float(np.clip(score, 0, 100))
        grade = ("A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50
                 else "D" if score >= 35 else "F")
        sid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO earnings_scorecard(id, symbol, period, score, grade, components)
               VALUES(?,?,?,?,?,?)""",
            (sid, ev["symbol"], ev["period"], round(score, 1), grade, json.dumps(components)))
        conn.commit()
        conn.close()
        return {"id": sid, "symbol": ev["symbol"], "period": ev["period"],
                "score": round(score, 1), "grade": grade, "components": components}

    def list_scorecards(self, symbol: Optional[str] = None, limit: int = 30) -> list[dict]:
        conn = _conn()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM earnings_scorecard WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
                (symbol, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM earnings_scorecard ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["components"] = json.loads(d["components"])
            except Exception:
                d["components"] = {}
            out.append(d)
        return out

    def stats(self) -> dict:
        conn = _conn()
        events = conn.execute("SELECT COUNT(*) FROM earnings_event").fetchone()[0]
        scorecards = conn.execute("SELECT COUNT(*) FROM earnings_scorecard").fetchone()[0]
        revisions = conn.execute("SELECT COUNT(*) FROM estimate_revision").fetchone()[0]
        conn.close()
        return {"earnings_events": events, "scorecards": scorecards, "revisions": revisions}


_instance: Optional[EarningsEngine] = None


def get_earnings_engine() -> EarningsEngine:
    global _instance
    if _instance is None:
        _instance = EarningsEngine()
    return _instance
