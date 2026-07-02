"""Idempotent database seeding: safe to run on every startup."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    Course,
    ExampleSentence,
    GrammarTopic,
    Language,
    Lesson,
    Lexeme,
    LexemeRelation,
    Scenario,
)
from app.seed.achievements import ACHIEVEMENTS
from app.seed.alphabet import ALPHABET, PRONUNCIATION_RULES
from app.seed.courses import COURSES
from app.seed.grammar_topics import TOPICS
from app.seed.scenarios import SCENARIOS
from app.seed.vocabulary_core import VOCABULARY


def seed_all(db: Session) -> None:
    russian = db.scalar(select(Language).where(Language.code == "ru"))
    if russian is None:
        russian = Language(
            code="ru",
            name_english="Russian",
            name_native="Русский",
            script="Cyrillic",
            metadata_json={
                "alphabet": ALPHABET,
                "pronunciation_rules": PRONUNCIATION_RULES,
            },
        )
        db.add(russian)
        db.flush()

    existing_lemmas = set(
        db.scalars(select(Lexeme.lemma).where(Lexeme.language_id == russian.id))
    )
    for item in VOCABULARY:
        if item["lemma"] in existing_lemmas:
            continue
        item = dict(item)  # keep module-level seed data immutable
        examples = item.pop("examples", [])
        relations = item.pop("relations", [])
        lexeme = Lexeme(language_id=russian.id, **item)
        db.add(lexeme)
        db.flush()
        for text, translation in examples:
            db.add(
                ExampleSentence(lexeme_id=lexeme.id, text=text, translation=translation)
            )
        for relation_type, target, note in relations:
            db.add(
                LexemeRelation(
                    lexeme_id=lexeme.id,
                    relation_type=relation_type,
                    target_lemma=target,
                    note=note,
                )
            )

    existing_topics = set(db.scalars(select(GrammarTopic.slug)))
    for t in TOPICS:
        if t["slug"] not in existing_topics:
            db.add(GrammarTopic(language_id=russian.id, **t))

    existing_courses = set(db.scalars(select(Course.slug)))
    for c in COURSES:
        if c["slug"] in existing_courses:
            continue
        c = dict(c)  # keep module-level seed data immutable
        lessons = c.pop("lessons")
        course = Course(language_id=russian.id, **c)
        db.add(course)
        db.flush()
        for lesson_data in lessons:
            db.add(Lesson(course_id=course.id, **lesson_data))

    existing_scenarios = set(db.scalars(select(Scenario.slug)))
    for s in SCENARIOS:
        if s["slug"] not in existing_scenarios:
            db.add(Scenario(language_id=russian.id, **s))

    existing_achievements = set(db.scalars(select(Achievement.slug)))
    for a in ACHIEVEMENTS:
        if a["slug"] not in existing_achievements:
            db.add(Achievement(**a))

    db.commit()
