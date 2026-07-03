"""Shared text/answer normalization and small time helpers.

Single source of truth for answer comparison across lesson mastery tests
and grammar drills (Phase 2 audit: this logic was duplicated).
"""
from __future__ import annotations

from datetime import datetime, timezone


def normalize_answer(text: str) -> str:
    """Normalize a learner-submitted answer for comparison: trim, lowercase,
    fold ё→е (Russians themselves type е for ё), collapse inner whitespace."""
    return " ".join(text.strip().lower().replace("ё", "е").split())


def answer_matches(submitted: str, answer: str, accept: list[str] | None = None) -> bool:
    normalized = normalize_answer(submitted)
    return normalized in [normalize_answer(a) for a in [answer, *(accept or [])]]


def ensure_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat stored timestamps as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
