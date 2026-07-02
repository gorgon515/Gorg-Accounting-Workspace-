from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Course(Base):
    """A structured learning path (Absolute Beginner, A1, ... C2)."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    cefr_level: Mapped[str] = mapped_column(String(4), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", order_by="Lesson.order_index"
    )


class Lesson(Base):
    """One session in a course.

    `blocks` is an ordered list of typed activity blocks the frontend
    renders: vocabulary, grammar_ref, reading, listening, speaking,
    writing, dictation, dialogue, exercise, culture, review, mastery_test.
    Machine-checkable blocks carry their answer key for server-side grading.
    """

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    new_lemmas: Mapped[list] = mapped_column(JSON, default=list)
    grammar_slugs: Mapped[list] = mapped_column(JSON, default=list)
    mastery_threshold: Mapped[float] = mapped_column(Float, default=0.8)

    course: Mapped[Course] = relationship(back_populates="lessons")


class LessonCompletion(Base):
    __tablename__ = "lesson_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    score: Mapped[float] = mapped_column(Float)  # 0..1 mastery-test score
    passed: Mapped[bool] = mapped_column(default=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
