"""Adaptive spaced-repetition engine.

Implements a two-component memory model in the spirit of FSRS:

* **Stability (S)** — how many days it takes for recall probability to
  decay to 90%. Grows with each successful review; the growth is larger
  when the review happened at a lower retrievability (desirable difficulty).
* **Difficulty (D)** — an item-specific 1..10 scalar that dampens
  stability growth for intrinsically hard items and is nudged by ratings.
* **Retrievability (R)** — predicted recall probability after `t` days:
  ``R(t) = exp(ln(0.9) * t / S)``, i.e. R(S) = 0.9 by construction.

The scheduler answers "when should this card come back so recall
probability at review time equals the target retention?" — solving the
same equation for t:  ``t = S * ln(target) / ln(0.9)``.

Ratings follow the Anki/FSRS convention: 1 Again, 2 Hard, 3 Good, 4 Easy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings

LN_09 = math.log(0.9)

# Initial stability (days) by first rating: an item you immediately knew
# well starts with a much longer memory half-life.
INITIAL_STABILITY = {1: 0.4, 2: 1.2, 3: 3.0, 4: 7.0}
# Initial difficulty by first rating.
INITIAL_DIFFICULTY = {1: 8.0, 2: 6.5, 3: 5.0, 4: 3.5}

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4


@dataclass
class SchedulingResult:
    stability: float
    difficulty: float
    interval_days: float
    due_at: datetime
    state: str
    predicted_retention: float


def retrievability(stability: float, elapsed_days: float) -> float:
    """Predicted recall probability after elapsed_days (memory decay)."""
    if stability <= 0:
        return 0.0
    return math.exp(LN_09 * elapsed_days / stability)


def interval_for_retention(stability: float, target_retention: float) -> float:
    """Days until predicted recall drops to target_retention."""
    return stability * math.log(target_retention) / LN_09


def _next_difficulty(difficulty: float, rating: int) -> float:
    # Mean-reverting update toward 5.0 keeps difficulty from saturating.
    delta = {AGAIN: 1.2, HARD: 0.5, GOOD: -0.1, EASY: -0.6}[rating]
    d = difficulty + delta
    d = d + 0.05 * (5.0 - d)  # mean reversion
    return min(10.0, max(1.0, d))


def _stability_after_success(
    stability: float, difficulty: float, r: float, rating: int
) -> float:
    """Stability growth on a successful review.

    Growth is proportional to (1 - R): reviewing right before you would
    have forgotten strengthens memory the most (spacing effect), while
    reviewing something at R≈1 barely helps. Difficulty dampens growth.
    """
    hard_penalty = 0.6 if rating == HARD else 1.0
    easy_bonus = 1.4 if rating == EASY else 1.0
    growth = (
        math.exp(0.9)
        * (11.0 - difficulty)
        / 10.0
        * math.pow(stability, -0.12)
        * (math.exp((1.0 - r) * 1.6) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return stability * (1.0 + max(growth, 0.02))


def _stability_after_lapse(stability: float, difficulty: float, r: float) -> float:
    """Forgetting doesn't reset memory to zero — relearning is faster than
    initial learning. New stability is a damped function of the old one."""
    s = (
        0.5
        * math.pow(difficulty, -0.4)
        * math.pow(stability + 1.0, 0.3)
        * math.exp((1.0 - r) * 0.8)
    )
    return max(0.1, min(s, stability))


def schedule(
    *,
    stability: float,
    difficulty: float,
    state: str,
    rating: int,
    elapsed_days: float,
    now: datetime | None = None,
    target_retention: float | None = None,
) -> SchedulingResult:
    """Compute the next memory state and due date for one review.

    `target_retention` overrides the configured default — the planner
    passes a per-user adaptive value (services/srs_planner.py).
    """
    if rating not in (AGAIN, HARD, GOOD, EASY):
        raise ValueError(f"rating must be 1..4, got {rating}")
    settings = get_settings()
    now = now or datetime.now(timezone.utc)

    if state == "new" or stability <= 0:
        r = 0.0
        new_s = INITIAL_STABILITY[rating]
        new_d = INITIAL_DIFFICULTY[rating]
        new_state = "learning" if rating == AGAIN else "review"
    else:
        r = retrievability(stability, elapsed_days)
        new_d = _next_difficulty(difficulty, rating)
        if rating == AGAIN:
            new_s = _stability_after_lapse(stability, new_d, r)
            new_state = "relearning"
        else:
            new_s = _stability_after_success(stability, new_d, r, rating)
            new_state = "review"

    interval = interval_for_retention(
        new_s, target_retention or settings.srs_target_retention
    )
    if new_state in ("learning", "relearning"):
        interval = min(interval, 1.0 / 144.0)  # ~10 minutes, same session
    interval = min(interval, float(settings.srs_max_interval_days))
    interval = max(interval, 1.0 / 144.0)

    return SchedulingResult(
        stability=new_s,
        difficulty=new_d,
        interval_days=interval,
        due_at=now + timedelta(days=interval),
        state=new_state,
        predicted_retention=r,
    )
