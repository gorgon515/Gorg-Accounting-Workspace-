from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    title_native: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(16), default="🏆")
    # Criterion evaluated by services/gamification.py against user stats.
    metric: Mapped[str] = mapped_column(String(32))
    # words_learned | reviews_done | lessons_completed | streak_days |
    # conversation_turns | xp
    threshold: Mapped[int] = mapped_column(Integer)
    xp_reward: Mapped[int] = mapped_column(Integer, default=25)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id"), index=True
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
