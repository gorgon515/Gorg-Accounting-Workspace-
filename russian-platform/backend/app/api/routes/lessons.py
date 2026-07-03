from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Card, Course, LearningEvent, Lesson, LessonCompletion, Lexeme, User
from app.services.gamification import (
    award_xp,
    evaluate_achievements,
    serialize_achievements,
    touch_streak,
)
from app.services.lesson_gate import (
    compute_unlock_map,
    grade_mastery_test,
    is_lesson_unlocked,
    passed_lesson_ids,
)

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/courses")
def list_courses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    passed = passed_lesson_ids(db, user.id)
    unlock_map = compute_unlock_map(db, user.id)
    courses = db.scalars(
        select(Course).options(selectinload(Course.lessons)).order_by(Course.order_index)
    ).all()
    result = []
    for course in courses:
        lessons = []
        for lesson in course.lessons:
            lessons.append(
                {
                    "slug": lesson.slug,
                    "title": lesson.title,
                    "order_index": lesson.order_index,
                    "objectives": lesson.objectives,
                    "passed": lesson.id in passed,
                    "unlocked": unlock_map.get(lesson.id, False),
                }
            )
        result.append(
            {
                "slug": course.slug,
                "title": course.title,
                "cefr_level": course.cefr_level,
                "description": course.description,
                "lessons": lessons,
            }
        )
    return result


@router.get("/{slug}")
def get_lesson(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    if not is_lesson_unlocked(db, user.id, lesson):
        raise HTTPException(403, "Lesson is locked — pass the previous lessons first")

    # Resolve the lesson's vocabulary for inline display.
    vocab = []
    for block in lesson.blocks:
        if block.get("type") == "vocabulary":
            rows = db.scalars(
                select(Lexeme).where(Lexeme.lemma.in_(block.get("lemmas", [])))
            ).all()
            vocab.extend(
                {
                    "id": l.id,
                    "lemma": l.lemma,
                    "stressed": l.stressed,
                    "translation": l.translation,
                    "transliteration": l.transliteration,
                }
                for l in rows
            )

    def strip_answers(block: dict) -> dict:
        if block.get("type") not in ("exercise", "mastery_test"):
            return block
        return {
            **block,
            "questions": [
                {"id": q["id"], "prompt": q["prompt"]} for q in block["questions"]
            ],
        }

    return {
        "slug": lesson.slug,
        "title": lesson.title,
        "objectives": lesson.objectives,
        "blocks": [strip_answers(b) for b in lesson.blocks],
        "vocabulary": vocab,
        "grammar_slugs": lesson.grammar_slugs,
        "mastery_threshold": lesson.mastery_threshold,
    }


class LessonSubmission(BaseModel):
    answers: dict[str, str]


@router.post("/{slug}/complete")
def complete_lesson(
    slug: str,
    payload: LessonSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    if not is_lesson_unlocked(db, user.id, lesson):
        raise HTTPException(403, "Lesson is locked")

    score, results = grade_mastery_test(lesson, payload.answers)
    passed = score >= lesson.mastery_threshold

    db.add(
        LessonCompletion(
            user_id=user.id,
            lesson_id=lesson.id,
            score=score,
            passed=passed,
            answers=payload.answers,
        )
    )

    new_cards = 0
    if passed:
        award_xp(user, settings.xp_per_lesson)
        # Enroll the lesson's new vocabulary into the SRS queue.
        lexemes = db.scalars(
            select(Lexeme).where(Lexeme.lemma.in_(lesson.new_lemmas))
        ).all()
        existing = set(
            db.scalars(
                select(Card.lexeme_id).where(
                    Card.user_id == user.id, Card.card_type == "vocabulary"
                )
            )
        )
        for lexeme in lexemes:
            if lexeme.id not in existing:
                db.add(Card(user_id=user.id, lexeme_id=lexeme.id))
                new_cards += 1

    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="lesson_completed",
            skill="vocabulary",
            payload={"lesson": slug, "score": score, "passed": passed},
        )
    )
    fresh = evaluate_achievements(db, user)
    db.commit()
    return {
        "score": round(score, 3),
        "passed": passed,
        "threshold": lesson.mastery_threshold,
        "results": results,
        "new_srs_cards": new_cards,
        "achievements": serialize_achievements(fresh),
    }
