"""PerformanceSampler — records latency/throughput samples and computes percentiles."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import get_connection, now


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return round(s[lo] + (s[hi] - s[lo]) * frac, 3)


class PerformanceSampler:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def record_sample(self, metric_name: str, value: float, unit: str = "ms",
                      component: Optional[str] = None, tags: Optional[dict] = None) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO perf_sample (metric_name, value, unit, component, tags, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (metric_name, float(value), unit, component,
                 json.dumps(tags) if tags else None, now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_percentiles(self, metric_name: str, period_hours: int = 24) -> dict:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=period_hours)).isoformat()
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT value FROM perf_sample WHERE metric_name=? AND created_at >= ?",
                (metric_name, cutoff),
            ).fetchall()
            values = [r["value"] for r in rows]
            if not values:
                return {"metric_name": metric_name, "count": 0, "p50": 0, "p95": 0,
                        "p99": 0, "min": 0, "max": 0, "mean": 0}
            return {
                "metric_name": metric_name,
                "count": len(values),
                "p50": _percentile(values, 0.50),
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "mean": round(sum(values) / len(values), 3),
            }
        finally:
            conn.close()

    def list_metrics(self) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT metric_name, component, COUNT(*) c, MAX(created_at) latest "
                "FROM perf_sample GROUP BY metric_name ORDER BY metric_name"
            ).fetchall()
            out = []
            for r in rows:
                latest = conn.execute(
                    "SELECT value FROM perf_sample WHERE metric_name=? ORDER BY created_at DESC LIMIT 1",
                    (r["metric_name"],),
                ).fetchone()
                out.append({
                    "metric_name": r["metric_name"], "component": r["component"],
                    "sample_count": r["c"], "latest_value": latest["value"] if latest else None,
                    "latest_at": r["latest"],
                })
            return out
        finally:
            conn.close()

    def get_history(self, metric_name: str, hours: int = 24, limit: int = 1000) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT created_at ts, value FROM perf_sample WHERE metric_name=? AND created_at >= ? "
                "ORDER BY created_at DESC LIMIT ?",
                (metric_name, cutoff, limit),
            ).fetchall()
            return [{"ts": r["ts"], "value": r["value"]} for r in rows]
        finally:
            conn.close()

    def dashboard(self) -> dict:
        metrics = self.list_metrics()
        detailed = [self.get_percentiles(m["metric_name"]) for m in metrics]
        top_slow = sorted(detailed, key=lambda d: d["p95"], reverse=True)[:5]
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) c FROM perf_sample").fetchone()["c"]
        finally:
            conn.close()
        return {"metrics": detailed, "top_slow": top_slow, "sample_count": total}


_instance: Optional[PerformanceSampler] = None


def get_performance_sampler() -> PerformanceSampler:
    global _instance
    if _instance is None:
        _instance = PerformanceSampler()
    return _instance
