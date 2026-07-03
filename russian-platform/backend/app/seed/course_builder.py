"""Data-driven course generation.

Builds themed vocabulary courses from the expanded wordlist: every lesson
teaches ~9 words of one topic with real bidirectional translation
exercises derived from the words' own data, plus a grammar reference that
walks the curriculum in order. As the wordlist grows (Phase 3 bulk
import), the курс catalog grows with it — no code changes.
"""
from __future__ import annotations

import re

from app.seed.wordlist import W
from app.services.morphology import strip_stress

WORDS_PER_LESSON = 9

# Topic order and titles for the generated courses.
A2_COURSE_TOPICS = [
    ("food", "Food & Drink", "Еда и напитки"),
    ("family", "Family & People", "Семья и люди"),
    ("home", "Home & Apartment", "Дом и квартира"),
    ("city", "City & Transport", "Город и транспорт"),
    ("time", "Time & Calendar", "Время и календарь"),
    ("daily", "Daily Verbs", "Глаголы каждый день"),
    ("adjectives", "Describing Things", "Описываем мир"),
    ("nature", "Nature & Weather", "Природа и погода"),
    ("clothing", "Clothing", "Одежда"),
    ("adverbs", "Adverbs & Connectors", "Наречия и союзы"),
]
B1_COURSE_TOPICS = [
    ("travel", "Travel & the World", "Путешествия"),
    ("work", "Work & Study", "Работа и учёба"),
    ("body", "Body & Health", "Тело и здоровье"),
    ("emotions", "Emotions & Character", "Эмоции и характер"),
    ("tech", "Technology & Media", "Технологии и медиа"),
    ("leisure", "Leisure & Sport", "Отдых и спорт"),
    ("communication", "Ideas & Society", "Идеи и общество"),
]

# Grammar curriculum walked across generated lessons, in difficulty order.
A2_GRAMMAR_SEQUENCE = [
    "verb-aspect-intro", "past-tense", "dative-case", "instrumental-case",
    "adjective-declension", "future-tense", "motion-verbs-1",
    "reflexive-verbs", "imperative", "plural-declension",
]
B1_GRAMMAR_SEQUENCE = [
    "short-adjectives", "motion-verbs-2", "aspect-mastery", "comparatives",
    "numerals-declension", "time-expressions", "conditional",
    "relative-clauses", "impersonal",
]


def _primary_translation(translation: str) -> str:
    """First alternative, parentheticals stripped: 'to go (by vehicle, one
    direction)' → 'to go'."""
    first = re.split(r"[;,]", translation)[0]
    return re.sub(r"\s*\(.*?\)", "", first).strip()


def _translation_accepts(translation: str) -> list[str]:
    parts = re.split(r"[;,]", translation)
    cleaned = [re.sub(r"\s*\(.*?\)", "", p).strip() for p in parts]
    return [c for c in cleaned if c]


def _lesson_from_words(
    course_slug: str, topic_title: str, index: int, words: list[tuple],
    grammar_slug: str | None,
) -> dict:
    lemmas = [strip_stress(w[0]) for w in words]
    blocks: list[dict] = [
        {"type": "vocabulary", "lemmas": lemmas, "note": ""},
    ]
    if grammar_slug:
        blocks.append({"type": "grammar_ref", "slug": grammar_slug})

    # Recognition practice: Russian → English.
    exercise_questions = [
        {
            "id": f"e{i}",
            "prompt": f"Translate to English: «{w[0]}»",
            "answer": _primary_translation(w[2]),
            "accept": _translation_accepts(w[2]),
        }
        for i, w in enumerate(words[:4])
    ]
    # Production mastery: English → Russian.
    mastery_questions = [
        {
            "id": f"m{i}",
            "prompt": f"Translate to Russian: “{_primary_translation(w[2])}”"
                      f" ({w[1]})",
            "answer": strip_stress(w[0]),
            "accept": [],
        }
        for i, w in enumerate(words[4:9] if len(words) > 4 else words)
    ]
    blocks.append({"type": "exercise", "questions": exercise_questions})
    blocks.append({"type": "mastery_test", "questions": mastery_questions})

    return {
        "slug": f"{course_slug}-{index:02d}",
        "title": f"{topic_title} {index}" if index > 1 else topic_title,
        "order_index": 0,  # assigned sequentially by the builder
        "objectives": [
            f"Learn {len(lemmas)} words: {topic_title.lower()}",
            "Translate in both directions from memory",
        ],
        "blocks": blocks,
        "new_lemmas": lemmas,
        "grammar_slugs": [grammar_slug] if grammar_slug else [],
        "mastery_threshold": 0.8,
    }


def _build_course(
    slug: str, title: str, cefr: str, order_index: int, description: str,
    topics: list[tuple[str, str, str]], levels: set[str],
    grammar_sequence: list[str],
) -> dict:
    words_by_topic: dict[str, list[tuple]] = {}
    for w in W:
        if w[3] in {t[0] for t in topics} and w[4] in levels:
            words_by_topic.setdefault(w[3], []).append(w)

    lessons: list[dict] = []
    grammar_cursor = 0
    for topic_key, topic_title, _native in topics:
        words = words_by_topic.get(topic_key, [])
        chunks = [
            words[i : i + WORDS_PER_LESSON]
            for i in range(0, len(words), WORDS_PER_LESSON)
        ]
        # Merge a trailing scrap (<4 words) into the previous lesson.
        if len(chunks) > 1 and len(chunks[-1]) < 4:
            chunks[-2].extend(chunks.pop())
        for chunk_index, chunk in enumerate(chunks, start=1):
            grammar_slug = (
                grammar_sequence[grammar_cursor % len(grammar_sequence)]
                if grammar_sequence
                else None
            )
            grammar_cursor += 1
            lessons.append(
                _lesson_from_words(
                    f"{slug}-{topic_key}", topic_title, chunk_index, chunk,
                    grammar_slug,
                )
            )
    for i, lesson in enumerate(lessons, start=1):
        lesson["order_index"] = i

    return {
        "slug": slug,
        "title": title,
        "cefr_level": cefr,
        "order_index": order_index,
        "description": description,
        "lessons": lessons,
    }


def build_generated_courses() -> list[dict]:
    return [
        _build_course(
            "a2-everyday", "Everyday Life", "A2", 3,
            "Themed vocabulary sprints through daily life — food, home, "
            "city, weather — with A2 grammar woven in.",
            A2_COURSE_TOPICS, {"A1", "A2"}, A2_GRAMMAR_SEQUENCE,
        ),
        _build_course(
            "b1-wider-world", "The Wider World", "B1", 4,
            "Travel, work, feelings, and ideas — the vocabulary of real "
            "conversations, with B1 grammar checkpoints.",
            B1_COURSE_TOPICS, {"B1", "B2"}, B1_GRAMMAR_SEQUENCE,
        ),
    ]
