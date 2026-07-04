"""Exams: CEFR level exams, placement test, results, certificates."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ExamResult, LearningEvent, User
from app.services.exams import (
    EXAM_LEVELS,
    LEVEL_ORDER,
    TIME_LIMITS_MINUTES,
    build_level_exam,
    build_placement_exam,
    grade_exam,
    grade_placement,
    strip_answer_keys,
)
from app.services.gamification import award_xp, touch_streak

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("/levels")
def list_levels(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    best = {}
    for result in db.scalars(
        select(ExamResult).where(
            ExamResult.user_id == user.id, ExamResult.kind == "level"
        )
    ):
        if result.level not in best or result.score > best[result.level]["score"]:
            best[result.level] = {"score": result.score, "passed": result.passed}
    return [
        {
            "level": level,
            "time_limit_minutes": TIME_LIMITS_MINUTES[level],
            "best": best.get(level),
        }
        for level in EXAM_LEVELS
    ]


@router.get("/level/{level}")
def get_level_exam(
    level: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if level not in EXAM_LEVELS:
        raise HTTPException(404, f"level must be one of {EXAM_LEVELS}")
    seed = secrets.token_hex(8)
    exam = build_level_exam(db, level, seed)
    return strip_answer_keys(exam)


class ExamSubmission(BaseModel):
    seed: str
    answers: dict[str, str]


@router.post("/level/{level}/submit")
def submit_level_exam(
    level: str,
    payload: ExamSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if level not in EXAM_LEVELS:
        raise HTTPException(404, f"level must be one of {EXAM_LEVELS}")
    exam = build_level_exam(db, level, payload.seed)  # deterministic rebuild
    result = grade_exam(exam, payload.answers)

    record = ExamResult(
        user_id=user.id, kind="level", level=level, seed=payload.seed,
        score=result["score"], passed=result["passed"],
        sections=result["sections"], weaknesses=result["weak_topics"],
    )
    db.add(record)
    if result["passed"]:
        award_xp(user, 100)
        # A passed exam is stronger evidence than the vocab heuristic —
        # never downgrade, only lift.
        if LEVEL_ORDER.index(level) > LEVEL_ORDER.index(user.cefr_estimate):
            user.cefr_estimate = level
    touch_streak(user)
    db.add(LearningEvent(user_id=user.id, event_type="exam", skill="grammar",
                         payload={"kind": "level", "level": level,
                                  "score": result["score"]}))
    db.commit()
    return {**result, "result_id": record.id}


@router.get("/placement")
def get_placement(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    seed = secrets.token_hex(8)
    exam = build_placement_exam(db, seed)
    return {
        "seed": seed,
        "time_limit_minutes": exam["time_limit_minutes"],
        "bands": {
            level: [{k: v for k, v in q.items() if not k.startswith("_")}
                    for q in questions]
            for level, questions in exam["bands"].items()
        },
    }


@router.post("/placement/submit")
def submit_placement(
    payload: ExamSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exam = build_placement_exam(db, payload.seed)
    result = grade_placement(exam, payload.answers)
    user.cefr_estimate = result["placed_level"]
    db.add(ExamResult(
        user_id=user.id, kind="placement", level=result["placed_level"],
        seed=payload.seed,
        score=max(result["band_scores"].values(), default=0.0),
        passed=True, sections=result["band_scores"],
    ))
    touch_streak(user)
    db.add(LearningEvent(user_id=user.id, event_type="exam", skill="grammar",
                         payload={"kind": "placement",
                                  "placed": result["placed_level"]}))
    db.commit()
    return result


@router.get("/results")
def exam_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    results = db.scalars(
        select(ExamResult)
        .where(ExamResult.user_id == user.id)
        .order_by(ExamResult.taken_at.desc())
    ).all()
    return [
        {
            "id": r.id, "kind": r.kind, "level": r.level,
            "score": r.score, "passed": r.passed,
            "sections": r.sections, "taken_at": r.taken_at.isoformat(),
        }
        for r in results
    ]


@router.get("/certificates/{result_id}")
def certificate(
    result_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Certificate payload for a passed level exam; the frontend renders
    the printable certificate view from this."""
    result = db.get(ExamResult, result_id)
    if result is None or result.user_id != user.id:
        raise HTTPException(404, "Result not found")
    if result.kind != "level" or not result.passed:
        raise HTTPException(409, "Certificates are issued for passed level exams only")
    return {
        "certificate_id": f"RLI-{result.id:06d}",
        "holder": user.display_name,
        "level": result.level,
        "score_percent": round(result.score * 100, 1),
        "issued_at": result.taken_at.date().isoformat(),
        "title": f"Russian Language Institute — CEFR {result.level} Certificate",
    }
