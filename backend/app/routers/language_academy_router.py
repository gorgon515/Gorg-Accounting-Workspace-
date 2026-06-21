"""Language Academy API — HELIOS Phase 15.75 Part 2.

A full language-learning platform: CEFR curriculum, deterministic lessons,
an SRS vocabulary system, a grammar academy with mistake detection, a
conversation simulator, listening + pronunciation labs, assessment/placement,
and a daily coach. All handlers lazily import the engine.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/language-academy", tags=["language-academy"])


# ── Request bodies ───────────────────────────────────────────────────────────
class GenerateLessonBody(BaseModel):
    language: str
    level: str
    topic: str


class ReviewBody(BaseModel):
    language: str
    limit: int = 20


class GradeBody(BaseModel):
    card_id: str
    grade: int


class GrammarCheckBody(BaseModel):
    language: str
    text: str
    rule_id: Optional[str] = None


class ConversationStartBody(BaseModel):
    language: str
    scenario: str
    level: str = "A2"


class ConversationRespondBody(BaseModel):
    session_id: str
    text: str


class ListeningGradeBody(BaseModel):
    ex_id: str
    answers: list


class PronunciationBody(BaseModel):
    language: str
    target: str
    attempt: str


class PlacementBody(BaseModel):
    language: str
    answers: Optional[list] = None


class SubmitBody(BaseModel):
    test_id: str
    answers: list


class CoachBody(BaseModel):
    language: str


# ── Reference ────────────────────────────────────────────────────────────────
@router.get("/languages")
def languages():
    from language_academy.engine import get_language_academy
    return get_language_academy().languages()


# ── Curriculum ───────────────────────────────────────────────────────────────
@router.get("/curriculum")
def curriculum(language: str, level: Optional[str] = None):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().get_curriculum(language, level)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Lessons ──────────────────────────────────────────────────────────────────
@router.get("/lessons")
def list_lessons(language: Optional[str] = None, level: Optional[str] = None,
                 topic: Optional[str] = None, limit: int = 200):
    from language_academy.engine import get_language_academy
    return get_language_academy().list_lessons(language, level, topic, limit)


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: str):
    from language_academy.engine import get_language_academy
    lesson = get_language_academy().get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("/lessons/generate")
def generate_lesson(body: GenerateLessonBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().generate_lesson(body.language, body.level, body.topic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Vocabulary ───────────────────────────────────────────────────────────────
@router.get("/vocabulary")
def vocabulary(language: str, topic: Optional[str] = None,
               level: Optional[str] = None, limit: int = 100):
    from language_academy.engine import get_language_academy
    return get_language_academy().list_vocabulary(language, topic, level, limit)


@router.get("/vocabulary/topics")
def vocabulary_topics(language: Optional[str] = None):
    from language_academy.engine import get_language_academy
    return get_language_academy().vocabulary_topics(language)


@router.post("/vocabulary/review")
def vocabulary_review(body: ReviewBody):
    from language_academy.engine import get_language_academy
    return get_language_academy().review_vocabulary(body.language, body.limit)


@router.post("/vocabulary/grade")
def vocabulary_grade(body: GradeBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().grade_vocabulary(body.card_id, body.grade)
    except KeyError:
        raise HTTPException(status_code=404, detail="Card not found")


# ── Grammar ──────────────────────────────────────────────────────────────────
@router.get("/grammar")
def grammar(language: str, level: Optional[str] = None):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().grammar_lessons(language, level)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/grammar/{rule_id}")
def grammar_rule(rule_id: str):
    from language_academy.engine import get_language_academy
    rule = get_language_academy().get_grammar_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Grammar rule not found")
    return rule


@router.post("/grammar/check")
def grammar_check(body: GrammarCheckBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().check_grammar(body.language, body.text, body.rule_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Conversation ─────────────────────────────────────────────────────────────
@router.get("/conversation/scenarios")
def conversation_scenarios():
    from language_academy.engine import get_language_academy
    return get_language_academy().conversation_scenarios()


@router.post("/conversation/start")
def conversation_start(body: ConversationStartBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().start_conversation(body.language, body.scenario, body.level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/conversation/respond")
def conversation_respond(body: ConversationRespondBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().respond_conversation(body.session_id, body.text)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


# ── Listening ────────────────────────────────────────────────────────────────
@router.get("/listening")
def listening(language: Optional[str] = None, level: Optional[str] = None):
    from language_academy.engine import get_language_academy
    return get_language_academy().list_listening(language, level)


@router.get("/listening/{ex_id}")
def listening_get(ex_id: str, language: Optional[str] = None):
    from language_academy.engine import get_language_academy
    ex = get_language_academy().get_listening(ex_id, language)
    if not ex:
        raise HTTPException(status_code=404, detail="Listening exercise not found")
    return ex


@router.post("/listening/grade")
def listening_grade(body: ListeningGradeBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().grade_listening(body.ex_id, body.answers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Listening exercise not found")


# ── Pronunciation ────────────────────────────────────────────────────────────
@router.post("/pronunciation/score")
def pronunciation_score(body: PronunciationBody):
    from language_academy.engine import get_language_academy
    return get_language_academy().score_pronunciation(body.language, body.target, body.attempt)


# ── Assessment ───────────────────────────────────────────────────────────────
@router.post("/assessment/placement")
def assessment_placement(body: PlacementBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().placement(body.language, body.answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessment/tests")
def assessment_tests(language: Optional[str] = None, level: Optional[str] = None,
                     kind: Optional[str] = None):
    from language_academy.engine import get_language_academy
    return get_language_academy().list_tests(language, level, kind)


@router.get("/assessment/tests/{test_id}")
def assessment_test(test_id: str):
    from language_academy.engine import get_language_academy
    test = get_language_academy().get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test


@router.post("/assessment/submit")
def assessment_submit(body: SubmitBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().submit_test(body.test_id, body.answers)
    except KeyError:
        raise HTTPException(status_code=404, detail="Test not found")


# ── Coach ────────────────────────────────────────────────────────────────────
@router.post("/coach/today")
def coach_today(body: CoachBody):
    from language_academy.engine import get_language_academy
    try:
        return get_language_academy().coach_today(body.language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Stats ────────────────────────────────────────────────────────────────────
@router.get("/stats")
def stats():
    from language_academy.engine import get_language_academy
    return get_language_academy().stats()
