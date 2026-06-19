"""
Portfolio Construction Engine — build, optimize, rebalance, and persist
portfolios. Pulls price history from the Financial Data Hub, computes optimal
weights, models rebalancing turnover, and supports constraint modeling.

All outputs are advisory. Rebalance proposals route to the approval workflow;
nothing executes automatically.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, Sequence
import numpy as np

from . import optimize as O

_DB = Path(".data/portfolio.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            method TEXT DEFAULT 'equal_weight',
            symbols TEXT DEFAULT '[]',
            weights TEXT DEFAULT '{}',
            constraints TEXT DEFAULT '{}',
            stats TEXT DEFAULT '{}',
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS rebalance_proposal (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            current_weights TEXT DEFAULT '{}',
            target_weights TEXT DEFAULT '{}',
            trades TEXT DEFAULT '[]',
            turnover REAL DEFAULT 0.0,
            est_cost REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


def _returns_matrix(symbols: Sequence[str], lookback: int = 252) -> tuple[list[str], np.ndarray]:
    """Build an aligned (n_assets x n_periods) return matrix from the hub."""
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    series = {}
    for sym in symbols:
        bars = hub.get_prices(sym, limit=lookback)
        closes = [b.get("close") for b in reversed(bars) if b.get("close") is not None]
        if len(closes) >= 3:
            arr = np.asarray(closes, dtype=float)
            rets = np.diff(arr) / arr[:-1]
            series[sym] = rets
    if not series:
        return [], np.empty((0, 0))
    min_len = min(len(v) for v in series.values())
    if min_len < 2:
        return [], np.empty((0, 0))
    valid = [s for s in symbols if s in series]
    matrix = np.vstack([series[s][-min_len:] for s in valid])
    return valid, matrix


class PortfolioEngine:
    def __init__(self):
        _conn().close()

    def construct(self, name: str, symbols: Sequence[str], method: str = "equal_weight",
                  description: str = "", lookback: int = 252,
                  constraints: Optional[dict] = None, risk_free: float = 0.0,
                  market_weights: Optional[Sequence[float]] = None,
                  views: Optional[dict] = None, persist: bool = True) -> dict:
        valid, matrix = _returns_matrix(symbols, lookback)
        if matrix.size == 0:
            # Fall back to equal weight over requested symbols when no price data.
            n = len(symbols)
            weights = {s: round(1.0 / n, 4) for s in symbols} if n else {}
            result = {"name": name, "method": "equal_weight", "symbols": list(symbols),
                      "weights": weights, "stats": {"note": "no price history — equal weighted"}}
            if persist:
                result["id"] = self._save(name, description, "equal_weight", symbols, weights, constraints or {}, result["stats"])
            return result

        kwargs = {"risk_free": risk_free}
        if market_weights is not None:
            kwargs["market_weights"] = np.asarray(market_weights, dtype=float)
        if views is not None:
            kwargs["views"] = views
        w = O.optimize(method, matrix, **kwargs)

        if constraints:
            w = O.apply_constraints(
                w,
                max_weight=constraints.get("max_weight"),
                min_weight=constraints.get("min_weight"),
                group_caps=self._resolve_group_caps(valid, constraints.get("group_caps")),
            )

        weights = {valid[i]: round(float(w[i]), 4) for i in range(len(valid))}
        stats = self._portfolio_stats(valid, matrix, w)
        result = {"name": name, "method": method, "symbols": valid,
                  "weights": weights, "stats": stats}
        if persist:
            result["id"] = self._save(name, description, method, valid, weights, constraints or {}, stats)
        return result

    def _resolve_group_caps(self, symbols: list[str], group_caps: Optional[list]) -> Optional[list]:
        if not group_caps:
            return None
        resolved = []
        for g in group_caps:
            members = [symbols.index(s) for s in g.get("symbols", []) if s in symbols]
            if members:
                resolved.append({"members": members, "cap": g.get("cap", 1.0)})
        return resolved or None

    def _portfolio_stats(self, symbols: list[str], matrix: np.ndarray, w: np.ndarray) -> dict:
        from backtesting import metrics as M
        port_returns = w @ matrix  # n_periods
        cov = np.cov(matrix, ddof=1) if matrix.shape[1] > 1 else np.eye(len(symbols)) * 1e-6
        ann_vol = float(np.sqrt(w @ (cov * 252) @ w))
        # Risk contributions
        port_var = float(w @ (cov * 252) @ w)
        mrc = (cov * 252) @ w
        rc = w * mrc
        risk_contrib = {symbols[i]: round(float(rc[i] / port_var), 4) if port_var > 0 else 0.0
                        for i in range(len(symbols))}
        return {
            "expected_return": round(float(np.mean(port_returns) * 252), 4),
            "volatility": round(ann_vol, 4),
            "sharpe": M.sharpe(list(port_returns)),
            "max_drawdown": M.max_drawdown(list(port_returns)),
            "effective_n": round(float(1.0 / np.sum(w ** 2)), 2),
            "risk_contributions": risk_contrib,
            "concentration": round(float(np.sum(w ** 2)), 4),  # Herfindahl
        }

    def _save(self, name, description, method, symbols, weights, constraints, stats) -> str:
        pid = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO portfolio(id, name, description, method, symbols, weights, constraints, stats)
               VALUES(?,?,?,?,?,?,?,?)""",
            (pid, name, description, method, json.dumps(list(symbols)),
             json.dumps(weights), json.dumps(constraints), json.dumps(stats)),
        )
        conn.commit()
        conn.close()
        return pid

    def get(self, portfolio_id: str) -> Optional[dict]:
        conn = _conn()
        row = conn.execute("SELECT * FROM portfolio WHERE id=?", (portfolio_id,)).fetchone()
        conn.close()
        return self._fmt(row) if row else None

    def list(self, status: str = "active", limit: int = 50) -> list[dict]:
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM portfolio WHERE status=? ORDER BY updated_at DESC LIMIT ?",
            (status, limit)).fetchall()
        conn.close()
        return [self._fmt(r) for r in rows]

    def _fmt(self, row) -> dict:
        d = dict(row)
        for f in ("symbols",):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = []
        for f in ("weights", "constraints", "stats"):
            try:
                d[f] = json.loads(d[f])
            except Exception:
                d[f] = {}
        return d

    def propose_rebalance(self, portfolio_id: str, lookback: int = 252,
                          commission_bps: float = 1.0, slippage_bps: float = 5.0) -> dict:
        """Re-optimize and produce a rebalance proposal (advisory; needs approval)."""
        pf = self.get(portfolio_id)
        if not pf:
            return {"error": "portfolio not found"}
        current = pf["weights"]
        fresh = self.construct(pf["name"], pf["symbols"], pf["method"],
                               lookback=lookback, constraints=pf.get("constraints"),
                               persist=False)
        target = fresh["weights"]
        all_syms = sorted(set(current) | set(target))
        trades = []
        turnover = 0.0
        for s in all_syms:
            cur = current.get(s, 0.0)
            tgt = target.get(s, 0.0)
            delta = round(tgt - cur, 4)
            turnover += abs(delta)
            if abs(delta) > 0.0001:
                trades.append({"symbol": s, "from": cur, "to": tgt, "delta": delta,
                               "action": "buy" if delta > 0 else "sell"})
        est_cost = turnover * (commission_bps + slippage_bps) / 10000.0
        prop_id = str(uuid.uuid4())
        conn = _conn()
        conn.execute(
            """INSERT INTO rebalance_proposal(id, portfolio_id, current_weights, target_weights,
               trades, turnover, est_cost) VALUES(?,?,?,?,?,?,?)""",
            (prop_id, portfolio_id, json.dumps(current), json.dumps(target),
             json.dumps(trades), round(turnover, 4), round(est_cost, 6)),
        )
        conn.commit()
        conn.close()
        return {"id": prop_id, "portfolio_id": portfolio_id, "trades": trades,
                "turnover": round(turnover, 4), "est_cost": round(est_cost, 6),
                "target_stats": fresh["stats"], "status": "pending"}

    def list_rebalances(self, portfolio_id: Optional[str] = None, status: str = "pending") -> list[dict]:
        conn = _conn()
        if portfolio_id:
            rows = conn.execute(
                "SELECT * FROM rebalance_proposal WHERE portfolio_id=? AND status=? ORDER BY created_at DESC",
                (portfolio_id, status)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rebalance_proposal WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            for f in ("current_weights", "target_weights", "trades"):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = {} if f != "trades" else []
            result.append(d)
        return result

    def methods(self) -> list[dict]:
        return [
            {"id": "equal_weight", "name": "Equal Weight", "needs_returns": False},
            {"id": "minimum_variance", "name": "Minimum Variance", "needs_returns": True},
            {"id": "maximum_sharpe", "name": "Maximum Sharpe", "needs_returns": True},
            {"id": "risk_parity", "name": "Risk Parity", "needs_returns": True},
            {"id": "hierarchical_risk_parity", "name": "Hierarchical Risk Parity", "needs_returns": True},
            {"id": "black_litterman", "name": "Black-Litterman", "needs_returns": True},
        ]

    def stats(self) -> dict:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM portfolio WHERE status='active'").fetchone()[0]
        rebal = conn.execute("SELECT COUNT(*) FROM rebalance_proposal WHERE status='pending'").fetchone()[0]
        conn.close()
        return {"active_portfolios": total, "pending_rebalances": rebal}


_instance: Optional[PortfolioEngine] = None


def get_portfolio_engine() -> PortfolioEngine:
    global _instance
    if _instance is None:
        _instance = PortfolioEngine()
    return _instance
