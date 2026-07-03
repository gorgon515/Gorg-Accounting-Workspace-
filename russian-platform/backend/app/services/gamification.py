"""XP, levels, streaks, and achievement evaluation."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    Card,
    ConversationSession,
    ConversationTurn,
    LessonCompletion,
    ReviewLog,
    User,
    UserAchievement,
)


def xp_progress(xp: int) -> dict:
    """Level curve: each level costs 100 * level XP (triangular growth).
    Level 1 at 0 XP, level 2 at 100, level 3 at 300, level 4 at 600 ..."""
    level, cost, remaining = 1, 100, xp
    while remaining >= cost:
        remaining -= cost
        level += 1
        cost = 100 * level
    return {"level": level, "xp_in_level": remaining, "xp_for_next": cost}


def level_for_xp(xp: int) -> int:
    return xp_progress(xp)["level"]


def serialize_achievements(achievements: list[Achievement]) -> list[dict]:
    return [
        {"slug": a.slug, "title": a.title, "icon": a.icon, "rarity": rarity_of(a)}
        for a in achievements
    ]


def rarity_of(achievement: Achievement) -> str:
    """Rarity from XP reward — a stable proxy for how hard the criterion is."""
    if achievement.xp_reward >= 300:
        return "legendary"
    if achievement.xp_reward >= 150:
        return "epic"
    if achievement.xp_reward >= 75:
        return "rare"
    return "common"


def award_xp(user: User, amount: int) -> None:
    user.xp += max(0, amount)


def touch_streak(user: User, today: date | None = None) -> None:
    """Maintain a daily learning streak. Called on any learning activity."""
    today = today or date.today()
    if user.last_active_date == today:
        return
    if user.last_active_date == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    user.last_active_date = today


def _metric_value(db: Session, user: User, metric: str) -> int:
    if metric == "xp":
        return user.xp
    if metric == "streak_days":
        return user.streak_days
    if metric == "words_learned":
        return (
            db.scalar(
                select(func.count(Card.id)).where(
                    Card.user_id == user.id, Card.state != "new"
                )
            )
            or 0
        )
    if metric == "reviews_done":
        return (
            db.scalar(
                select(func.count(ReviewLog.id)).where(ReviewLog.user_id == user.id)
            )
            or 0
        )
    if metric == "lessons_completed":
        return (
            db.scalar(
                select(func.count(LessonCompletion.id)).where(
                    LessonCompletion.user_id == user.id,
                    LessonCompletion.passed.is_(True),
                )
            )
            or 0
        )
    if metric == "conversation_turns":
        return (
            db.scalar(
                select(func.count(ConversationTurn.id))
                .join(
                    ConversationSession,
                    ConversationTurn.session_id == ConversationSession.id,
                )
                .where(
                    ConversationSession.user_id == user.id,
                    ConversationTurn.role == "user",
                )
            )
            or 0
        )
    return 0


def evaluate_achievements(db: Session, user: User) -> list[Achievement]:
    """Grant any newly earned achievements; returns the fresh ones."""
    earned_ids = set(
        db.scalars(
            select(UserAchievement.achievement_id).where(
                UserAchievement.user_id == user.id
            )
        )
    )
    fresh: list[Achievement] = []
    for ach in db.scalars(select(Achievement)):
        if ach.id in earned_ids:
            continue
        if _metric_value(db, user, ach.metric) >= ach.threshold:
            db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
            award_xp(user, ach.xp_reward)
            fresh.append(ach)
    return fresh
