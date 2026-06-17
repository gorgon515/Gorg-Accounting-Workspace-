"""Pydantic request schemas for the sidecar. Responses are plain JSON dicts
returned by the service layer (which is pydantic-free and unit-tested)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class PriceInput(BaseModel):
    """Either a symbol to fetch, or an explicit close-price series (offline)."""
    symbol: Optional[str] = None
    prices: Optional[list[float]] = None
    range: str = "6mo"

    @model_validator(mode="after")
    def _need_one(self):
        if not self.symbol and not self.prices:
            raise ValueError("provide either 'symbol' or 'prices'")
        if self.prices is not None and len(self.prices) < 2:
            raise ValueError("'prices' needs at least 2 points")
        return self


class FactorRequest(BaseModel):
    symbol: str
    fundamentals: dict[str, float] = Field(default_factory=dict)
    prices: Optional[list[float]] = None
    range: str = "1y"


class RiskRequest(BaseModel):
    symbol: Optional[str] = None
    prices: Optional[list[float]] = None
    benchmark_symbol: Optional[str] = None
    benchmark_prices: Optional[list[float]] = None
    risk_free: float = 0.0
    range: str = "1y"

    @model_validator(mode="after")
    def _need_one(self):
        if not self.symbol and not self.prices:
            raise ValueError("provide either 'symbol' or 'prices'")
        return self


class PortfolioRequest(BaseModel):
    holdings: list[dict[str, Any]]
    benchmark_symbol: Optional[str] = None
    benchmark_prices: Optional[list[float]] = None


class MemoRequest(BaseModel):
    issue: str
    facts: str
    topic: str
    conclusion: Optional[str] = None


# ---- Phase 4: intelligence engines ----
class MemoFullRequest(BaseModel):
    facts: str
    issue: str
    topic: str
    alternatives: Optional[list[str]] = None
    conclusion: Optional[str] = None


class ChecklistRequest(BaseModel):
    topic: str


class FundamentalsRequest(BaseModel):
    symbol: str
    fundamentals: dict[str, Any] = Field(default_factory=dict)
    history: Optional[dict[str, list[float]]] = None


class SignalRequest(BaseModel):
    symbol: str
    prices: Optional[list[float]] = None
    fundamentals: Optional[dict[str, Any]] = None
    benchmark_prices: Optional[list[float]] = None
    benchmark_symbol: Optional[str] = None
    sector: Optional[str] = None
    range: str = "1y"


class MarketBriefingRequest(BaseModel):
    quotes: Optional[list[dict[str, Any]]] = None
    symbols: Optional[list[str]] = None
    portfolio: Optional[list[dict[str, Any]]] = None
    watchlist_changes: Optional[list[str]] = None
    earnings: Optional[list[dict[str, Any]]] = None
    macro: Optional[list[dict[str, Any]]] = None


class WorkflowSpecRequest(BaseModel):
    name: str = "HELIOS Workflow"
    schedule: str = "0 7 * * *"
    collect_url: Optional[str] = None
    email_to: Optional[str] = None
    subject: Optional[str] = None
    transform_js: Optional[str] = None
    kind: Optional[str] = None  # 'accounting_briefing' for the flagship example


# ---- Phase 5 — chief of staff / operational layer ----
class TaskCreate(BaseModel):
    title: str
    notes: str = ""
    project: Optional[str] = None
    priority: int = 3
    due: Optional[str] = None
    recurrence: str = "none"
    depends_on: Optional[list[str]] = None
    category: Optional[str] = None


class TaskUpdate(BaseModel):
    id: str
    fields: dict[str, Any] = Field(default_factory=dict)


class GoalCreate(BaseModel):
    title: str
    category: str = "personal"
    target: float = 100
    unit: str = "%"
    deadline: Optional[str] = None
    milestones: Optional[list[dict[str, Any]]] = None


class ProgressUpdate(BaseModel):
    id: str
    progress: float


class JobCreate(BaseModel):
    name: str
    handler: str
    kind: str
    spec: str
    tz: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class EmailBatch(BaseModel):
    emails: list[dict[str, Any]] = Field(default_factory=list)


class CalendarPlanRequest(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    work_start: str = "09:00"
    work_end: str = "18:00"


class CosContext(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
    emails: list[dict[str, Any]] = Field(default_factory=list)
    tasks: Optional[list[dict[str, Any]]] = None
    goals: Optional[list[dict[str, Any]]] = None
    market: Optional[dict[str, Any]] = None
    accounting: Optional[dict[str, Any]] = None
    goals_progress: Optional[list[dict[str, Any]]] = None
    portfolio: Optional[dict[str, Any]] = None
