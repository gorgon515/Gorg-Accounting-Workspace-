"""
Quant Research Lab — strategy/signal creation & versioning, research notebooks,
hypothesis & experiment tracking, research history and performance attribution.

Strategies hold signal definitions and link to backtest runs. Versioning keeps a
full history so research is reproducible and auditable. Feeds the Knowledge
Engine with research artifacts.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

_DB = Path(".data/quant_lab.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS strategy (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'signal',
            definition TEXT DEFAULT '{}',
            version INTEGER DEFAULT 1,
            status TEXT DEFAULT 'research',
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS strategy_version (
            id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            definition TEXT DEFAULT '{}',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS hypothesis (
            id TEXT PRIMARY KEY,
            statement TEXT NOT NULL,
            rationale TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            evidence TEXT DEFAULT '[]',
            conclusion TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS experiment (
            id TEXT PRIMARY KEY,
            strategy_id TEXT DEFAULT '',
            hypothesis_id TEXT DEFAULT '',
            name TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            result TEXT DEFAULT '{}',
            backtest_id TEXT DEFAULT '',
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notebook (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            strategy_id TEXT DEFAULT '',
            cells TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


class QuantLab:
    def __init__(self):
        _conn().close()

    # ── strategies & versioning ─────────────────────────────────────────────

    def create_strategy(self, name: str, description: str = "", category: str = "signal",
                        definition: Optional[dict] = None, tags: Optional[list] = None) -> dict:
        sid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO strategy(id, name, description, category, definition, tags)
               VALUES(?,?,?,?,?,?)""",
            (sid, name, description, category, json.dumps(definition or {}), json.dumps(tags or [])))
        conn.execute(
            "INSERT INTO strategy_version(id, strategy_id, version, definition, note) VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), sid, 1, json.dumps(definition or {}), "initial"))
        conn.commit()
        conn.close()
        self._ingest_knowledge(name, description, "strategy")
        return self.get_strategy(sid)

    def update_strategy(self, strategy_id: str, definition: dict, note: str = "") -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT version FROM strategy WHERE id=?", (strategy_id,)).fetchone()
        if not row:
            conn.close()
            return None
        new_version = row["version"] + 1
        conn.execute(
            "UPDATE strategy SET definition=?, version=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(definition), new_version, strategy_id))
        conn.execute(
            "INSERT INTO strategy_version(id, strategy_id, version, definition, note) VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), strategy_id, new_version, json.dumps(definition), note))
        conn.commit()
        conn.close()
        return self.get_strategy(strategy_id)

    def get_strategy(self, strategy_id: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM strategy WHERE id=?", (strategy_id,)).fetchone()
        conn.close()
        return self._fmt_strategy(row) if row else None

    def list_strategies(self, status: Optional[str] = None, category: Optional[str] = None) -> list[dict]:
        conn = _conn()
        clauses, params = [], []
        if status:
            clauses.append("status=?"); params.append(status)
        if category:
            clauses.append("category=?"); params.append(category)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(f"SELECT * FROM strategy {where} ORDER BY updated_at DESC", params).fetchall()
        conn.close()
        return [self._fmt_strategy(r) for r in rows]

    def strategy_versions(self, strategy_id: str) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM strategy_version WHERE strategy_id=? ORDER BY version DESC", (strategy_id,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["definition"] = json.loads(d["definition"])
            except Exception:
                d["definition"] = {}
            out.append(d)
        return out

    def set_strategy_status(self, strategy_id: str, status: str) -> Optional[dict]:
        conn = _conn()
        conn.execute("UPDATE strategy SET status=?, updated_at=datetime('now') WHERE id=?",
                     (status, strategy_id))
        conn.commit()
        conn.close()
        return self.get_strategy(strategy_id)

    def _fmt_strategy(self, row) -> dict:
        d = dict(row)
        for f in ("definition",):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = {}
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = []
        return d

    # ── signal generation ───────────────────────────────────────────────────

    def generate_signal(self, symbol: str, definition: dict) -> dict:
        """
        Generate a signal series for a symbol from a strategy definition.
        Supported kinds: 'sma_cross', 'momentum', 'mean_reversion', 'factor'.
        Returns aligned signals + asset returns for backtesting.
        """
        from financial_hub.store import get_financial_hub
        bars = get_financial_hub().get_prices(symbol, limit=definition.get("lookback", 252))
        closes = [b["close"] for b in reversed(bars) if b.get("close") is not None]
        if len(closes) < 20:
            return {"error": "insufficient price history", "symbol": symbol}
        p = np.asarray(closes, dtype=float)
        rets = list(np.diff(p) / p[:-1])
        kind = definition.get("kind", "momentum")
        signals = self._signal_series(kind, p, definition)
        # align signals to returns (signal acts on next period — shift)
        sig = signals[:-1] if len(signals) == len(p) else signals
        sig = sig[-len(rets):]
        return {"symbol": symbol, "kind": kind, "signals": list(map(float, sig)),
                "asset_returns": rets, "n": len(rets)}

    def _signal_series(self, kind: str, prices: np.ndarray, d: dict) -> np.ndarray:
        n = len(prices)
        if kind == "sma_cross":
            fast = d.get("fast", 20); slow = d.get("slow", 50)
            sf = self._sma(prices, fast); ss = self._sma(prices, slow)
            return np.where(sf > ss, 1.0, 0.0)
        if kind == "mean_reversion":
            window = d.get("window", 20)
            sma = self._sma(prices, window)
            std = self._rolling_std(prices, window)
            z = np.zeros(n)
            mask = std > 0
            z[mask] = (prices[mask] - sma[mask]) / std[mask]
            # buy when oversold (z<-1), short when overbought (z>1)
            return np.clip(-z, -1.0, 1.0)
        if kind == "momentum":
            window = d.get("window", 60)
            mom = np.zeros(n)
            for t in range(window, n):
                mom[t] = 1.0 if prices[t] > prices[t - window] else 0.0
            return mom
        # default: always long
        return np.ones(n)

    def _sma(self, p: np.ndarray, w: int) -> np.ndarray:
        out = np.copy(p)
        for t in range(len(p)):
            lo = max(0, t - w + 1)
            out[t] = np.mean(p[lo:t + 1])
        return out

    def _rolling_std(self, p: np.ndarray, w: int) -> np.ndarray:
        out = np.zeros(len(p))
        for t in range(len(p)):
            lo = max(0, t - w + 1)
            seg = p[lo:t + 1]
            out[t] = np.std(seg, ddof=1) if len(seg) > 1 else 0.0
        return out

    # ── hypotheses & experiments ────────────────────────────────────────────

    def create_hypothesis(self, statement: str, rationale: str = "") -> dict:
        hid = str(uuid.uuid4())
        conn = _conn()
        conn.execute("INSERT INTO hypothesis(id, statement, rationale) VALUES(?,?,?)",
                     (hid, statement, rationale))
        conn.commit()
        conn.close()
        return self.get_hypothesis(hid)

    def get_hypothesis(self, hid: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM hypothesis WHERE id=?", (hid,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        try:
            d["evidence"] = json.loads(d["evidence"])
        except Exception:
            d["evidence"] = []
        return d

    def resolve_hypothesis(self, hid: str, conclusion: str, status: str = "confirmed") -> Optional[dict]:
        conn = _conn()
        conn.execute(
            "UPDATE hypothesis SET status=?, conclusion=?, resolved_at=datetime('now') WHERE id=?",
            (status, conclusion, hid))
        conn.commit()
        conn.close()
        return self.get_hypothesis(hid)

    def list_hypotheses(self, status: Optional[str] = None) -> list[dict]:
        conn = _conn()
        if status:
            rows = conn.execute("SELECT * FROM hypothesis WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM hypothesis ORDER BY created_at DESC").fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["evidence"] = json.loads(d["evidence"])
            except Exception:
                d["evidence"] = []
            out.append(d)
        return out

    def run_experiment(self, name: str, symbol: str, definition: dict,
                       strategy_id: str = "", hypothesis_id: str = "",
                       commission_bps: float = 1.0, slippage_bps: float = 5.0) -> dict:
        """Generate signals, backtest, persist the experiment + result."""
        sig = self.generate_signal(symbol, definition)
        if "error" in sig:
            return sig
        from backtesting.engine import get_backtester
        bt = get_backtester().run(
            name=f"{name} · {symbol}", signals=sig["signals"], asset_returns=sig["asset_returns"],
            strategy_id=strategy_id, symbol=symbol,
            commission_bps=commission_bps, slippage_bps=slippage_bps,
            benchmark_returns=sig["asset_returns"])
        eid = str(uuid.uuid4())
        result = {"metrics": bt["metrics"], "backtest_id": bt.get("id")}
        conn = _conn()
        conn.execute(
            """INSERT INTO experiment(id, strategy_id, hypothesis_id, name, params, result, backtest_id)
               VALUES(?,?,?,?,?,?,?)""",
            (eid, strategy_id, hypothesis_id, name, json.dumps(definition),
             json.dumps(result), bt.get("id", "")))
        conn.commit()
        conn.close()
        return {"id": eid, "name": name, "symbol": symbol, "metrics": bt["metrics"],
                "backtest_id": bt.get("id"), "benchmark": bt.get("benchmark")}

    def list_experiments(self, strategy_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = _conn()
        if strategy_id:
            rows = conn.execute(
                "SELECT * FROM experiment WHERE strategy_id=? ORDER BY created_at DESC LIMIT ?",
                (strategy_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM experiment ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            for f in ("params", "result"):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = {}
            out.append(d)
        return out

    # ── notebooks ───────────────────────────────────────────────────────────

    def create_notebook(self, title: str, content: str = "", strategy_id: str = "",
                        cells: Optional[list] = None) -> dict:
        nid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            "INSERT INTO notebook(id, title, content, strategy_id, cells) VALUES(?,?,?,?,?)",
            (nid, title, content, strategy_id, json.dumps(cells or [])))
        conn.commit()
        conn.close()
        return self.get_notebook(nid)

    def get_notebook(self, nid: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM notebook WHERE id=?", (nid,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        try:
            d["cells"] = json.loads(d["cells"])
        except Exception:
            d["cells"] = []
        return d

    def list_notebooks(self) -> list[dict]:
        conn = _conn()
        rows = conn.execute("SELECT id, title, strategy_id, created_at, updated_at FROM notebook ORDER BY updated_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _ingest_knowledge(self, title: str, content: str, kind: str):
        try:
            from knowledge.engine import get_knowledge_engine
            get_knowledge_engine().ingest(title=f"[Quant] {title}", content=content or title,
                                          domain="markets", kind="insight", source="quant_lab")
        except Exception:
            pass

    def stats(self) -> dict:
        conn = _conn()
        strategies = conn.execute("SELECT COUNT(*) FROM strategy").fetchone()[0]
        experiments = conn.execute("SELECT COUNT(*) FROM experiment").fetchone()[0]
        hypotheses = conn.execute("SELECT COUNT(*) FROM hypothesis WHERE status='open'").fetchone()[0]
        notebooks = conn.execute("SELECT COUNT(*) FROM notebook").fetchone()[0]
        conn.close()
        return {"strategies": strategies, "experiments": experiments,
                "open_hypotheses": hypotheses, "notebooks": notebooks}


_instance: Optional[QuantLab] = None


def get_quant_lab() -> QuantLab:
    global _instance
    if _instance is None:
        _instance = QuantLab()
    return _instance
