from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LearningEvent(Base):
    """Append-only event stream. Every interaction lands here and feeds the
    adaptive algorithms and the analytics dashboard."""

    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    # review | lesson_completed | conversation_turn | pronunciation |
    # reading | listening | writing | quiz | grammar_drill | login
    skill: Mapped[str | None] = mapped_column(String(24), index=True)
    # vocabulary | grammar | reading | listening | speaking | writing
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )


class PronunciationAttempt(Base):
    """Result of one pronunciation-engine evaluation. Audio itself is stored
    in object storage; the row keeps scores and phoneme-level feedback."""

    __tablename__ = "pronunciation_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_text: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(String(512))
    overall_score: Mapped[float] = mapped_column(Float)  # 0..100
    stress_score: Mapped[float | None] = mapped_column(Float)
    phoneme_scores: Mapped[list] = mapped_column(JSON, default=list)
    feedback: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    corrections: Mapped[list] = mapped_column(JSON, default=list)
    quality_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
