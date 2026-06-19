"""Risk Analytics Platform API — Phase 14."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/risk-analytics", tags=["risk-analytics"])


class RiskAnalyze(BaseModel):
    holdings: list[dict]   # [{symbol, weight}, ...]
    name: str = ""
    portfolio_id: str = ""
    level: float = 0.95


class StressTest(BaseModel):
    holdings: list[dict]
    scenario_id: Optional[str] = None


class ScenarioAnalysis(BaseModel):
    holdings: list[dict]
    shocks: dict


@router.post("/analyze")
def analyze(body: RiskAnalyze):
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().analyze(body.holdings, body.name, body.portfolio_id, body.level)


@router.post("/stress-test")
def stress_test(body: StressTest):
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().stress_test(body.holdings, body.scenario_id)


@router.post("/scenario")
def scenario(body: ScenarioAnalysis):
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().scenario_analysis(body.holdings, body.shocks)


@router.post("/factor-exposure")
def factor_exposure(body: RiskAnalyze):
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().factor_exposure(body.holdings)


@router.get("/scenarios")
def scenarios():
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().scenarios()


@router.get("/reports")
def list_reports(portfolio_id: Optional[str] = None, limit: int = 20):
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().list_reports(portfolio_id=portfolio_id, limit=limit)


@router.get("/stats")
def stats():
    from risk_analytics.engine import get_risk_engine
    return get_risk_engine().stats()
