"""LearningEngine — tracks the historical accuracy of predictions and
recommendations so forecast/opportunity/risk quality can improve over time.
"""
from __future__ import annotations

from typing import Optional

from intelligence.db import get_connection, now


class LearningEngine:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def record_outcome(self, kind: str, predicted: float, actual: float,
                       subject_id: Optional[str] = None) -> dict:
        """Record a prediction vs. actual; computes error and accuracy (0..1)."""
        error = abs(predicted - actual)
        denom = max(abs(actual), abs(predicted), 1.0)
        accuracy = round(max(0.0, 1.0 - error / denom), 4)
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO learning_record (kind, subject_id, predicted, actual, error, accuracy, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (kind, subject_id, predicted, actual, round(error, 4), accuracy, now()),
            )
            conn.commit()
            return {"id": cur.lastrowid, "kind": kind, "predicted": predicted,
                    "actual": actual, "error": round(error, 4), "accuracy": accuracy}
        finally:
            conn.close()

    def accuracy_by_kind(self, kind: Optional[str] = None) -> dict:
        conn = self._conn()
        try:
            if kind:
                rows = conn.execute(
                    "SELECT accuracy FROM learning_record WHERE kind=?", (kind,)
                ).fetchall()
                vals = [r["accuracy"] for r in rows]
                return {"kind": kind, "samples": len(vals),
                        "mean_accuracy": round(sum(vals) / len(vals), 4) if vals else None}
            rows = conn.execute(
                "SELECT kind, COUNT(*) c, AVG(accuracy) a FROM learning_record GROUP BY kind"
            ).fetchall()
            return {r["kind"]: {"samples": r["c"], "mean_accuracy": round(r["a"], 4)}
                    for r in rows}
        finally:
            conn.close()

    def history(self, kind: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = self._conn()
        try:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM learning_record WHERE kind=? ORDER BY created_at DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learning_record ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def trend(self, kind: str, window: int = 10) -> dict:
        """Compare recent accuracy to the prior window to detect improvement."""
        hist = self.history(kind, limit=window * 2)
        if len(hist) < 2:
            return {"kind": kind, "trend": "insufficient_data", "samples": len(hist)}
        recent = [h["accuracy"] for h in hist[:window]]
        prior = [h["accuracy"] for h in hist[window:window * 2]] or recent
        recent_avg = sum(recent) / len(recent)
        prior_avg = sum(prior) / len(prior)
        delta = recent_avg - prior_avg
        trend = "improving" if delta > 0.02 else "declining" if delta < -0.02 else "stable"
        return {"kind": kind, "trend": trend, "recent_accuracy": round(recent_avg, 4),
                "prior_accuracy": round(prior_avg, 4), "delta": round(delta, 4)}


_instance: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    global _instance
    if _instance is None:
        _instance = LearningEngine()
    return _instance
