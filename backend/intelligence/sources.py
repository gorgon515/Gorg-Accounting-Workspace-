"""Cross-domain data access for the intelligence layer.

Reads from existing HELIOS subsystems (accounting, goals, tasks) and degrades
gracefully — a missing or empty database returns empty/zeroed structures rather
than raising, so the reasoning engines always have something to work with.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
ACCT_DB = os.path.join(BASE_DIR, "accounting.db")


def _safe_conn(path: str) -> Optional[sqlite3.Connection]:
    if not os.path.isfile(path):
        return None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def accounting_snapshot() -> dict:
    """Aggregate ledger figures: revenue, expenses, net, AR/AP, cash proxy."""
    conn = _safe_conn(ACCT_DB)
    if conn is None:
        return {"available": False, "revenue": 0.0, "expenses": 0.0, "net": 0.0,
                "ar_outstanding": 0.0, "ap_outstanding": 0.0, "entry_count": 0}
    try:
        out = {"available": True, "revenue": 0.0, "expenses": 0.0, "net": 0.0,
               "ar_outstanding": 0.0, "ap_outstanding": 0.0, "entry_count": 0}
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if {"journal_line", "account"}.issubset(tables):
            rows = conn.execute(
                "SELECT a.type type, SUM(l.debit) d, SUM(l.credit) c "
                "FROM journal_line l JOIN account a ON a.id = l.account_id GROUP BY a.type"
            ).fetchall()
            for r in rows:
                t = (r["type"] or "").lower()
                debit, credit = r["d"] or 0.0, r["c"] or 0.0
                if t in ("revenue", "income"):
                    out["revenue"] += credit - debit
                elif t in ("expense",):
                    out["expenses"] += debit - credit
        out["net"] = round(out["revenue"] - out["expenses"], 2)
        if "journal_entry" in tables:
            out["entry_count"] = conn.execute(
                "SELECT COUNT(*) c FROM journal_entry").fetchone()["c"]
        if "invoice" in tables:
            try:
                out["ar_outstanding"] = conn.execute(
                    "SELECT COALESCE(SUM(balance),0) b FROM invoice WHERE status!='paid'"
                ).fetchone()["b"] or 0.0
            except Exception:
                pass
        return out
    except Exception:
        return {"available": False, "revenue": 0.0, "expenses": 0.0, "net": 0.0,
                "ar_outstanding": 0.0, "ap_outstanding": 0.0, "entry_count": 0}
    finally:
        conn.close()


def goals_snapshot() -> dict:
    try:
        from goals.engine import GoalStore
        store = GoalStore()
        try:
            goals = store.list()
        finally:
            store.close()
        active = [g for g in goals if g.get("progress", 0) < 100]
        at_risk = [g for g in goals if 0 < g.get("progress", 0) < 40]
        return {"available": True, "total": len(goals), "active": len(active),
                "at_risk": len(at_risk), "goals": goals}
    except Exception:
        return {"available": False, "total": 0, "active": 0, "at_risk": 0, "goals": []}


def tasks_snapshot() -> dict:
    try:
        from tasks.engine import TaskStore
        store = TaskStore()
        try:
            stats = store.stats()
            pending = store.list(status="pending")
        finally:
            store.close()
        return {"available": True, "stats": stats, "pending_count": len(pending),
                "pending": pending}
    except Exception:
        return {"available": False, "stats": {}, "pending_count": 0, "pending": []}
