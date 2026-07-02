from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Learner profile
    cefr_estimate: Mapped[str] = mapped_column(String(4), default="A0")
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=60)

    # Gamification
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Immersion mode: 0.0 = English UI, 1.0 = fully Russian UI. The frontend
    # blends interface strings toward the target language as this rises.
    ui_immersion_ratio: Mapped[float] = mapped_column(default=0.0)

    # Free-form preferences (voice gender, playback speed, theme, ...)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
