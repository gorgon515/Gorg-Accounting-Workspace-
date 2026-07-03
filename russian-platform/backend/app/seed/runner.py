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
    Text,
)
from app.seed.achievements import ACHIEVEMENTS
from app.seed.alphabet import ALPHABET, PRONUNCIATION_RULES
from app.seed.library import TEXTS
from app.seed.course_builder import build_generated_courses
from app.seed.courses import COURSES
from app.seed.grammar_advanced import C2_TOPICS, CONTENT as GRAMMAR_CONTENT
from app.seed.grammar_topics import TOPICS
from app.seed.scenarios import SCENARIOS
from app.seed.vocabulary_core import VOCABULARY
from app.seed.wordlist import W as WORDLIST
from app.services.vocab_factory import build_all


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
    expanded = [e for e in build_all(WORDLIST) if e["lemma"] not in existing_lemmas]
    for item in [*VOCABULARY, *expanded]:
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

    def merged_topics() -> list[dict]:
        """Catalog topics + Phase 2 content fills + C2 tier."""
        merged = []
        for t in TOPICS:
            if t["slug"] in GRAMMAR_CONTENT and not t["content"]:
                t = {**t, **GRAMMAR_CONTENT[t["slug"]]}
            merged.append(t)
        return merged + C2_TOPICS

    existing_topics = set(db.scalars(select(GrammarTopic.slug)))
    for t in merged_topics():
        if t["slug"] not in existing_topics:
            db.add(GrammarTopic(language_id=russian.id, **t))
        else:
            # Content upgrade: fill in topics that were catalog-only before.
            row = db.scalar(
                select(GrammarTopic).where(GrammarTopic.slug == t["slug"])
            )
            if row is not None and not row.content and t["content"]:
                row.content = t["content"]
                row.drills = t["drills"]

    existing_courses = set(db.scalars(select(Course.slug)))
    for c in [*COURSES, *build_generated_courses()]:
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

    existing_texts = set(db.scalars(select(Text.slug)))
    for t in TEXTS:
        if t["slug"] not in existing_texts:
            word_count = sum(len(sent["ru"].split()) for sent in t["sentences"])
            db.add(Text(language_id=russian.id, word_count=word_count, **t))

    existing_achievements = set(db.scalars(select(Achievement.slug)))
    for a in ACHIEVEMENTS:
        if a["slug"] not in existing_achievements:
            db.add(Achievement(**a))

    db.commit()
