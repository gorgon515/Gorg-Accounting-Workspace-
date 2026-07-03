"""Lesson unlocking and mastery-test grading.

Lessons unlock strictly in order within a course; a lesson is unlocked
when every earlier lesson in the course has a passing completion. Courses
unlock when the previous course's lessons are all passed.

The unlock state for ALL lessons is computed in one pass over two queries
(Phase 2 audit fix: the previous per-lesson check issued O(n²) queries
when listing courses).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Lesson, LessonCompletion
from app.services.text_utils import answer_matches, normalize_answer


def passed_lesson_ids(db: Session, user_id: int) -> set[int]:
    return set(
        db.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user_id,
                LessonCompletion.passed.is_(True),
            )
        )
    )


def compute_unlock_map(db: Session, user_id: int) -> dict[int, bool]:
    """lesson_id -> unlocked, for every lesson, in curriculum order.

    A lesson is unlocked iff every lesson before it (course order, then
    lesson order) has been passed. Two queries total, regardless of size.
    """
    passed = passed_lesson_ids(db, user_id)
    ordered = db.execute(
        select(Lesson.id)
        .join(Course, Lesson.course_id == Course.id)
        .order_by(Course.order_index, Lesson.order_index)
    ).scalars()

    unlock_map: dict[int, bool] = {}
    all_previous_passed = True
    for lesson_id in ordered:
        unlock_map[lesson_id] = all_previous_passed
        if lesson_id not in passed:
            all_previous_passed = False
    return unlock_map


def is_lesson_unlocked(db: Session, user_id: int, lesson: Lesson) -> bool:
    return compute_unlock_map(db, user_id).get(lesson.id, False)


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
        submitted = answers.get(q["id"]) or ""
        ok = answer_matches(submitted, q["answer"], q.get("accept"))
        correct += ok
        results.append(
            {
                "id": q["id"],
                "correct": ok,
                "expected": q["answer"],
                "submitted": normalize_answer(submitted),
            }
        )
    return correct / len(questions), results
