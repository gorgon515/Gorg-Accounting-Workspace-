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
    """lesson_id -> unlocked, for every lesson. Two queries total.

    Phase 3 rule (the Phase 2 global-linear rule can't scale to 300+
    lessons): lessons unlock sequentially *within* their course, and a
    course unlocks when its `prerequisite_slug` course is at least
    `min_completion` passed (no prerequisite = always open).
    """
    passed = passed_lesson_ids(db, user_id)
    rows = db.execute(
        select(
            Lesson.id,
            Course.slug,
            Course.prerequisite_slug,
            Course.min_completion,
        )
        .join(Course, Lesson.course_id == Course.id)
        .order_by(Course.order_index, Lesson.order_index)
    ).all()

    total_by_course: dict[str, int] = {}
    passed_by_course: dict[str, int] = {}
    for lesson_id, course_slug, _prereq, _min in rows:
        total_by_course[course_slug] = total_by_course.get(course_slug, 0) + 1
        if lesson_id in passed:
            passed_by_course[course_slug] = passed_by_course.get(course_slug, 0) + 1

    def course_open(prereq: str | None, min_completion: float) -> bool:
        if prereq is None or prereq not in total_by_course:
            return True
        ratio = passed_by_course.get(prereq, 0) / total_by_course[prereq]
        return ratio >= min_completion

    unlock_map: dict[int, bool] = {}
    previous_passed_in_course: dict[str, bool] = {}
    for lesson_id, course_slug, prereq, min_completion in rows:
        sequential_ok = previous_passed_in_course.get(course_slug, True)
        unlock_map[lesson_id] = sequential_ok and course_open(prereq, min_completion)
        if lesson_id not in passed:
            previous_passed_in_course[course_slug] = False
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
