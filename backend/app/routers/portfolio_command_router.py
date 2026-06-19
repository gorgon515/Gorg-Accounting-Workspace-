"""
Portfolio Command Center API — flagship aggregated dashboard for Phase 14.

Assembles a single live snapshot across portfolios, risk, performance, factor &
macro exposure, watchlists, research, theses, signals, opportunities and
warnings — pulling from every Phase 14 engine plus Phase 13 signals.
"""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/portfolio-command", tags=["portfolio-command"])


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e), **(default if isinstance(default, dict) else {})}


@router.get("/overview")
def overview():
    """Single aggregated payload for the Portfolio Command Center HUD."""
    out: dict = {}

    # Portfolios + best/worst by Sharpe
    def _portfolios():
        from portfolio.engine import get_portfolio_engine
        pe = get_portfolio_engine()
        portfolios = pe.list()
        return {"count": len(portfolios),
                "portfolios": [{"id": p["id"], "name": p["name"], "method": p["method"],
                                "stats": p.get("stats", {})} for p in portfolios[:10]],
                "stats": pe.stats()}
    out["portfolios"] = _safe(_portfolios, {"count": 0, "portfolios": []})

    # Macro regime
    def _macro():
        from macro.engine import get_macro_engine
        return get_macro_engine().classify_regime(persist=False)
    out["macro"] = _safe(_macro, {})

    # Risk summary (most recent reports)
    def _risk():
        from risk_analytics.engine import get_risk_engine
        re = get_risk_engine()
        reports = re.list_reports(limit=5)
        return {"recent_reports": [{"name": r.get("name"), "health_score": r.get("health_score"),
                                    "created_at": r.get("created_at")} for r in reports],
                "stats": re.stats()}
    out["risk"] = _safe(_risk, {})

    # Theses
    def _theses():
        from thesis.engine import get_thesis_engine
        te = get_thesis_engine()
        return {"active": te.list(status="active")[:8], "stats": te.stats()}
    out["theses"] = _safe(_theses, {})

    # Signals (market + alt data)
    def _signals():
        out_sig = {}
        try:
            from market_intel.signals import get_signal_detector
            out_sig["market"] = get_signal_detector().list_signals(status="active", limit=8)
        except Exception:
            out_sig["market"] = []
        try:
            from altdata.platform import get_altdata_platform
            out_sig["alternative"] = get_altdata_platform().list_signals(limit=8)
        except Exception:
            out_sig["alternative"] = []
        return out_sig
    out["signals"] = _safe(_signals, {})

    # Watchlist
    def _watchlist():
        from financial_hub.store import get_financial_hub
        return get_financial_hub().get_watchlist()
    out["watchlist"] = _safe(_watchlist, [])

    # Research queue (quant lab)
    def _research():
        from quant_lab.lab import get_quant_lab
        lab = get_quant_lab()
        return {"strategies": lab.list_strategies(status="research")[:8], "stats": lab.stats()}
    out["research"] = _safe(_research, {})

    # Warnings: low-health portfolios + recession signal
    warnings = []
    macro = out.get("macro", {})
    if isinstance(macro, dict) and macro.get("yield_curve", {}).get("signal") == "recession_warning":
        warnings.append({"type": "macro", "message": "Yield curve inverted — recession signal active",
                         "severity": "high"})
    for r in out.get("risk", {}).get("recent_reports", []):
        if r.get("health_score") is not None and r["health_score"] < 50:
            warnings.append({"type": "risk", "message": f"{r['name']} portfolio health {r['health_score']}/100",
                             "severity": "high"})
    out["warnings"] = warnings

    return out


@router.get("/stats")
def stats():
    result = {}
    for name, getter in [
        ("quant_lab", "quant_lab.lab:get_quant_lab"),
        ("backtesting", "backtesting.engine:get_backtester"),
        ("portfolio", "portfolio.engine:get_portfolio_engine"),
        ("risk", "risk_analytics.engine:get_risk_engine"),
        ("factors", "quant_lab.factors:get_factor_library"),
        ("altdata", "altdata.platform:get_altdata_platform"),
        ("thesis", "thesis.engine:get_thesis_engine"),
        ("earnings", "earnings.engine:get_earnings_engine"),
        ("macro", "macro.engine:get_macro_engine"),
    ]:
        try:
            mod_path, fn = getter.split(":")
            import importlib
            mod = importlib.import_module(mod_path)
            result[name] = getattr(mod, fn)().stats()
        except Exception as e:
            result[name] = {"error": str(e)}
    return result
