from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import (
    ConversationSession,
    ConversationTurn,
    LearningEvent,
    Scenario,
    User,
)
from app.services.conversation_engine import ConversationEngine
from app.services.gamification import award_xp, evaluate_achievements, touch_streak
from app.services.llm import get_llm_provider
from app.services.tutor import MODES, PERSONALITIES, TutorEngine, offline_practice_plan

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.get("/tutor/plan")
def tutor_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Personalized practice plan from the learner's real weaknesses.
    Works fully offline — this is the tutor's deterministic core."""
    return offline_practice_plan(db, user.id)


class TutorMessage(BaseModel):
    text: str
    mode: str = "free"
    personality: str = "warm"
    history: list[dict] = []


@router.post("/tutor")
def tutor_chat(
    payload: TutorMessage,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Free-form tutoring chat (Socratic, storytelling, debate, ...).
    Requires a generative LLM provider; offline callers get 409 with
    guidance toward /tutor/plan and the scripted scenarios."""
    if payload.mode not in MODES:
        raise HTTPException(422, f"mode must be one of {sorted(MODES)}")
    if payload.personality not in PERSONALITIES:
        raise HTTPException(422, f"personality must be one of {sorted(PERSONALITIES)}")
    engine = TutorEngine(get_llm_provider())
    if not engine.is_generative:
        raise HTTPException(
            409,
            "The free-form tutor needs a generative LLM provider "
            "(RLP_LLM_PROVIDER=anthropic). Offline, use /conversation/tutor/plan "
            "and the scripted scenarios.",
        )
    reply = engine.reply(
        db, user.id, payload.mode, payload.personality, payload.history, payload.text
    )
    award_xp(user, get_settings().xp_per_conversation_turn)
    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="conversation_turn",
            skill="speaking",
            payload={"tutor_mode": payload.mode},
        )
    )
    db.commit()
    return reply


@router.get("/scenarios")
def list_scenarios(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    scenarios = db.scalars(select(Scenario).order_by(Scenario.cefr_level)).all()
    return [
        {
            "slug": s.slug,
            "title": s.title,
            "persona": s.persona,
            "setting": s.setting,
            "cefr_level": s.cefr_level,
            "description": s.description,
            "key_vocabulary": s.key_vocabulary,
        }
        for s in scenarios
    ]


@router.post("/sessions/{scenario_slug}", status_code=201)
def start_session(
    scenario_slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scenario = db.scalar(select(Scenario).where(Scenario.slug == scenario_slug))
    if scenario is None:
        raise HTTPException(404, "Scenario not found")

    # Carry memory over from the learner's last session in this scenario.
    previous = db.scalar(
        select(ConversationSession)
        .where(
            ConversationSession.user_id == user.id,
            ConversationSession.scenario_id == scenario.id,
        )
        .order_by(ConversationSession.started_at.desc())
    )
    memory = {}
    if previous and previous.memory:
        memory = {
            "completions": previous.memory.get("completions", 0),
            "difficulty": previous.memory.get("difficulty", scenario.cefr_level),
        }

    session = ConversationSession(
        user_id=user.id, scenario_id=scenario.id, memory=memory
    )
    db.add(session)
    db.flush()

    engine = ConversationEngine(get_llm_provider())
    opening = engine.opening_line(scenario)
    db.add(
        ConversationTurn(
            session_id=session.id,
            turn_index=0,
            role="partner",
            text=opening["text"],
            translation=opening.get("translation"),
        )
    )
    db.commit()
    return {"session_id": session.id, "opening": opening}


class MessageRequest(BaseModel):
    text: str


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    payload: MessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    session = db.scalar(
        select(ConversationSession)
        .options(selectinload(ConversationSession.turns))
        .where(ConversationSession.id == session_id)
    )
    if session is None or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    scenario = db.get(Scenario, session.scenario_id)

    history = [{"role": t.role, "text": t.text} for t in session.turns]
    next_index = len(session.turns)

    db.add(
        ConversationTurn(
            session_id=session.id,
            turn_index=next_index,
            role="user",
            text=payload.text,
        )
    )

    engine = ConversationEngine(get_llm_provider())
    reply = engine.reply(scenario, session, history, payload.text)

    db.add(
        ConversationTurn(
            session_id=session.id,
            turn_index=next_index + 1,
            role="partner",
            text=reply["text"],
            translation=reply.get("translation"),
            corrections=reply.get("corrections", []),
        )
    )
    if reply.get("completed"):
        session.ended_at = datetime.now(timezone.utc)

    award_xp(user, settings.xp_per_conversation_turn)
    touch_streak(user)
    db.add(
        LearningEvent(
            user_id=user.id,
            event_type="conversation_turn",
            skill="speaking",
            payload={"session_id": session.id, "scenario": scenario.slug},
        )
    )
    evaluate_achievements(db, user)
    db.commit()
    return reply
