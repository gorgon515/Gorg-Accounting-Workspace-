from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lexeme(Base):
    """A dictionary entry with everything a learner needs.

    Structured morphology (declension/conjugation tables, aspect pairs,
    government) lives in JSON columns: shapes differ per part of speech and
    per language, and both SQLite and PostgreSQL handle JSON natively.
    """

    __tablename__ = "lexemes"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)

    # Core form
    lemma: Mapped[str] = mapped_column(String(128), index=True)  # "говорить"
    stressed: Mapped[str] = mapped_column(String(128))  # "говори́ть"
    ipa: Mapped[str] = mapped_column(String(128))  # [ɡəvɐˈrʲitʲ]
    transliteration: Mapped[str] = mapped_column(String(128))  # "govorit'"

    part_of_speech: Mapped[str] = mapped_column(String(24), index=True)
    cefr_level: Mapped[str] = mapped_column(String(4), index=True)  # A1..C2
    frequency_rank: Mapped[int | None] = mapped_column(Integer, index=True)
    register: Mapped[str] = mapped_column(String(24), default="neutral")
    # formal | neutral | informal | slang | vulgar | academic | technical
    domain: Mapped[str] = mapped_column(String(32), default="general", index=True)
    # general | business | medical | legal | finance | tech | ...
    topic: Mapped[str] = mapped_column(String(32), default="general", index=True)
    # thematic grouping for lessons/filtering: food, family, travel, ...
    difficulty: Mapped[float] = mapped_column(Float, default=1.0)
    # 1.0 (A1 core) .. 6.0 (C2 rare); drives quiz/lesson composition
    etymology: Mapped[str | None] = mapped_column(Text)

    # Meaning
    translation: Mapped[str] = mapped_column(String(256))  # natural translation
    literal_translation: Mapped[str | None] = mapped_column(String(256))
    meanings: Mapped[list] = mapped_column(JSON, default=list)  # all senses

    # Morphology & word formation
    root: Mapped[str | None] = mapped_column(String(64))
    prefixes: Mapped[list] = mapped_column(JSON, default=list)
    suffixes: Mapped[list] = mapped_column(JSON, default=list)
    aspect: Mapped[str | None] = mapped_column(String(16))  # imperfective/perfective
    aspect_partner: Mapped[str | None] = mapped_column(String(128))
    gender: Mapped[str | None] = mapped_column(String(8))  # m | f | n
    animacy: Mapped[str | None] = mapped_column(String(12))
    inflections: Mapped[dict] = mapped_column(JSON, default=dict)  # full tables
    government: Mapped[list] = mapped_column(JSON, default=list)  # case requirements

    # Learning aids
    mnemonic: Mapped[str | None] = mapped_column(Text)
    usage_notes: Mapped[str | None] = mapped_column(Text)
    cultural_notes: Mapped[str | None] = mapped_column(Text)
    common_mistakes: Mapped[list] = mapped_column(JSON, default=list)

    # Audio asset references (populated by the media pipeline; see docs/ROADMAP.md)
    audio: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"male": url, "female": url, "slow": url}

    examples: Mapped[list["ExampleSentence"]] = relationship(
        back_populates="lexeme", cascade="all, delete-orphan"
    )


class ExampleSentence(Base):
    __tablename__ = "example_sentences"

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(ForeignKey("lexemes.id"), index=True)
    text: Mapped[str] = mapped_column(Text)  # with stress marks
    translation: Mapped[str] = mapped_column(Text)
    cefr_level: Mapped[str] = mapped_column(String(4), default="A1")
    audio_url: Mapped[str | None] = mapped_column(String(512))

    lexeme: Mapped[Lexeme] = relationship(back_populates="examples")


class InflectionForm(Base):
    """Reverse index: every inflected form → its lexeme, so learners can
    look up «живу» and land on жить. Populated at seed time from the
    morphology tables (see seed/runner.py)."""

    __tablename__ = "inflection_forms"

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(ForeignKey("lexemes.id"), index=True)
    form: Mapped[str] = mapped_column(String(128), index=True)  # stress-stripped
    table_name: Mapped[str] = mapped_column(String(24))  # declension | present | ...
    slot: Mapped[str] = mapped_column(String(16))  # gen_sg | я | f | ...


class LexemeRelation(Base):
    """Synonyms, antonyms, word-family links, collocations, false friends."""

    __tablename__ = "lexeme_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    lexeme_id: Mapped[int] = mapped_column(ForeignKey("lexemes.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(24), index=True)
    # synonym | antonym | family | collocation | false_friend | derived
    target_lemma: Mapped[str] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(String(256))
    strength: Mapped[float] = mapped_column(Float, default=1.0)
