"""License edition definitions for HELIOS."""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class Edition:
    name: str
    max_seats: int
    features: FrozenSet[str]
    price_monthly_usd: float


EDITIONS = {
    "professional": Edition(
        name="professional",
        max_seats=1,
        features=frozenset(["accounting", "vault", "backup", "markets", "assistant", "reports"]),
        price_monthly_usd=49.0,
    ),
    "firm": Edition(
        name="firm",
        max_seats=10,
        features=frozenset([
            "accounting", "vault", "backup", "markets", "assistant", "reports",
            "workspaces", "team_roles", "audit_logs", "api_access",
        ]),
        price_monthly_usd=199.0,
    ),
    "enterprise": Edition(
        name="enterprise",
        max_seats=999,
        features=frozenset([
            "accounting", "vault", "backup", "markets", "assistant", "reports",
            "workspaces", "team_roles", "audit_logs", "api_access",
            "sso", "custom_plugins", "priority_support", "sla", "white_label",
        ]),
        price_monthly_usd=999.0,
    ),
}


def get_edition(name: str) -> Edition:
    if name not in EDITIONS:
        raise ValueError(f"Unknown edition: {name}")
    return EDITIONS[name]


def list_editions() -> list[dict]:
    return [
        {
            "name": e.name,
            "max_seats": e.max_seats,
            "features": sorted(e.features),
            "price_monthly_usd": e.price_monthly_usd,
        }
        for e in EDITIONS.values()
    ]
