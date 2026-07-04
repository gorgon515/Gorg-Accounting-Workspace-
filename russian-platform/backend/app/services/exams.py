"""Exam engine: seeded, deterministic, graded server-side.

An exam is fully determined by (level, seed): the builder samples
questions from the content DB with a seeded RNG, so the server can
rebuild the identical exam at grading time and never has to store or
ship answer keys. Sections:

  vocabulary — multiple choice (RU→EN), distractors share part of speech
  grammar    — drills from topics at/below the exam level
  reading    — match a sentence from a level-appropriate text to its
               translation among distractor translations
  listening  — dictation (client TTS speaks; learner types)

Placement = one band of questions per level A1→C2; the learner places at
the highest level whose band they clear at ≥60%.
"""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GrammarTopic, Lexeme, Text
from app.services.morphology import strip_stress
from app.services.text_utils import answer_matches

EXAM_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_ORDER = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
TIME_LIMITS_MINUTES = {"A1": 20, "A2": 25, "B1": 30, "B2": 35, "C1": 40, "C2": 45}
PASS_THRESHOLD = 0.7
PLACEMENT_BAND_THRESHOLD = 0.6

SECTION_SIZES = {"vocabulary": 8, "grammar": 8, "reading": 4, "listening": 3}


def _levels_at_or_below(level: str) -> list[str]:
    return LEVEL_ORDER[: LEVEL_ORDER.index(level) + 1]


def _vocab_questions(db: Session, level: str, rng: random.Random, count: int) -> list[dict]:
    pool = db.scalars(
        select(Lexeme)
        .where(Lexeme.cefr_level.in_(_levels_at_or_below(level)))
        .order_by(Lexeme.id)
    ).all()
    # Prefer words AT the level; pad with easier ones.
    at_level = [l for l in pool if l.cefr_level == level] or pool
    chosen = rng.sample(at_level, min(count, len(at_level)))
    questions = []
    for i, lexeme in enumerate(chosen):
        same_pos = [l for l in pool
                    if l.part_of_speech == lexeme.part_of_speech and l.id != lexeme.id]
        distractors = rng.sample(same_pos, min(3, len(same_pos)))
        options = [lexeme.translation] + [d.translation for d in distractors]
        rng.shuffle(options)
        questions.append({
            "id": f"v{i}",
            "type": "choice",
            "prompt": f"«{lexeme.stressed}» means:",
            "options": options,
            "_answer": lexeme.translation,
        })
    return questions


def _grammar_questions(db: Session, level: str, rng: random.Random, count: int) -> list[dict]:
    topics = db.scalars(
        select(GrammarTopic)
        .where(GrammarTopic.cefr_level.in_(_levels_at_or_below(level)))
        .order_by(GrammarTopic.order_index)
    ).all()
    drills = [(t.slug, d) for t in topics for d in t.drills]
    chosen = rng.sample(drills, min(count, len(drills)))
    return [{
        "id": f"g{i}",
        "type": "text",
        "prompt": drill["prompt"],
        "topic": slug,
        "_answer": drill["answer"],
        "_accept": drill.get("accept", []),
    } for i, (slug, drill) in enumerate(chosen)]


def _reading_questions(db: Session, level: str, rng: random.Random, count: int) -> list[dict]:
    texts = db.scalars(
        select(Text)
        .where(Text.cefr_level.in_(_levels_at_or_below(level)))
        .order_by(Text.id)
    ).all()
    sentences = [s for t in texts for s in t.sentences]
    if len(sentences) < 4:
        return []
    chosen = rng.sample(sentences, min(count, len(sentences)))
    questions = []
    for i, sentence in enumerate(chosen):
        others = [s["en"] for s in sentences if s["en"] != sentence["en"]]
        options = [sentence["en"]] + rng.sample(others, min(3, len(others)))
        rng.shuffle(options)
        questions.append({
            "id": f"r{i}",
            "type": "choice",
            "prompt": f"Choose the correct translation: «{sentence['ru']}»",
            "options": options,
            "_answer": sentence["en"],
        })
    return questions


def _listening_questions(db: Session, level: str, rng: random.Random, count: int) -> list[dict]:
    texts = db.scalars(
        select(Text)
        .where(Text.cefr_level.in_(_levels_at_or_below(level)))
        .order_by(Text.id)
    ).all()
    sentences = [s for t in texts for s in t.sentences
                 if len(strip_stress(s["ru"]).split()) <= 8]
    chosen = rng.sample(sentences, min(count, len(sentences)))
    questions = []
    for i, sentence in enumerate(chosen):
        plain = strip_stress(sentence["ru"])
        answer = plain.replace("«", "").replace("»", "").replace("—", "").rstrip(".!?").strip()
        questions.append({
            "id": f"l{i}",
            "type": "dictation",
            "prompt": f"Listen and type what you hear ({i + 1}/{count}):",
            "speak": plain,
            "_answer": answer,
        })
    return questions


def build_level_exam(db: Session, level: str, seed: str) -> dict:
    """Deterministic exam for (level, seed). Private keys (_answer) are
    stripped before the exam leaves the API."""
    rng = random.Random(f"{level}:{seed}")
    return {
        "level": level,
        "seed": seed,
        "time_limit_minutes": TIME_LIMITS_MINUTES[level],
        "pass_threshold": PASS_THRESHOLD,
        "sections": {
            "vocabulary": _vocab_questions(db, level, rng, SECTION_SIZES["vocabulary"]),
            "grammar": _grammar_questions(db, level, rng, SECTION_SIZES["grammar"]),
            "reading": _reading_questions(db, level, rng, SECTION_SIZES["reading"]),
            "listening": _listening_questions(db, level, rng, SECTION_SIZES["listening"]),
        },
    }


def strip_answer_keys(exam: dict) -> dict:
    return {
        **exam,
        "sections": {
            name: [{k: v for k, v in q.items() if not k.startswith("_")}
                   for q in questions]
            for name, questions in exam["sections"].items()
        },
    }


def grade_exam(exam: dict, answers: dict[str, str]) -> dict:
    """Grade submitted answers against the rebuilt exam."""
    section_results: dict[str, dict] = {}
    weak_topics: dict[str, int] = {}
    total_correct = 0
    total_questions = 0

    for name, questions in exam["sections"].items():
        correct = 0
        detail = []
        for q in questions:
            submitted = (answers.get(q["id"]) or "").strip()
            ok = answer_matches(submitted, q["_answer"], q.get("_accept"))
            correct += ok
            total_correct += ok
            total_questions += 1
            if not ok and q.get("topic"):
                weak_topics[q["topic"]] = weak_topics.get(q["topic"], 0) + 1
            detail.append({"id": q["id"], "correct": ok, "expected": q["_answer"]})
        section_results[name] = {
            "correct": correct,
            "total": len(questions),
            "score": round(correct / len(questions), 3) if questions else 1.0,
            "detail": detail,
        }

    score = round(total_correct / total_questions, 3) if total_questions else 0.0
    weaknesses = sorted(weak_topics, key=weak_topics.get, reverse=True)
    worst_section = min(
        (s for s in section_results.items() if s[1]["total"]),
        key=lambda s: s[1]["score"],
        default=(None, None),
    )[0]
    return {
        "score": score,
        "passed": score >= exam["pass_threshold"],
        "sections": {k: {kk: vv for kk, vv in v.items() if kk != "detail"}
                     for k, v in section_results.items()},
        "detail": {k: v["detail"] for k, v in section_results.items()},
        "weak_topics": weaknesses,
        "worst_section": worst_section,
        "recommended_lessons": [f"grammar-{slug}" for slug in weaknesses[:3]],
    }


def build_placement_exam(db: Session, seed: str) -> dict:
    """One band per level: 4 vocabulary + 4 grammar questions each."""
    bands = {}
    for level in EXAM_LEVELS:
        rng = random.Random(f"placement:{level}:{seed}")
        bands[level] = (
            _vocab_questions(db, level, rng, 4)
            + [{**q, "id": f"{q['id']}x"} for q in _grammar_questions(db, level, rng, 4)]
        )
    return {"seed": seed, "kind": "placement",
            "time_limit_minutes": 30, "bands": bands}


def grade_placement(exam: dict, answers: dict[str, str]) -> dict:
    """Place at the highest level whose band scores ≥ 60%; A0 if none."""
    band_scores = {}
    placed = "A0"
    for level in EXAM_LEVELS:
        questions = exam["bands"][level]
        correct = sum(
            answer_matches((answers.get(f"{level}:{q['id']}") or ""),
                           q["_answer"], q.get("_accept"))
            for q in questions
        )
        score = correct / len(questions) if questions else 0.0
        band_scores[level] = round(score, 3)
        if score >= PLACEMENT_BAND_THRESHOLD:
            placed = level
        else:
            break  # bands are ordered; stop at the first failed level
    return {"placed_level": placed, "band_scores": band_scores}
