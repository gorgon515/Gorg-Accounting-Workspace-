"""Lesson unlocking and mastery-test grading.

Lessons unlock strictly in order within a course; a lesson is unlocked
when every earlier lesson in the course has a passing completion. Courses
unlock when the previous course's lessons are all passed.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Lesson, LessonCompletion


def passed_lesson_ids(db: Session, user_id: int) -> set[int]:
    return set(
        db.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.passed.is_(True),
            )
        )
    )


def is_lesson_unlocked(db: Session, user_id: int, lesson: Lesson) -> bool:
    passed = passed_lesson_ids(db, user_id)
    earlier = db.scalars(
        select(Lesson.id).where(
            Lesson.course_id == lesson.course_id,
            Lesson.order_index < lesson.order_index,
        )
    )
    if not all(lid in passed for lid in earlier):
        return False
    # All previous courses must be fully passed.
    course = db.get(Course, lesson.course_id)
    prev_courses = db.scalars(
        select(Course).where(
            Course.language_id == course.language_id,
            Course.order_index < course.order_index,
        )
    )
    for prev in prev_courses:
        for lid in db.scalars(select(Lesson.id).where(Lesson.course_id == prev.id)):
            if lid not in passed:
                return False
    return True


def grade_mastery_test(lesson: Lesson, answers: dict[str, str]) -> tuple[float, list]:
    """Grade submitted answers against the lesson's exercise answer keys.

    Returns (score 0..1, per-question results). Questions live in blocks of
    type "exercise" or "mastery_test" as
    {"id": str, "prompt": str, "answer": str, "accept": [str, ...]}.
    """
    questions: list[dict] = []
    for block in lesson.blocks:
        if block.get("type") in ("exercise", "mastery_test"):
            questions.extend(block.get("questions", []))
    if not questions:
        return 1.0, []

    results = []
    correct = 0
    for q in questions:
        submitted = (answers.get(q["id"]) or "").strip().lower().replace("ё", "е")
        accepted = [q["answer"], *q.get("accept", [])]
        ok = submitted in [a.strip().lower().replace("ё", "е") for a in accepted]
        correct += ok
        results.append(
            {"id": q["id"], "correct": ok, "expected": q["answer"], "submitted": submitted}
        )
    return correct / len(questions), results
