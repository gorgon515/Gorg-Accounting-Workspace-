from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Card, LearningEvent, Lexeme, ReviewLog, User
from app.services import srs_engine
from app.services.gamification import (
    award_xp,
    evaluate_achievements,
    serialize_achievements,
    touch_streak,
)
from app.services.srs_planner import (
    adaptive_target_retention,
    balance_due_date,
    forecast,
)
from app.services.text_utils import ensure_utc

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/forecast")
def review_forecast(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Daily due-card forecast plus the learner's adaptive retention target."""
    return {
        "forecast": forecast(db, user.id, days),
        "target_retention": adaptive_target_retention(db, user.id),
    }


@router.get("/queue")
def review_queue(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    due = db.execute(
        select(Card, Lexeme)
        .join(Lexeme, Card.lexeme_id == Lexeme.id)
        .where(Card.user_id == user.id, Card.due_at <= now)
        .order_by(Card.due_at)
        .limit(limit)
    ).all()
    total_due = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.user_id == user.id, Card.due_at <= now
            )
        )
        or 0
    )
    return {
        "total_due": total_due,
        "cards": [
            {
                "card_id": card.id,
                "state": card.state,
                "direction": card.direction,
                "lexeme": {
                    "id": lex.id,
                    "lemma": lex.lemma,
                    "stressed": lex.stressed,
                    "ipa": lex.ipa,
                    "transliteration": lex.transliteration,
                    "translation": lex.translation,
                    "part_of_speech": lex.part_of_speech,
                    "mnemonic": lex.mnemonic,
                    "examples": [
                        {"text": e.text, "translation": e.translation}
                        for e in lex.examples[:2]
                    ],
                },
            }
            for card, lex in due
        ],
    }


class ReviewSubmission(BaseModel):
    rating: int = Field(ge=1, le=4, description="1 Again, 2 Hard, 3 Good, 4 Easy")


@router.post("/{card_id}")
def submit_review(
    card_id: int,
    payload: ReviewSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    card = db.get(Card, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(404, "Card not found")

    now = datetime.now(timezone.utc)
    last = card.last_reviewed_at
    elapsed = (now - ensure_utc(last)).total_seconds() / 86400.0 if last else 0.0

    result = srs_engine.schedule(
        stability=card.stability,
        difficulty=card.difficulty,
        state=card.state,
        rating=payload.rating,
        elapsed_days=elapsed,
        now=now,
        target_retention=adaptive_target_retention(db, user.id),
    )

    db.add(
        ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=payload.rating,
            elapsed_days=elapsed,
            predicted_retention=result.predicted_retention,
            stability_before=card.stability,
            stability_after=result.stability,
            interval_days=result.interval_days,
        )
    )

    if payload.rating == srs_engine.AGAIN and card.state in ("review", "relearning"):
        card.lapses += 1
    card.stability = result.stability
    card.difficulty = result.difficulty
    card.state = result.state
    card.due_at = balance_due_date(db, user.id, result.due_at)
    card.last_reviewed_at = now
    card.reps += 1

    award_xp(user, settings.xp_per_review)
    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="review",
            skill="vocabulary",
            payload={"card_id": card.id, "rating": payload.rating},
        )
    )
    fresh = evaluate_achievements(db, user)
    db.commit()
    return {
        "card_id": card.id,
        "state": card.state,
        "stability": round(card.stability, 2),
        "difficulty": round(card.difficulty, 2),
        "interval_days": round(result.interval_days, 2),
        "due_at": card.due_at.isoformat(),
        "achievements": serialize_achievements(fresh),
    }
