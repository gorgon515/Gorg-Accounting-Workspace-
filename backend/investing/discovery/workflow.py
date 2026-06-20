"""Daily Discovery Workflow.

Runs a once-a-day sweep of the universe, deriving six watch-lists (new
opportunities, improving, deteriorating, insider activity, earnings surprises,
valuation dislocations) and persisting each run for later retrieval.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .scanner import OpportunityScanner
from .ranking import IdeaRanker

_DB = Path(".data/discovery_workflow.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class DailyWorkflow:
    def __init__(self, universe, scanner: Optional[OpportunityScanner] = None,
                 ranker: Optional[IdeaRanker] = None):
        self.universe = universe
        self.scanner = scanner or OpportunityScanner(universe)
        self.ranker = ranker or IdeaRanker(universe, self.scanner)
        _conn().close()

    def run(self) -> dict:
        secs = self.universe.all()
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # New opportunities: freshly high-ranked names (top of composite ranking).
        ranked = self.ranker.rank(limit=10, exclude_mega_cap=True)
        new_opportunities = [
            {"symbol": r["symbol"], "name": r["name"], "composite": r["composite"]}
            for r in ranked
        ]

        # Improving / deteriorating: from earnings-series acceleration.
        deltas = []
        for s in secs:
            eg1, eg2 = self.scanner._series_deltas(s.get("eps_3y", []))
            rg1, rg2 = self.scanner._series_deltas(s.get("revenue_3y", []))
            deltas.append((s, (eg2 - eg1) + 0.5 * (rg2 - rg1), eg2, rg2))
        deltas.sort(key=lambda x: x[1], reverse=True)
        improving = [
            {"symbol": s["symbol"], "name": s["name"],
             "earnings_accel": round(d, 3), "eps_growth": round(eg2, 3)}
            for s, d, eg2, rg2 in deltas[:10] if d > 0.02
        ]
        deteriorating = [
            {"symbol": s["symbol"], "name": s["name"],
             "earnings_accel": round(d, 3), "eps_growth": round(eg2, 3)}
            for s, d, eg2, rg2 in reversed(deltas[-10:]) if d < -0.02
        ]

        # Insider activity: high insider ownership names.
        insiders = sorted(secs, key=lambda s: s.get("insider_ownership", 0), reverse=True)
        insider_activity = [
            {"symbol": s["symbol"], "name": s["name"],
             "insider_ownership": s.get("insider_ownership", 0)}
            for s in insiders[:10] if s.get("insider_ownership", 0) >= 0.05
        ]

        # Earnings surprises: largest positive EPS acceleration.
        surprises = []
        for s in secs:
            eg1, eg2 = self.scanner._series_deltas(s.get("eps_3y", []))
            accel = eg2 - eg1
            if accel > 0.15 and eg2 > 0:
                surprises.append({"symbol": s["symbol"], "name": s["name"],
                                  "eps_acceleration": round(accel, 3),
                                  "eps_growth": round(eg2, 3)})
        surprises.sort(key=lambda x: x["eps_acceleration"], reverse=True)
        earnings_surprises = surprises[:10]

        # Valuation dislocations: value-score outliers (cheapest names).
        value_scan = self.scanner.scan("value", limit=10)
        valuation_dislocations = [
            {"symbol": r["symbol"], "name": r["name"], "value_score": r["score"],
             "rationale": r["rationale"]}
            for r in value_scan if r["score"] >= 55
        ]

        payload = {
            "run_date": run_date,
            "new_opportunities": new_opportunities,
            "improving": improving,
            "deteriorating": deteriorating,
            "insider_activity": insider_activity,
            "earnings_surprises": earnings_surprises,
            "valuation_dislocations": valuation_dislocations,
        }

        conn = _conn()
        conn.execute("INSERT INTO daily_run(run_date, payload) VALUES(?, ?)",
                     (run_date, json.dumps(payload)))
        conn.commit()
        conn.close()
        return payload

    def latest(self) -> Optional[dict]:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM daily_run ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return None
        try:
            return json.loads(row["payload"])
        except Exception:
            return None

    def history(self, limit: int = 30) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT run_date, created_at FROM daily_run ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


_instance = None
