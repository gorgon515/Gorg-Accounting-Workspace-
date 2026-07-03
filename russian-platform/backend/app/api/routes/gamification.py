"""Quests and achievements.

Daily quests are computed from the day's LearningEvents (no extra state
to keep in sync); claiming one is recorded in the user's preferences JSON
under "quests_claimed" so XP is granted exactly once per quest per day.
"""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Achievement, LearningEvent, User, UserAchievement
from app.services.gamification import award_xp, rarity_of

router = APIRouter(prefix="/gamification", tags=["gamification"])

DAILY_QUESTS = [
    {"slug": "reviews-20", "title": "Memory keeper", "title_native": "Хранитель памяти",
     "description": "Complete 20 reviews", "event_type": "review", "target": 20,
     "xp": 30, "icon": "🔁"},
    {"slug": "lesson-1", "title": "One step forward", "title_native": "Шаг вперёд",
     "description": "Pass a lesson", "event_type": "lesson_completed", "target": 1,
     "xp": 40, "icon": "🎓"},
    {"slug": "speak-5", "title": "Find your voice", "title_native": "Голос",
     "description": "Send 5 conversation turns", "event_type": "conversation_turn",
     "target": 5, "xp": 30, "icon": "💬"},
    {"slug": "read-1", "title": "Bookworm", "title_native": "Книголюб",
     "description": "Open a library text", "event_type": "reading", "target": 1,
     "xp": 20, "icon": "📖"},
]


def _today_counts(db: Session, user_id: int) -> dict[str, int]:
    day_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    rows = db.execute(
        select(LearningEvent.event_type, func.count(LearningEvent.id))
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.created_at >= day_start,
        )
        .group_by(LearningEvent.event_type)
    ).all()
    return {etype: count for etype, count in rows}


def _claimed_today(user: User) -> list[str]:
    claimed = (user.preferences or {}).get("quests_claimed", {})
    return claimed.get(date.today().isoformat(), [])


@router.get("/quests")
def daily_quests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    counts = _today_counts(db, user.id)
    claimed = _claimed_today(user)
    return [
        {
            **quest,
            "progress": min(counts.get(quest["event_type"], 0), quest["target"]),
            "complete": counts.get(quest["event_type"], 0) >= quest["target"],
            "claimed": quest["slug"] in claimed,
        }
        for quest in DAILY_QUESTS
    ]


@router.post("/quests/{slug}/claim")
def claim_quest(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    quest = next((q for q in DAILY_QUESTS if q["slug"] == slug), None)
    if quest is None:
        raise HTTPException(404, "Quest not found")
    counts = _today_counts(db, user.id)
    if counts.get(quest["event_type"], 0) < quest["target"]:
        raise HTTPException(409, "Quest not complete yet")
    today = date.today().isoformat()
    preferences = dict(user.preferences or {})
    claimed = dict(preferences.get("quests_claimed", {}))
    today_list = list(claimed.get(today, []))
    if slug in today_list:
        raise HTTPException(409, "Quest already claimed today")
    today_list.append(slug)
    # Keep only today's record — historical claims add no value.
    preferences["quests_claimed"] = {today: today_list}
    user.preferences = preferences
    award_xp(user, quest["xp"])
    db.commit()
    return {"claimed": True, "xp": quest["xp"], "total_xp": user.xp}


@router.get("/achievements")
def all_achievements(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """The full badge collection with earned state and rarity."""
    earned = {
        ua.achievement_id: ua.earned_at
        for ua in db.scalars(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        )
    }
    achievements = db.scalars(select(Achievement)).all()
    return [
        {
            "slug": a.slug,
            "title": a.title,
            "title_native": a.title_native,
            "description": a.description,
            "icon": a.icon,
            "rarity": rarity_of(a),
            "xp_reward": a.xp_reward,
            "earned_at": earned[a.id].isoformat() if a.id in earned else None,
        }
        for a in achievements
    ]
