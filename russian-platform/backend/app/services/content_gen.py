"""Adaptive content generation.

With a generative LLM provider, produces personalized stories, dialogues
and drills at the learner's level. Offline, composes practice content
from the seeded database (weak-word quizzes, cloze drills from example
sentences) — deterministic but still personalized, since it is driven by
the learner's own SRS state and mistake history.
"""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Card, ExampleSentence, Lexeme
from app.services.llm import LLMProvider
from app.services.speech import strip_stress


def weakest_lexemes(db: Session, user_id: int, limit: int = 10) -> list[Lexeme]:
    """The learner's shakiest vocabulary: low stability first, then hardest."""
    rows = db.execute(
        select(Lexeme, Card)
        .join(Card, Card.lexeme_id == Lexeme.id)
        .where(Card.user_id == user_id, Card.state != "new")
        .order_by(Card.stability.asc(), Card.difficulty.desc())
        .limit(limit)
    ).all()
    return [lexeme for lexeme, _ in rows]


def build_quiz(db: Session, user_id: int, size: int = 8, seed: int | None = None) -> dict:
    """Multiple-choice quiz targeting weak vocabulary; distractors are
    same-part-of-speech words so guessing by category doesn't work."""
    rng = random.Random(seed)
    targets = weakest_lexemes(db, user_id, limit=size)
    if len(targets) < size:
        extra = list(
            db.scalars(
                select(Lexeme).where(Lexeme.cefr_level.in_(["A1", "A2"])).limit(50)
            )
        )
        rng.shuffle(extra)
        seen = {t.id for t in targets}
        targets += [e for e in extra if e.id not in seen][: size - len(targets)]

    questions = []
    for lexeme in targets:
        pool = list(
            db.scalars(
                select(Lexeme)
                .where(
                    Lexeme.part_of_speech == lexeme.part_of_speech,
                    Lexeme.id != lexeme.id,
                )
                .limit(30)
            )
        )
        rng.shuffle(pool)
        options = [lexeme.translation] + [p.translation for p in pool[:3]]
        rng.shuffle(options)
        questions.append(
            {
                "id": f"q{lexeme.id}",
                "prompt": lexeme.stressed,
                "options": options,
                "answer": lexeme.translation,
            }
        )
    return {"type": "vocabulary_quiz", "questions": questions}


def build_cloze_drill(db: Session, user_id: int, size: int = 6, seed: int | None = None) -> dict:
    """Fill-in-the-blank sentences built from curated examples of the
    learner's weak words."""
    rng = random.Random(seed)
    targets = weakest_lexemes(db, user_id, limit=size * 2)
    items = []
    for lexeme in targets:
        examples = list(
            db.scalars(
                select(ExampleSentence).where(ExampleSentence.lexeme_id == lexeme.id)
            )
        )
        if not examples:
            continue
        example = rng.choice(examples)
        plain = strip_stress(example.text)
        answer = strip_stress(lexeme.lemma)
        if answer not in plain.lower():
            continue
        idx = plain.lower().index(answer)
        blanked = plain[:idx] + "____" + plain[idx + len(answer):]
        items.append(
            {
                "id": f"c{example.id}",
                "sentence": blanked,
                "translation": example.translation,
                "answer": answer,
            }
        )
        if len(items) >= size:
            break
    return {"type": "cloze_drill", "questions": items}


def generate_story(
    provider: LLMProvider, level: str, known_words: list[str], topic: str | None = None
) -> dict:
    """Personalized graded reading. Requires a generative provider; the
    API returns 409 with guidance when only offline content is available."""
    if not provider.is_generative:
        raise LookupError("generative_provider_required")
    system = (
        "You are a Russian graded-reader author. Write a short story in "
        f"Russian at CEFR {level}, preferring these known words: "
        f"{', '.join(known_words[:120])}. Use stress marks on every "
        "multisyllabic word. After the story add '---' and an English "
        "translation, then '###' and a JSON array of 5 comprehension "
        'questions [{"q": ..., "a": ...}].'
    )
    user = f"Topic: {topic or 'everyday life in a Russian city'}"
    raw = provider.complete(system, [{"role": "user", "content": user}], max_tokens=2048)
    story, _, rest = raw.partition("---")
    translation, _, questions_raw = rest.partition("###")
    import json

    try:
        questions = json.loads(questions_raw.strip()) if questions_raw.strip() else []
    except ValueError:
        questions = []
    return {
        "type": "story",
        "level": level,
        "text": story.strip(),
        "translation": translation.strip(),
        "questions": questions,
    }
