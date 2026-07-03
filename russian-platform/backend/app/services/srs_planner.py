"""Review planning intelligence on top of the core memory model.

Three concerns, all fed by the learner's own history:

* **Adaptive target retention** — struggling learners get shorter
  intervals (higher target), cruising learners get longer ones. This is
  the single highest-leverage personalization in an SRS.
* **Load balancing** — long intervals are nudged ±1 day toward the least
  loaded day so reviews arrive in an even stream instead of spikes
  (fatigue avoidance / workload optimization).
* **Forecast** — due counts per day, for the dashboard and daily planning.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Card, ReviewLog
from app.services.text_utils import ensure_utc


def adaptive_target_retention(db: Session, user_id: int) -> float:
    """Base target ±0.03 by recent accuracy, clamped to [0.85, 0.95].

    Accuracy = share of last-100 reviews not rated Again. Below 80% the
    learner is drowning — raise retention (shorter intervals, more
    support). Above 95% they can afford longer intervals.
    """
    settings = get_settings()
    base = settings.srs_target_retention
    recent = db.execute(
        select(ReviewLog.rating)
        .where(ReviewLog.user_id == user_id)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(100)
    ).scalars().all()
    if len(recent) < 20:
        return base
    accuracy = sum(1 for r in recent if r != 1) / len(recent)
    if accuracy < 0.80:
        target = base + 0.03
    elif accuracy > 0.95:
        target = base - 0.03
    else:
        target = base
    return min(0.95, max(0.85, target))


def balance_due_date(db: Session, user_id: int, due_at: datetime) -> datetime:
    """For intervals ≥ 3 days out, shift the due date within ±1 day to the
    least-loaded day. Preserves the hour so reviews keep their spacing."""
    now = datetime.now(timezone.utc)
    due_at = ensure_utc(due_at)
    if (due_at - now).days < 3:
        return due_at

    def day_load(day_start: datetime) -> int:
        return (
            db.scalar(
                select(func.count(Card.id)).where(
                    Card.user_id == user_id,
                    Card.due_at >= day_start,
                    Card.due_at < day_start + timedelta(days=1),
                )
            )
            or 0
        )

    base_day = due_at.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = [base_day + timedelta(days=offset) for offset in (-1, 0, 1)]
    best = min(candidates, key=lambda d: (day_load(d), abs((d - base_day).days)))
    return due_at + (best - base_day)


def forecast(db: Session, user_id: int, days: int = 30) -> list[dict]:
    """Due-card counts per day for the next `days` days (overdue lands on
    day 0). Feeds the dashboard's review-forecast chart."""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    rows = db.execute(
        select(Card.due_at).where(Card.user_id == user_id, Card.due_at < horizon)
    ).scalars().all()
    counts = [0] * days
    for due in rows:
        offset = (ensure_utc(due) - now).days
        counts[max(0, min(days - 1, offset))] += 1
    start = now.date()
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "due": counts[i]}
        for i in range(days)
    ]
