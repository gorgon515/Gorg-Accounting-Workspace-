"""Base connector interface all providers implement."""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ConnectorMeta:
    id: str
    name: str
    kind: str
    category: str
    version: str = "1.0.0"
    description: str = ""
    auth_type: str = "none"       # none | api_key | oauth2 | basic
    requires_credential: bool = False
    permissions: list[str] = field(default_factory=list)
    poll_interval_sec: int = 3600


@dataclass
class FetchResult:
    connector_id: str
    status: str                   # ok | error | partial | offline
    items: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: float = 0.0


class BaseConnector(ABC):
    meta: ConnectorMeta

    def fetch(self, **kwargs) -> FetchResult:
        t0 = time.perf_counter()
        try:
            items = self._fetch(**kwargs)
            return FetchResult(
                connector_id=self.meta.id,
                status="ok",
                items=items,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return FetchResult(
                connector_id=self.meta.id,
                status="error",
                error=str(exc),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    @abstractmethod
    def _fetch(self, **kwargs) -> list[dict]:
        """Return a list of fetched items as dicts."""

    def health_check(self) -> dict:
        t0 = time.perf_counter()
        try:
            self._health()
            return {"healthy": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        except Exception as exc:
            return {"healthy": False, "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "error": str(exc)}

    def _health(self):
        """Override to do a lightweight health probe. Default: do nothing."""
