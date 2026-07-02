from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Card(Base):
    """One SRS memory item for one user.

    Cards usually point at a lexeme but can also target grammar drills or
    sentences (`card_type`). Scheduling state follows a two-component
    memory model (stability + difficulty); see services/srs_engine.py.
    """

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lexeme_id: Mapped[int | None] = mapped_column(ForeignKey("lexemes.id"), index=True)
    card_type: Mapped[str] = mapped_column(String(24), default="vocabulary")
    # vocabulary | grammar | sentence | listening | production
    direction: Mapped[str] = mapped_column(String(16), default="recognition")
    # recognition (RU->EN) | production (EN->RU)

    # Memory model state
    stability: Mapped[float] = mapped_column(Float, default=0.0)  # days
    difficulty: Mapped[float] = mapped_column(Float, default=5.0)  # 1..10
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(12), default="new")
    # new | learning | review | relearning

    due_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ReviewLog(Base):
    """Immutable log of every review — the raw material for forgetting-curve
    fitting, difficulty estimation, and the analytics dashboard."""

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1 again, 2 hard, 3 good, 4 easy
    elapsed_days: Mapped[float] = mapped_column(Float)
    predicted_retention: Mapped[float] = mapped_column(Float)
    stability_before: Mapped[float] = mapped_column(Float)
    stability_after: Mapped[float] = mapped_column(Float)
    interval_days: Mapped[float] = mapped_column(Float)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
