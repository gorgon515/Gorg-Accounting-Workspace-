"""Outcome Tracking + Learning Feedback.

Records recommendations and their outcomes, then scores accuracy, agent
performance, completion, and confidence calibration — feeding a suggested
confidence adjustment per agent to improve future recommendations.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendation (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, summary TEXT, confidence REAL,
  ref TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outcome (
  id INTEGER PRIMARY KEY AUTOINCREMENT, recommendation_id INTEGER NOT NULL,
  success INTEGER, satisfaction INTEGER, note TEXT, recorded_at TEXT NOT NULL
);
"""


class OutcomeStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("HELIOS_OUTCOMES_DB") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".data", "outcomes.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record_recommendation(self, agent: str, summary: str, *, confidence: Optional[float] = None,
                              ref: Optional[str] = None) -> dict:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO recommendation (agent,summary,confidence,ref,created_at) VALUES (?,?,?,?,?)",
                (agent, summary, confidence, ref, datetime.now(timezone.utc).isoformat()))
            self.conn.commit()
        return {"id": cur.lastrowid, "agent": agent, "summary": summary, "confidence": confidence}

    def record_outcome(self, recommendation_id: int, *, success: bool,
                       satisfaction: Optional[int] = None, note: str = "") -> dict:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO outcome (recommendation_id,success,satisfaction,note,recorded_at) VALUES (?,?,?,?,?)",
                (recommendation_id, 1 if success else 0, satisfaction, note,
                 datetime.now(timezone.utc).isoformat()))
            self.conn.commit()
        return {"id": cur.lastrowid, "recommendation_id": recommendation_id, "success": success}

    def agent_performance(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT r.agent,
                   COUNT(DISTINCT r.id) AS recommendations,
                   COUNT(o.id) AS outcomes,
                   AVG(o.success) AS accuracy,
                   AVG(r.confidence) AS avg_confidence,
                   AVG(o.satisfaction) AS avg_satisfaction
            FROM recommendation r LEFT JOIN outcome o ON o.recommendation_id = r.id
            GROUP BY r.agent
        """)
        out = []
        for r in rows:
            acc = round(r["accuracy"], 3) if r["accuracy"] is not None else None
            conf = round(r["avg_confidence"], 3) if r["avg_confidence"] is not None else None
            # Calibration: if confidence overshoots realized accuracy, suggest a downward nudge.
            adj = None
            if acc is not None and conf is not None:
                adj = round(acc - conf, 3)
            out.append({"agent": r["agent"], "recommendations": r["recommendations"],
                        "outcomes_recorded": r["outcomes"], "accuracy": acc, "avg_confidence": conf,
                        "avg_satisfaction": round(r["avg_satisfaction"], 2) if r["avg_satisfaction"] is not None else None,
                        "suggested_confidence_adjustment": adj})
        return out

    def metrics(self) -> dict:
        total_rec = self.conn.execute("SELECT COUNT(*) n FROM recommendation").fetchone()["n"]
        total_out = self.conn.execute("SELECT COUNT(*) n FROM outcome").fetchone()["n"]
        acc = self.conn.execute("SELECT AVG(success) a FROM outcome").fetchone()["a"]
        return {"recommendations": total_rec, "outcomes_recorded": total_out,
                "completion_rate": round(total_out / total_rec, 3) if total_rec else 0.0,
                "overall_accuracy": round(acc, 3) if acc is not None else None,
                "by_agent": self.agent_performance()}

    def close(self):
        self.conn.close()
