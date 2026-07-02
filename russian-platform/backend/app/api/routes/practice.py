"""Adaptive practice: quizzes, cloze drills, pronunciation, dictation,
and AI-generated stories."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import LearningEvent, PronunciationAttempt, User, WritingSubmission
from app.services.cefr import estimate_cefr
from app.services.content_gen import build_cloze_drill, build_quiz, generate_story
from app.services.gamification import touch_streak
from app.services.llm import get_llm_provider
from app.services.speech import score_pronunciation

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/quiz")
def get_quiz(
    size: int = 8,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return build_quiz(db, user.id, size=min(size, 20))


@router.get("/cloze")
def get_cloze(
    size: int = 6,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return build_cloze_drill(db, user.id, size=min(size, 12))


@router.get("/story")
def get_story(
    topic: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    provider = get_llm_provider()
    cefr = estimate_cefr(db, user.id)
    from sqlalchemy import select

    from app.models import Card, Lexeme

    known = list(
        db.scalars(
            select(Lexeme.lemma)
            .join(Card, Card.lexeme_id == Lexeme.id)
            .where(Card.user_id == user.id, Card.state != "new")
            .limit(150)
        )
    )
    try:
        return generate_story(provider, cefr["level"], known, topic)
    except LookupError:
        raise HTTPException(
            409,
            "Personalized stories need a generative LLM provider. Set "
            "RLP_LLM_PROVIDER=anthropic and RLP_ANTHROPIC_API_KEY, or use "
            "/practice/quiz and /practice/cloze which work offline.",
        )


class PronunciationRequest(BaseModel):
    target_text: str
    recognized_text: str  # from browser Web Speech API or a Whisper service


@router.post("/pronunciation")
def check_pronunciation(
    payload: PronunciationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = score_pronunciation(payload.target_text, payload.recognized_text)
    db.add(
        PronunciationAttempt(
            user_id=user.id,
            target_text=payload.target_text,
            overall_score=result["overall_score"],
            phoneme_scores=result["words"],
            feedback=result["feedback"],
        )
    )
    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="pronunciation",
            skill="speaking",
            payload={"score": result["overall_score"]},
        )
    )
    db.commit()
    return result


class WritingRequest(BaseModel):
    prompt: str
    text: str


@router.post("/writing")
def submit_writing(
    payload: WritingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    provider = get_llm_provider()
    corrections: list = []
    quality: float | None = None
    if provider.is_generative:
        import json

        raw = provider.complete(
            "You are a Russian writing tutor. Review the learner's text. Reply "
            'with pure JSON: {"quality_score": 0..1, "corrections": '
            '[{"error": "...", "correction": "...", "explanation": "..."}]}',
            [{"role": "user", "content": f"Prompt: {payload.prompt}\n\n{payload.text}"}],
        )
        try:
            parsed = json.loads(raw)
            corrections = parsed.get("corrections", [])
            quality = parsed.get("quality_score")
        except ValueError:
            pass

    submission = WritingSubmission(
        user_id=user.id,
        prompt=payload.prompt,
        text=payload.text,
        word_count=len(payload.text.split()),
        corrections=corrections,
        quality_score=quality,
    )
    db.add(submission)
    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="writing",
            skill="writing",
            payload={"words": submission.word_count},
        )
    )
    db.commit()
    return {
        "word_count": submission.word_count,
        "quality_score": quality,
        "corrections": corrections,
        "feedback_available": provider.is_generative,
    }
