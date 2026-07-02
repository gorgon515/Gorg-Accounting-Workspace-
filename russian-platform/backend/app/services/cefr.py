"""CEFR proficiency estimation.

Combines demonstrated signals — vocabulary in long-term memory, grammar
mastery, and lesson progress — into a conservative CEFR estimate. The
thresholds follow common vocabulary-size research (Nation, Milton):
roughly A1≈500, A2≈1000, B1≈2000, B2≈4000, C1≈8000, C2≈16000 known words,
moderated by grammar mastery so vocab-cramming alone can't inflate level.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Card, GrammarMastery, GrammarTopic, LessonCompletion

LEVELS = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
VOCAB_THRESHOLDS = {"A1": 500, "A2": 1000, "B1": 2000, "B2": 4000, "C1": 8000, "C2": 16000}


def known_word_count(db: Session, user_id: int) -> int:
    """Words with enough stability to count as 'known' (>= 7 days)."""
    return (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.user_id == user_id,
                Card.card_type == "vocabulary",
                Card.stability >= 7.0,
            )
        )
        or 0
    )


def grammar_mastery_by_level(db: Session, user_id: int) -> dict[str, float]:
    """Average mastery per CEFR level across that level's grammar topics."""
    rows = db.execute(
        select(GrammarTopic.cefr_level, func.avg(GrammarMastery.mastery))
        .join(GrammarMastery, GrammarMastery.topic_id == GrammarTopic.id)
        .where(GrammarMastery.user_id == user_id)
        .group_by(GrammarTopic.cefr_level)
    ).all()
    return {level: float(avg or 0.0) for level, avg in rows}


def estimate_cefr(db: Session, user_id: int) -> dict:
    vocab = known_word_count(db, user_id)
    grammar = grammar_mastery_by_level(db, user_id)
    lessons_passed = (
        db.scalar(
            select(func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.passed.is_(True),
            )
        )
        or 0
    )

    level = "A0"
    for candidate in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        vocab_ok = vocab >= VOCAB_THRESHOLDS[candidate]
        # Grammar for the level below must be reasonably mastered.
        below = LEVELS[LEVELS.index(candidate) - 1]
        grammar_ok = grammar.get(below, 0.0) >= 0.6 if below != "A0" else True
        if vocab_ok and grammar_ok:
            level = candidate
        else:
            break

    # Fractional progress toward the next level, for the dashboard.
    nxt = LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]
    target = VOCAB_THRESHOLDS.get(nxt, VOCAB_THRESHOLDS["C2"])
    prev_target = VOCAB_THRESHOLDS.get(level, 0)
    span = max(target - prev_target, 1)
    progress = min(1.0, max(0.0, (vocab - prev_target) / span))

    return {
        "level": level,
        "progress_to_next": round(progress, 3),
        "known_words": vocab,
        "grammar_mastery": grammar,
        "lessons_passed": lessons_passed,
    }
