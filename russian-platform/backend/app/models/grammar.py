from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GrammarTopic(Base):
    """One node in the interactive grammar encyclopedia.

    `content` holds the structured lesson body (sections of markdown,
    tables, and interactive drill specs the frontend renders). `drills`
    holds machine-checkable exercises used for adaptive quizzes.
    """

    __tablename__ = "grammar_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    title_native: Mapped[str] = mapped_column(String(128))
    cefr_level: Mapped[str] = mapped_column(String(4), index=True)
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    summary: Mapped[str] = mapped_column(Text)
    content: Mapped[list] = mapped_column(JSON, default=list)  # sections
    drills: Mapped[list] = mapped_column(JSON, default=list)  # exercises
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)  # slugs


class GrammarMastery(Base):
    """Per-user mastery of a grammar topic, updated by drill results and
    mistake detection across all modules (writing, conversation, quizzes)."""

    __tablename__ = "grammar_mastery"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("grammar_topics.id"), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime)
    error_log: Mapped[list] = mapped_column(JSON, default=list)

    def record(self, is_correct: bool) -> None:
        # Column defaults apply at flush; a fresh row still has None here.
        self.attempts = (self.attempts or 0) + 1
        if is_correct:
            self.correct = (self.correct or 0) + 1
        # Exponential moving average: recent performance dominates, but a
        # single slip never craters demonstrated mastery.
        alpha = 0.3
        current = self.mastery or 0.0
        self.mastery = (1 - alpha) * current + alpha * (1.0 if is_correct else 0.0)
        self.last_practiced = datetime.now(timezone.utc)
