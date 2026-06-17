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
