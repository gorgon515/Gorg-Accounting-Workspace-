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
    Lexeme,
    PronunciationAttempt,
    ReviewLog,
    User,
    UserAchievement,
)
from app.services.cefr import estimate_cefr
from app.services.gamification import xp_progress
from app.services.srs_engine import retrievability
from app.services.text_utils import ensure_utc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/report")
def periodic_report(
    period: str = "week",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Error-intelligence report: what went wrong recently, and exactly
    what to do about it. `period` = week | month."""
    if period not in ("week", "month"):
        period = "week"
    days = 7 if period == "week" else 30
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Forgotten words: cards that lapsed in the period.
    lapsed = db.execute(
        select(Lexeme.lemma, Lexeme.stressed, Lexeme.translation,
               func.count(ReviewLog.id))
        .join(Card, Card.lexeme_id == Lexeme.id)
        .join(ReviewLog, ReviewLog.card_id == Card.id)
        .where(ReviewLog.user_id == user.id, ReviewLog.rating == 1,
               ReviewLog.reviewed_at >= since)
        .group_by(Lexeme.id)
        .order_by(func.count(ReviewLog.id).desc())
        .limit(10)
    ).all()

    total = db.scalar(
        select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= since
        )
    ) or 0
    lapses = db.scalar(
        select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= since,
            ReviewLog.rating == 1,
        )
    ) or 0

    weak_grammar = db.execute(
        select(GrammarTopic.slug, GrammarTopic.title, GrammarMastery.mastery)
        .join(GrammarMastery, GrammarMastery.topic_id == GrammarTopic.id)
        .where(GrammarMastery.user_id == user.id, GrammarMastery.mastery < 0.7)
        .order_by(GrammarMastery.mastery)
        .limit(5)
    ).all()

    pron_avg = db.scalar(
        select(func.avg(PronunciationAttempt.overall_score)).where(
            PronunciationAttempt.user_id == user.id,
            PronunciationAttempt.created_at >= since,
        )
    )
    study_seconds = db.scalar(
        select(func.coalesce(func.sum(LearningEvent.duration_seconds), 0.0)).where(
            LearningEvent.user_id == user.id, LearningEvent.created_at >= since
        )
    ) or 0.0
    events = db.scalar(
        select(func.count(LearningEvent.id)).where(
            LearningEvent.user_id == user.id, LearningEvent.created_at >= since
        )
    ) or 0

    recommendations = []
    for slug, title, mastery in weak_grammar:
        recommendations.append({
            "kind": "grammar",
            "action": f"Redo “{title}” drills (mastery {int(mastery * 100)}%)",
            "lesson_slug": f"grammar-{slug}",
        })
    if total and lapses / total > 0.2:
        recommendations.append({
            "kind": "reviews",
            "action": "Your lapse rate is above 20% — shorter, more frequent "
                      "review sessions beat marathons.",
            "lesson_slug": None,
        })
    if lapsed:
        recommendations.append({
            "kind": "vocabulary",
            "action": f"Drill your {len(lapsed)} most-forgotten words in the "
                      "practice quiz.",
            "lesson_slug": None,
        })
    if pron_avg is not None and pron_avg < 80:
        recommendations.append({
            "kind": "speaking",
            "action": "Pronunciation scores are below 80% — use the practice "
                      "queue to repeat weak words until mastered.",
            "lesson_slug": None,
        })
    if not recommendations:
        recommendations.append({
            "kind": "keep-going",
            "action": "No weak spots detected this period — advance to the "
                      "next lesson or take a level exam.",
            "lesson_slug": None,
        })

    return {
        "period": period,
        "reviews": {"total": total, "lapses": lapses,
                    "accuracy": round(1 - lapses / total, 3) if total else None},
        "forgotten_words": [
            {"lemma": lemma, "stressed": stressed, "translation": translation,
             "lapses": count}
            for lemma, stressed, translation, count in lapsed
        ],
        "weak_grammar": [
            {"slug": slug, "title": title, "mastery": round(m, 3)}
            for slug, title, m in weak_grammar
        ],
        "pronunciation_avg": round(float(pron_avg), 1) if pron_avg is not None else None,
        "study_minutes": round(study_seconds / 60, 1),
        "activity_events": events,
        "recommendations": recommendations,
    }


@router.get("/trends")
def trends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Heatmap, learning velocity, per-skill strengths, and a fluency
    projection — the Phase 2 deep-analytics layer."""
    now = datetime.now(timezone.utc)

    # Activity heatmap: events per day, last 13 weeks.
    start = now - timedelta(days=91)
    heat_rows = db.execute(
        select(
            func.date(LearningEvent.created_at), func.count(LearningEvent.id)
        )
        .where(LearningEvent.user_id == user.id, LearningEvent.created_at >= start)
        .group_by(func.date(LearningEvent.created_at))
    ).all()
    heatmap = {str(day): count for day, count in heat_rows}

    # Learning velocity: cards first reviewed per ISO week, last 6 weeks.
    week_counts: dict[str, int] = {}
    first_reviews = db.execute(
        select(func.min(ReviewLog.reviewed_at))
        .where(ReviewLog.user_id == user.id)
        .group_by(ReviewLog.card_id)
    ).scalars().all()
    for reviewed in first_reviews:
        if reviewed is None:
            continue
        reviewed = ensure_utc(reviewed)
        if (now - reviewed).days > 42:
            continue
        key = reviewed.strftime("%G-W%V")
        week_counts[key] = week_counts.get(key, 0) + 1
    velocity = sorted(
        [{"week": week, "new_words": count} for week, count in week_counts.items()],
        key=lambda item: item["week"],
    )

    # Per-skill scores from each skill's own evidence.
    cefr = estimate_cefr(db, user.id)
    week_ago = now - timedelta(days=7)
    again = db.scalar(
        select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user.id,
            ReviewLog.reviewed_at >= week_ago,
            ReviewLog.rating == 1,
        )
    ) or 0
    total_reviews = db.scalar(
        select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= week_ago
        )
    ) or 0
    grammar_avg = db.scalar(
        select(func.avg(GrammarMastery.mastery)).where(
            GrammarMastery.user_id == user.id
        )
    )
    speaking_avg = db.scalar(
        select(func.avg(PronunciationAttempt.overall_score)).where(
            PronunciationAttempt.user_id == user.id
        )
    )
    listening_scores = [
        e.payload.get("score")
        for e in db.scalars(
            select(LearningEvent).where(
                LearningEvent.user_id == user.id,
                LearningEvent.event_type == "listening",
            )
        )
        if e.payload.get("score") is not None
    ]
    skills = {
        "vocabulary": round(1 - again / total_reviews, 3) if total_reviews else None,
        "grammar": round(float(grammar_avg), 3) if grammar_avg is not None else None,
        "speaking": round(float(speaking_avg) / 100, 3) if speaking_avg is not None else None,
        "listening": round(sum(listening_scores) / len(listening_scores) / 100, 3)
        if listening_scores else None,
    }
    rated = {k: v for k, v in skills.items() if v is not None}
    strongest = max(rated, key=rated.get) if rated else None
    weakest = min(rated, key=rated.get) if rated else None

    # Fluency projection: extrapolate recent word velocity to B2 vocabulary.
    recent_velocity = sum(v["new_words"] for v in velocity[-4:]) / max(len(velocity[-4:]), 1)
    fluency_estimate = None
    if recent_velocity > 0:
        remaining = max(0, 4000 - cefr["known_words"])  # B2 threshold
        weeks_left = remaining / recent_velocity
        fluency_estimate = {
            "target_level": "B2",
            "words_remaining": remaining,
            "words_per_week": round(recent_velocity, 1),
            "estimated_date": (now + timedelta(weeks=weeks_left)).date().isoformat(),
        }

    return {
        "heatmap": heatmap,
        "velocity": velocity,
        "skills": skills,
        "strongest_skill": strongest,
        "weakest_skill": weakest,
        "fluency_estimate": fluency_estimate,
    }


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
        elapsed_days = (now - ensure_utc(last)).total_seconds() / 86400
        retentions.append(retrievability(stability, elapsed_days))
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
