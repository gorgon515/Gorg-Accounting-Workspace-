"""
Investment Thesis Engine — structured thesis builder storing the investment
case, supporting evidence, risks, catalysts, valuation assumptions, expected
returns, confidence, review history, and outcome tracking.

Theses feed the Knowledge Engine and Portfolio Command Center. Outcome tracking
closes the loop for institutional memory and self-improvement.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_DB = Path(".data/thesis.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS thesis (
            id TEXT PRIMARY KEY,
            symbol TEXT DEFAULT '',
            title TEXT NOT NULL,
            direction TEXT DEFAULT 'long',
            summary TEXT DEFAULT '',
            evidence TEXT DEFAULT '[]',
            risks TEXT DEFAULT '[]',
            catalysts TEXT DEFAULT '[]',
            valuation TEXT DEFAULT '{}',
            expected_return REAL,
            time_horizon TEXT DEFAULT '12m',
            confidence REAL DEFAULT 0.5,
            status TEXT DEFAULT 'active',
            outcome TEXT DEFAULT '',
            realized_return REAL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS thesis_review (
            id TEXT PRIMARY KEY,
            thesis_id TEXT NOT NULL,
            note TEXT DEFAULT '',
            confidence REAL,
            action TEXT DEFAULT 'review',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class ThesisEngine:
    def __init__(self):
        _conn().close()

    def create(self, title: str, symbol: str = "", direction: str = "long",
               summary: str = "", evidence: Optional[list] = None,
               risks: Optional[list] = None, catalysts: Optional[list] = None,
               valuation: Optional[dict] = None, expected_return: Optional[float] = None,
               time_horizon: str = "12m", confidence: float = 0.5) -> dict:
        tid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO thesis(id, symbol, title, direction, summary, evidence, risks,
               catalysts, valuation, expected_return, time_horizon, confidence)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, symbol, title, direction, summary, json.dumps(evidence or []),
             json.dumps(risks or []), json.dumps(catalysts or []),
             json.dumps(valuation or {}), expected_return, time_horizon, confidence))
        conn.commit()
        conn.close()
        self._ingest_knowledge(title, summary, symbol)
        return self.get(tid)

    def get(self, tid: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM thesis WHERE id=?", (tid,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def list(self, status: Optional[str] = None, symbol: Optional[str] = None) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if status:
            clauses.append("status=?"); params.append(status)
        if symbol:
            clauses.append("symbol=?"); params.append(symbol)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(f"SELECT * FROM thesis {where} ORDER BY updated_at DESC", params).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def update(self, tid: str, fields: dict) -> Optional[dict]:
        allowed = {"summary", "direction", "confidence", "expected_return", "time_horizon",
                   "status", "evidence", "risks", "catalysts", "valuation"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed:
                if k in ("evidence", "risks", "catalysts", "valuation"):
                    v = json.dumps(v)
                sets.append(f"{k}=?"); params.append(v)
        if not sets:
            return self.get(tid)
        params.append(tid)
        conn = _conn()
        conn.execute(f"UPDATE thesis SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?", params)
        conn.commit()
        conn.close()
        return self.get(tid)

    def add_review(self, tid: str, note: str, confidence: Optional[float] = None,
                   action: str = "review") -> dict:
        rid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            "INSERT INTO thesis_review(id, thesis_id, note, confidence, action) VALUES(?,?,?,?,?)",
            (rid, tid, note, confidence, action))
        if confidence is not None:
            conn.execute("UPDATE thesis SET confidence=?, updated_at=datetime('now') WHERE id=?",
                         (confidence, tid))
        conn.commit()
        conn.close()
        return {"id": rid, "thesis_id": tid, "note": note, "action": action}

    def reviews(self, tid: str) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM thesis_review WHERE thesis_id=? ORDER BY created_at DESC", (tid,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def close_outcome(self, tid: str, outcome: str, realized_return: Optional[float] = None) -> Optional[dict]:
        """Close a thesis and record the realized outcome → institutional memory."""
        conn = _conn()
        conn.execute(
            "UPDATE thesis SET status='closed', outcome=?, realized_return=?, updated_at=datetime('now') WHERE id=?",
            (outcome, realized_return, tid))
        conn.commit()
        conn.close()
        t = self.get(tid)
        # Feed institutional memory + self-improvement loop.
        try:
            from knowledge.memory import get_institutional_memory
            get_institutional_memory().record(
                event_type="investment_decision",
                title=f"Investment thesis: {t['title']}",
                description=t.get("summary", ""),
                decision=f"{t.get('direction', 'long')} {t.get('symbol', '')}".strip(),
                outcome=outcome, confidence=t.get("confidence", 0.5), domain="markets")
        except Exception:
            pass
        try:
            if realized_return is not None and t.get("expected_return") is not None:
                from self_improvement.engine import get_self_improvement_engine
                get_self_improvement_engine().record_accuracy(
                    kind="investment_thesis", predicted=t["expected_return"],
                    actual=realized_return, domain="markets",
                    context={"title": t["title"]})
        except Exception:
            pass
        return t

    def _fmt(self, row) -> dict:
        d = dict(row)
        for f in ("evidence", "risks", "catalysts"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        try:
            d["valuation"] = json.loads(d["valuation"])
        except Exception:
            d["valuation"] = {}
        return d

    def _ingest_knowledge(self, title: str, summary: str, symbol: str):
        try:
            from knowledge.engine import get_knowledge_engine
            get_knowledge_engine().ingest(
                title=f"[Thesis] {title}", content=summary or title,
                domain="markets", kind="insight", source="thesis_engine")
        except Exception:
            pass

    def stats(self) -> dict:
        conn = _conn()
        active = conn.execute("SELECT COUNT(*) FROM thesis WHERE status='active'").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM thesis WHERE status='closed'").fetchone()[0]
        avg_conf = conn.execute("SELECT AVG(confidence) FROM thesis WHERE status='active'").fetchone()[0]
        conn.close()
        return {"active_theses": active, "closed_theses": closed,
                "avg_confidence": round(avg_conf, 3) if avg_conf else None}


_instance: Optional[ThesisEngine] = None


def get_thesis_engine() -> ThesisEngine:
    global _instance
    if _instance is None:
        _instance = ThesisEngine()
    return _instance
