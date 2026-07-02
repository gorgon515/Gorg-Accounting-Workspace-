from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import GrammarMastery, GrammarTopic, LearningEvent, User
from app.services.gamification import touch_streak

router = APIRouter(prefix="/grammar", tags=["grammar"])


@router.get("/topics")
def list_topics(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    mastery = {
        m.topic_id: m.mastery
        for m in db.scalars(
            select(GrammarMastery).where(GrammarMastery.user_id == user.id)
        )
    }
    topics = db.scalars(
        select(GrammarTopic).order_by(GrammarTopic.order_index)
    ).all()
    return [
        {
            "slug": t.slug,
            "title": t.title,
            "title_native": t.title_native,
            "cefr_level": t.cefr_level,
            "summary": t.summary,
            "has_content": bool(t.content),
            "drill_count": len(t.drills),
            "prerequisites": t.prerequisites,
            "mastery": round(mastery.get(t.id, 0.0), 3),
        }
        for t in topics
    ]


@router.get("/topics/{slug}")
def get_topic(
    slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == slug))
    if topic is None:
        raise HTTPException(404, "Topic not found")
    record = db.scalar(
        select(GrammarMastery).where(
            GrammarMastery.user_id == user.id, GrammarMastery.topic_id == topic.id
        )
    )
    return {
        "slug": topic.slug,
        "title": topic.title,
        "title_native": topic.title_native,
        "cefr_level": topic.cefr_level,
        "summary": topic.summary,
        "content": topic.content,
        # Drills without answer keys; grading happens server-side.
        "drills": [
            {"id": d["id"], "prompt": d["prompt"]} for d in topic.drills
        ],
        "prerequisites": topic.prerequisites,
        "mastery": round(record.mastery, 3) if record else 0.0,
    }


class DrillSubmission(BaseModel):
    answers: dict[str, str]


@router.post("/topics/{slug}/drills")
def submit_drills(
    slug: str,
    payload: DrillSubmission,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == slug))
    if topic is None:
        raise HTTPException(404, "Topic not found")
    if not topic.drills:
        raise HTTPException(400, "Topic has no drills yet")

    record = db.scalar(
        select(GrammarMastery).where(
            GrammarMastery.user_id == user.id, GrammarMastery.topic_id == topic.id
        )
    )
    if record is None:
        record = GrammarMastery(user_id=user.id, topic_id=topic.id)
        db.add(record)

    def norm(s: str) -> str:
        return s.strip().lower().replace("ё", "е")

    results = []
    for d in topic.drills:
        submitted = payload.answers.get(d["id"])
        if submitted is None:
            continue
        ok = norm(submitted) in [norm(d["answer"]), *[norm(a) for a in d["accept"]]]
        record.record(ok)
        results.append(
            {
                "id": d["id"],
                "correct": ok,
                "expected": d["answer"],
                "explanation": d.get("explanation", ""),
            }
        )

    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="grammar_drill",
            skill="grammar",
            payload={
                "topic": slug,
                "correct": sum(r["correct"] for r in results),
                "total": len(results),
            },
        )
    )
    db.commit()
    return {"results": results, "mastery": round(record.mastery, 3)}
