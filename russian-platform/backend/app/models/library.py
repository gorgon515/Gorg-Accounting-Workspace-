from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text as SAText
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Text(Base):
    """A graded reading/listening text with sentence-aligned translation.

    `sentences` is the transcript-sync structure the reader UI consumes:
    [{"ru": "stressed sentence", "en": "translation", "audio_url": null}].
    Audio URLs are filled by the Phase 3 audio pipeline; until then the
    client synthesizes speech per sentence (same provider-abstraction
    pattern as vocabulary audio).
    """

    __tablename__ = "texts"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    title_translation: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(24), index=True)
    # story | dialogue | fairy_tale | article | news
    cefr_level: Mapped[str] = mapped_column(String(4), index=True)
    topic: Mapped[str] = mapped_column(String(32), default="general")
    summary: Mapped[str] = mapped_column(SAText)
    sentences: Mapped[list] = mapped_column(JSON, default=list)
    word_count: Mapped[int] = mapped_column(Integer, default=0)


class Bookmark(Base):
    """Reading position / saved place in a text, one per user+text."""

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text_id: Mapped[int] = mapped_column(ForeignKey("texts.id"), index=True)
    sentence_index: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
