"""Global search across all content types.

Word search reuses the Dictionary 2.0 ladder: literal substring →
inflected-form index → fuzzy. Everything is stress-insensitive because
lemmas/forms are stored stress-stripped and queries are ё-folded.
"""
from __future__ import annotations

import difflib

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Bookmark,
    Course,
    GrammarTopic,
    InflectionForm,
    Lesson,
    Lexeme,
    Scenario,
    Text,
)
from app.services.morphology import strip_stress

SECTION_LIMIT = 5


def _norm(q: str) -> str:
    return q.strip().lower().replace("ё", "е")


def _word_hits(db: Session, q: str) -> list[dict]:
    pattern = f"%{_norm(q)}%"
    rows = db.scalars(
        select(Lexeme)
        .where(or_(
            func.lower(Lexeme.lemma).like(pattern),
            func.lower(Lexeme.translation).like(pattern),
            func.lower(Lexeme.transliteration).like(pattern),
        ))
        .order_by(Lexeme.frequency_rank.asc().nulls_last())
        .limit(SECTION_LIMIT)
    ).all()
    hits = [
        {"id": l.id, "lemma": l.lemma, "stressed": l.stressed,
         "translation": l.translation, "match": "literal"}
        for l in rows
    ]
    if hits:
        return hits

    form_rows = db.execute(
        select(InflectionForm, Lexeme)
        .join(Lexeme, InflectionForm.lexeme_id == Lexeme.id)
        .where(InflectionForm.form == _norm(q))
        .limit(SECTION_LIMIT)
    ).all()
    hits = [
        {"id": l.id, "lemma": l.lemma, "stressed": l.stressed,
         "translation": l.translation,
         "match": f"form:{f.table_name}.{f.slot}"}
        for f, l in form_rows
    ]
    if hits:
        return hits

    lemmas = {l.lemma: l for l in db.scalars(select(Lexeme))}
    close = difflib.get_close_matches(_norm(q), list(lemmas), n=SECTION_LIMIT,
                                      cutoff=0.72)
    return [
        {"id": lemmas[m].id, "lemma": m, "stressed": lemmas[m].stressed,
         "translation": lemmas[m].translation, "match": "fuzzy"}
        for m in close
    ]


def global_search(db: Session, user_id: int, q: str) -> dict:
    pattern = f"%{_norm(q)}%"
    results: dict[str, list] = {}

    words = _word_hits(db, q)
    if words:
        results["words"] = words

    grammar = db.scalars(
        select(GrammarTopic)
        .where(or_(
            func.lower(GrammarTopic.title).like(pattern),
            func.lower(GrammarTopic.title_native).like(pattern),
            func.lower(GrammarTopic.summary).like(pattern),
        ))
        .order_by(GrammarTopic.order_index)
        .limit(SECTION_LIMIT)
    ).all()
    if grammar:
        results["grammar"] = [
            {"slug": t.slug, "title": t.title, "cefr_level": t.cefr_level,
             "summary": t.summary}
            for t in grammar
        ]

    lessons = db.execute(
        select(Lesson, Course.title)
        .join(Course, Lesson.course_id == Course.id)
        .where(func.lower(Lesson.title).like(pattern))
        .order_by(Course.order_index, Lesson.order_index)
        .limit(SECTION_LIMIT)
    ).all()
    if lessons:
        results["lessons"] = [
            {"slug": lesson.slug, "title": lesson.title, "course": course_title}
            for lesson, course_title in lessons
        ]

    # Text titles carry stress marks («Пого́да»), which SQL LIKE can't
    # normalize — filter in Python (texts are pack-scale, hundreds at most).
    needle = _norm(q)
    texts = [
        t for t in db.scalars(select(Text))
        if needle in strip_stress(t.title).lower().replace("ё", "е")
        or needle in t.title_translation.lower()
        or needle in t.summary.lower()
    ][:SECTION_LIMIT]
    if texts:
        bookmarked = set(db.scalars(
            select(Bookmark.text_id).where(Bookmark.user_id == user_id)
        ))
        results["texts"] = [
            {"slug": t.slug, "title": t.title, "cefr_level": t.cefr_level,
             "kind": t.kind, "bookmarked": t.id in bookmarked}
            for t in texts
        ]

    scenarios = db.scalars(
        select(Scenario)
        .where(or_(
            func.lower(Scenario.title).like(pattern),
            func.lower(Scenario.persona).like(pattern),
            func.lower(Scenario.setting).like(pattern),
        ))
        .limit(SECTION_LIMIT)
    ).all()
    if scenarios:
        results["scenarios"] = [
            {"slug": s.slug, "title": s.title, "cefr_level": s.cefr_level}
            for s in scenarios
        ]

    return results
