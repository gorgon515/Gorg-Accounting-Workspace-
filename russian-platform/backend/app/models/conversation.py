from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Scenario(Base):
    """A roleplay setting for the AI conversation partner (waiter, taxi
    driver, customs officer, ...). `script` powers the deterministic
    offline engine; the LLM engine uses `persona_prompt` instead."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    persona: Mapped[str] = mapped_column(String(64))  # "waiter", "friend", ...
    setting: Mapped[str] = mapped_column(String(128))  # "restaurant", ...
    cefr_level: Mapped[str] = mapped_column(String(4), index=True)
    description: Mapped[str] = mapped_column(Text)
    persona_prompt: Mapped[str] = mapped_column(Text)  # LLM system prompt
    script: Mapped[list] = mapped_column(JSON, default=list)  # offline dialogue tree
    key_vocabulary: Mapped[list] = mapped_column(JSON, default=list)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Engine memory: detected weaknesses, topics covered, difficulty level —
    # re-loaded on the next session so the partner "remembers" the learner.
    memory: Mapped[dict] = mapped_column(JSON, default=dict)

    turns: Mapped[list["ConversationTurn"]] = relationship(
        back_populates="session", order_by="ConversationTurn.turn_index"
    )


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_sessions.id"), index=True
    )
    turn_index: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(12))  # user | partner
    text: Mapped[str] = mapped_column(Text)
    translation: Mapped[str | None] = mapped_column(Text)
    corrections: Mapped[list] = mapped_column(JSON, default=list)
    audio_url: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped[ConversationSession] = relationship(back_populates="turns")
