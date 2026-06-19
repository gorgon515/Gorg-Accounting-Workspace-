"""
Portfolio optimization methods — real numpy/scipy implementations.

Each optimizer takes an (n_assets x n_periods) return matrix (or precomputed
covariance / expected returns) and returns a weight vector that sums to 1.
Long-only by default with optional bounds; supports constraint modeling.
"""
from __future__ import annotations
from typing import Optional, Sequence
import numpy as np
from scipy.optimize import minimize


def _cov(returns: np.ndarray) -> np.ndarray:
    # returns: n_assets x n_periods
    if returns.shape[1] < 2:
        return np.eye(returns.shape[0]) * 1e-6
    return np.cov(returns, ddof=1)


def _annualize_cov(cov: np.ndarray, periods_per_year: int = 252) -> np.ndarray:
    return cov * periods_per_year


def _exp_returns(returns: np.ndarray, periods_per_year: int = 252) -> np.ndarray:
    return np.mean(returns, axis=1) * periods_per_year


def equal_weight(n: int) -> np.ndarray:
    return np.ones(n) / n


def minimum_variance(returns: np.ndarray, bounds: Optional[tuple] = None) -> np.ndarray:
    n = returns.shape[0]
    cov = _annualize_cov(_cov(returns))

    def obj(w):
        return float(w @ cov @ w)

    w0 = equal_weight(n)
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bnds = bounds or tuple((0.0, 1.0) for _ in range(n))
    res = minimize(obj, w0, method="SLSQP", bounds=bnds, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-10})
    return _clean(res.x if res.success else w0)


def maximum_sharpe(returns: np.ndarray, risk_free: float = 0.0,
                   bounds: Optional[tuple] = None) -> np.ndarray:
    n = returns.shape[0]
    cov = _annualize_cov(_cov(returns))
    mu = _exp_returns(returns)

    def neg_sharpe(w):
        ret = float(w @ mu)
        vol = float(np.sqrt(w @ cov @ w))
        if vol == 0:
            return 1e6
        return -(ret - risk_free) / vol

    w0 = equal_weight(n)
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bnds = bounds or tuple((0.0, 1.0) for _ in range(n))
    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bnds, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-10})
    return _clean(res.x if res.success else w0)


def risk_parity(returns: np.ndarray) -> np.ndarray:
    """Equal risk contribution portfolio (long-only)."""
    n = returns.shape[0]
    cov = _annualize_cov(_cov(returns))

    def obj(w):
        port_var = float(w @ cov @ w)
        if port_var <= 0:
            return 1e6
        mrc = cov @ w
        rc = w * mrc
        target = port_var / n
        return float(np.sum((rc - target) ** 2))

    w0 = equal_weight(n)
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bnds = tuple((1e-4, 1.0) for _ in range(n))
    res = minimize(obj, w0, method="SLSQP", bounds=bnds, constraints=cons,
                   options={"maxiter": 1000, "ftol": 1e-12})
    return _clean(res.x if res.success else w0)


def hierarchical_risk_parity(returns: np.ndarray) -> np.ndarray:
    """
    Lopez de Prado's HRP: cluster assets by correlation distance, then allocate
    via recursive bisection using inverse-variance weights. No matrix inversion.
    """
    n = returns.shape[0]
    if n == 1:
        return np.array([1.0])
    cov = _cov(returns)
    std = np.sqrt(np.diag(cov))
    std[std == 0] = 1e-8
    corr = cov / np.outer(std, std)
    corr = np.clip(corr, -1.0, 1.0)
    dist = np.sqrt(0.5 * (1.0 - corr))

    order = _quasi_diag(dist)
    weights = _recursive_bisection(cov, order)
    w = np.zeros(n)
    for idx, asset in enumerate(order):
        w[asset] = weights[idx]
    return _clean(w)


def _quasi_diag(dist: np.ndarray) -> list[int]:
    """Single-linkage clustering order via a simple agglomerative sort."""
    n = dist.shape[0]
    # Greedy nearest-neighbour chaining for a deterministic seriation.
    remaining = list(range(n))
    order = [remaining.pop(0)]
    while remaining:
        last = order[-1]
        nearest = min(remaining, key=lambda j: dist[last, j])
        order.append(nearest)
        remaining.remove(nearest)
    return order


def _recursive_bisection(cov: np.ndarray, order: list[int]) -> np.ndarray:
    w = np.ones(len(order))
    clusters = [list(range(len(order)))]
    while clusters:
        new_clusters = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            split = len(cl) // 2
            left, right = cl[:split], cl[split:]
            var_left = _cluster_var(cov, [order[i] for i in left])
            var_right = _cluster_var(cov, [order[i] for i in right])
            alloc = 1.0 - var_left / (var_left + var_right) if (var_left + var_right) > 0 else 0.5
            for i in left:
                w[i] *= alloc
            for i in right:
                w[i] *= (1.0 - alloc)
            new_clusters.extend([left, right])
        clusters = new_clusters
    return w


def _cluster_var(cov: np.ndarray, assets: list[int]) -> float:
    sub = cov[np.ix_(assets, assets)]
    ivp = 1.0 / np.diag(sub)
    ivp = ivp / ivp.sum()
    return float(ivp @ sub @ ivp)


def black_litterman(returns: np.ndarray, market_weights: Sequence[float],
                    views: Optional[dict] = None, tau: float = 0.05,
                    risk_aversion: float = 2.5) -> np.ndarray:
    """
    Black-Litterman: blend market-implied equilibrium returns with investor
    views. `views` = {"P": [[...]], "Q": [...], "omega_scale": float}.
    Returns the optimal (max-utility) weights.
    """
    n = returns.shape[0]
    cov = _annualize_cov(_cov(returns))
    w_mkt = np.asarray(market_weights, dtype=float)
    w_mkt = w_mkt / w_mkt.sum()
    # Implied equilibrium returns
    pi = risk_aversion * cov @ w_mkt

    if views and views.get("P") is not None and views.get("Q") is not None:
        P = np.asarray(views["P"], dtype=float)
        Q = np.asarray(views["Q"], dtype=float)
        omega_scale = views.get("omega_scale", 1.0)
        omega = np.diag(np.diag(P @ (tau * cov) @ P.T)) * omega_scale
        omega[omega == 0] = 1e-8
        tau_cov = tau * cov
        inv_tau_cov = np.linalg.inv(tau_cov)
        inv_omega = np.linalg.inv(omega)
        post_cov = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
        mu_bl = post_cov @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)
    else:
        mu_bl = pi

    # Max-utility weights: w = (λΣ)^-1 μ, normalized long-only
    try:
        w = np.linalg.inv(risk_aversion * cov) @ mu_bl
    except np.linalg.LinAlgError:
        w = w_mkt
    w = np.clip(w, 0.0, None)
    if w.sum() == 0:
        return _clean(w_mkt)
    return _clean(w / w.sum())


def _clean(w: np.ndarray) -> np.ndarray:
    w = np.clip(np.asarray(w, dtype=float), 0.0, None)
    s = w.sum()
    if s == 0:
        return equal_weight(len(w))
    return w / s


def apply_constraints(weights: np.ndarray, max_weight: Optional[float] = None,
                      min_weight: Optional[float] = None,
                      group_caps: Optional[list] = None) -> np.ndarray:
    """
    Apply box and group constraints, then renormalize. group_caps is a list of
    {"members": [idx...], "cap": float}.
    """
    w = np.asarray(weights, dtype=float).copy()
    if max_weight is not None:
        # Iteratively cap and redistribute excess to uncapped names so the
        # binding constraint still holds after renormalization.
        for _ in range(100):
            over = w > max_weight + 1e-12
            if not over.any():
                break
            excess = float(np.sum(w[over] - max_weight))
            w[over] = max_weight
            under = ~over
            pool = float(np.sum(w[under]))
            if pool <= 0:
                break
            w[under] += excess * (w[under] / pool)
    if min_weight is not None:
        w = np.maximum(w, min_weight)
    if group_caps:
        for g in group_caps:
            members = g.get("members", [])
            cap = g.get("cap", 1.0)
            total = w[members].sum()
            if total > cap and total > 0:
                w[members] *= cap / total
    s = w.sum()
    return w / s if s > 0 else equal_weight(len(w))


OPTIMIZERS = {
    "equal_weight": lambda r, **k: equal_weight(r.shape[0]),
    "minimum_variance": lambda r, **k: minimum_variance(r),
    "maximum_sharpe": lambda r, **k: maximum_sharpe(r, k.get("risk_free", 0.0)),
    "risk_parity": lambda r, **k: risk_parity(r),
    "hierarchical_risk_parity": lambda r, **k: hierarchical_risk_parity(r),
    "black_litterman": lambda r, **k: black_litterman(
        r, k.get("market_weights", equal_weight(r.shape[0])), k.get("views")),
}


def optimize(method: str, returns: np.ndarray, **kwargs) -> np.ndarray:
    fn = OPTIMIZERS.get(method)
    if not fn:
        raise ValueError(f"Unknown optimization method: {method}")
    return fn(returns, **kwargs)
