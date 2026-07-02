from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    Achievement,
    Card,
    GrammarMastery,
    GrammarTopic,
    LearningEvent,
    ReviewLog,
    User,
    UserAchievement,
)
from app.services.cefr import estimate_cefr
from app.services.gamification import xp_progress
from app.services.srs_engine import retrievability

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    cefr = estimate_cefr(db, user.id)

    # Vocabulary state
    cards = db.execute(
        select(Card.state, func.count(Card.id))
        .where(Card.user_id == user.id)
        .group_by(Card.state)
    ).all()
    card_states = {state: count for state, count in cards}
    due_now = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.user_id == user.id, Card.due_at <= now
            )
        )
        or 0
    )

    # Predicted retention across the whole collection (memory decay model)
    rows = db.execute(
        select(Card.stability, Card.last_reviewed_at).where(
            Card.user_id == user.id, Card.state != "new"
        )
    ).all()
    retentions = []
    for stability, last in rows:
        if last is None:
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        retentions.append(retrievability(stability, (now - last).total_seconds() / 86400))
    avg_retention = round(sum(retentions) / len(retentions), 3) if retentions else None

    # Review accuracy trend, last 7 days
    week_ago = now - timedelta(days=7)
    recent = db.execute(
        select(ReviewLog.rating, func.count(ReviewLog.id))
        .where(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= week_ago)
        .group_by(ReviewLog.rating)
    ).all()
    rating_counts = {rating: count for rating, count in recent}
    total_recent = sum(rating_counts.values())
    accuracy = (
        round(1 - rating_counts.get(1, 0) / total_recent, 3) if total_recent else None
    )

    # Weakest grammar topics
    weak_grammar = db.execute(
        select(GrammarTopic.slug, GrammarTopic.title, GrammarMastery.mastery)
        .join(GrammarMastery, GrammarMastery.topic_id == GrammarTopic.id)
        .where(GrammarMastery.user_id == user.id, GrammarMastery.mastery < 0.7)
        .order_by(GrammarMastery.mastery)
        .limit(5)
    ).all()

    # Time studied, last 7 days, from the event stream
    time_studied = db.scalar(
        select(func.coalesce(func.sum(LearningEvent.duration_seconds), 0.0)).where(
            LearningEvent.user_id == user.id, LearningEvent.created_at >= week_ago
        )
    )
    events_by_type = db.execute(
        select(LearningEvent.event_type, func.count(LearningEvent.id))
        .where(LearningEvent.user_id == user.id)
        .group_by(LearningEvent.event_type)
    ).all()

    achievements = db.execute(
        select(Achievement, UserAchievement.earned_at)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user.id)
    ).all()

    return {
        "cefr": cefr,
        "xp": xp_progress(user.xp),
        "streak_days": user.streak_days,
        "vocabulary": {
            "known_words": cefr["known_words"],
            "card_states": card_states,
            "due_now": due_now,
            "predicted_retention": avg_retention,
        },
        "reviews_7d": {"total": total_recent, "accuracy": accuracy,
                       "ratings": rating_counts},
        "weak_grammar": [
            {"slug": slug, "title": title, "mastery": round(m, 3)}
            for slug, title, m in weak_grammar
        ],
        "time_studied_7d_minutes": round((time_studied or 0) / 60, 1),
        "activity": {etype: count for etype, count in events_by_type},
        "achievements": [
            {"slug": a.slug, "title": a.title, "icon": a.icon,
             "earned_at": earned.isoformat()}
            for a, earned in achievements
        ],
    }
