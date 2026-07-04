"""Writing coach: analysis, history, and recurring-mistake tracking.

Supersedes the bare /practice/writing endpoint (kept for compatibility)
with real offline analysis plus LLM enrichment when configured.
"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import LearningEvent, User, WritingSubmission
from app.services.gamification import award_xp, touch_streak
from app.services.llm import get_llm_provider
from app.services.writing_coach import analyze_writing

router = APIRouter(prefix="/writing", tags=["writing"])

PROMPTS = {
    "journal": "Напиши́те о ва́шем дне. (Write about your day.)",
    "email": "Напиши́те коро́ткое письмо́ дру́гу. (Write a short email to a friend.)",
    "story": "Напиши́те коро́ткую исто́рию. (Write a short story.)",
    "essay": "Напиши́те эссе́ на те́му «Мой го́род». (Write an essay: 'My city'.)",
    "summary": "Переска́жите после́дний текст из библиоте́ки. (Summarize the last library text.)",
    "letter": "Напиши́те официа́льное письмо́. (Write a formal letter.)",
    "dialogue": "Напиши́те диало́г в магази́не. (Write a shop dialogue.)",
}


@router.get("/prompts")
def writing_prompts(user: User = Depends(get_current_user)):
    return [{"kind": kind, "prompt": prompt} for kind, prompt in PROMPTS.items()]


class WritingRequest(BaseModel):
    kind: str = "journal"
    prompt: str = ""
    text: str = Field(min_length=1, max_length=10000)


@router.post("/analyze")
def analyze(
    payload: WritingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = analyze_writing(db, payload.text)

    provider = get_llm_provider()
    llm_corrections: list = []
    quality: float | None = None
    if provider.is_generative:
        raw = provider.complete(
            "You are a Russian writing tutor. Review the learner's text. Reply "
            'with pure JSON: {"quality_score": 0..1, "corrections": '
            '[{"error": "...", "correction": "...", "explanation": "..."}]}',
            [{"role": "user",
              "content": f"Prompt: {payload.prompt or payload.kind}\n\n{payload.text}"}],
        )
        try:
            parsed = json.loads(raw)
            llm_corrections = parsed.get("corrections", [])
            quality = parsed.get("quality_score")
        except ValueError:
            pass

    submission = WritingSubmission(
        user_id=user.id,
        prompt=payload.prompt or PROMPTS.get(payload.kind, payload.kind),
        text=payload.text,
        word_count=analysis["word_count"],
        corrections=llm_corrections or analysis["unknown_words"],
        quality_score=quality if quality is not None else analysis["dictionary_coverage"],
    )
    db.add(submission)
    award_xp(user, max(5, min(25, analysis["word_count"] // 10)))
    touch_streak(user)
    db.add(LearningEvent(
        user_id=user.id, event_type="writing", skill="writing",
        payload={"kind": payload.kind, "words": analysis["word_count"],
                 "unknown": len(analysis["unknown_words"])},
    ))
    db.commit()
    return {
        **analysis,
        "llm_corrections": llm_corrections,
        "llm_feedback_available": provider.is_generative,
        "submission_id": submission.id,
    }


@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    submissions = db.scalars(
        select(WritingSubmission)
        .where(WritingSubmission.user_id == user.id)
        .order_by(WritingSubmission.created_at.desc())
        .limit(50)
    ).all()
    # Recurring mistakes: unknown/corrected words seen in 2+ submissions.
    seen: dict[str, int] = {}
    for s in submissions:
        words = {c.get("word") or c.get("error") for c in (s.corrections or [])}
        for word in filter(None, words):
            seen[word] = seen.get(word, 0) + 1
    recurring = sorted(
        [{"word": w, "times": n} for w, n in seen.items() if n >= 2],
        key=lambda item: -item["times"],
    )
    return {
        "submissions": [
            {
                "id": s.id, "prompt": s.prompt, "word_count": s.word_count,
                "quality_score": s.quality_score,
                "created_at": s.created_at.isoformat(),
            }
            for s in submissions
        ],
        "recurring_mistakes": recurring[:10],
        "total_words_written": sum(s.word_count for s in submissions),
    }
