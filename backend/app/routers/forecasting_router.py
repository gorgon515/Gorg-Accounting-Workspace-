"""HELIOS Financial Forecasting & Scenario Simulation API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


class RetirementRequest(BaseModel):
    current_assets: float
    monthly_contribution: float
    years: int = 30
    annual_return: float = 0.07


class ScenarioRequest(BaseModel):
    levers: dict
    label: str = "scenario"


class SensitivityRequest(BaseModel):
    levers: dict
    vary: Optional[list[str]] = None
    step_pct: float = 10.0


@router.get("/metric/{metric}")
def forecast_metric(metric: str, months: int = 12):
    try:
        from forecasting.engine import get_forecast_engine
        return get_forecast_engine().forecast_metric(metric, months)
    except Exception as e:
        return {"error": str(e)}


@router.get("/all")
def forecast_all(months: int = 12):
    try:
        from forecasting.engine import get_forecast_engine
        return get_forecast_engine().forecast_all(months)
    except Exception as e:
        return {"error": str(e)}


@router.post("/retirement")
def retirement(req: RetirementRequest):
    try:
        from forecasting.engine import get_forecast_engine
        return get_forecast_engine().retirement_projection(
            req.current_assets, req.monthly_contribution, req.years, req.annual_return
        )
    except Exception as e:
        return {"error": str(e)}


@router.post("/scenario")
def scenario(req: ScenarioRequest):
    try:
        from forecasting.scenarios import get_scenario_simulator
        return get_scenario_simulator().simulate(req.levers, req.label)
    except Exception as e:
        return {"error": str(e)}


@router.post("/sensitivity")
def sensitivity(req: SensitivityRequest):
    try:
        from forecasting.scenarios import get_scenario_simulator
        return get_scenario_simulator().sensitivity(req.levers, req.vary, req.step_pct)
    except Exception as e:
        return {"error": str(e)}


@router.get("/levers")
def levers():
    try:
        from forecasting.scenarios import get_scenario_simulator
        return {"levers": get_scenario_simulator().levers()}
    except Exception as e:
        return {"error": str(e)}
