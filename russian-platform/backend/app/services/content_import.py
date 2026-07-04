"""Bulk content import validation.

The path to 6,000–8,000 words and 150+ texts is licensed/community
datasets flowing through these validators — not hand-authored code. The
validators enforce the same invariants the curated seed obeys, so
imported content is indistinguishable from first-party content
downstream (SRS, курс builder, dictionary, exams all consume it).

Dataset formats are documented in docs/CONTENT_PIPELINE.md. Both CLIs
(tools/import_vocabulary.py, tools/import_texts.py) are thin wrappers
around these functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExampleSentence, Language, Lexeme, LexemeRelation, Text
from app.services.morphology import STRESS, VOWELS, strip_stress
from app.services.vocab_factory import CEFR_DIFFICULTY, POS_MAP, build_entry

VALID_CEFR = set(CEFR_DIFFICULTY) | {"A0"}
VALID_KINDS = {"story", "dialogue", "fairy_tale", "article", "news", "recipe",
               "history", "science", "culture", "blog"}


@dataclass
class ImportReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid_items: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        return (
            f"{len(self.valid_items)} valid, {len(self.errors)} errors, "
            f"{len(self.warnings)} warnings"
        )


def _syllables(word: str) -> int:
    return sum(1 for ch in strip_stress(word).lower() if ch in VOWELS)


def validate_vocabulary_dataset(
    items: list, db: Session | None = None
) -> ImportReport:
    """Validate a vocabulary dataset (compact rows, same shape as
    seed/wordlist.py but JSON: [stressed, pos, translation, topic, cefr,
    extras?]). Every row is expanded through the morphology factory so
    import failures surface before anything touches the database."""
    report = ImportReport()
    seen: set[str] = set()
    existing: set[str] = set()
    if db is not None:
        existing = set(db.scalars(select(Lexeme.lemma)))

    for index, row in enumerate(items):
        where = f"row {index}"
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            report.errors.append(f"{where}: expected [stressed, pos, translation, topic, cefr, extras?]")
            continue
        stressed, pos, translation, topic, cefr = row[:5]
        extras = row[5] if len(row) > 5 else {}
        where = f"row {index} «{strip_stress(str(stressed))}»"

        if pos not in POS_MAP:
            report.errors.append(f"{where}: unknown pos '{pos}' (valid: {sorted(POS_MAP)})")
            continue
        if cefr not in VALID_CEFR:
            report.errors.append(f"{where}: invalid CEFR '{cefr}'")
            continue
        if not translation or not str(translation).strip():
            report.errors.append(f"{where}: empty translation")
            continue
        if _syllables(str(stressed)) >= 2 and STRESS not in str(stressed) \
                and "ё" not in str(stressed).lower():
            report.errors.append(
                f"{where}: multisyllabic word missing stress mark (U+0301)"
            )
            continue

        try:
            entry = build_entry((stressed, pos, translation, topic, cefr, extras))
        except ValueError as exc:
            report.errors.append(f"{where}: {exc}")
            continue

        if entry["lemma"] in seen:
            report.errors.append(f"{where}: duplicate within dataset")
            continue
        seen.add(entry["lemma"])
        if entry["lemma"] in existing:
            report.warnings.append(f"{where}: already in database — will be skipped")
            continue

        if pos == "n" and not entry["inflections"].get("declension"):
            report.warnings.append(f"{where}: noun has no declension table (indeclinable?)")
        if pos == "v" and not entry["inflections"].get("present"):
            report.warnings.append(f"{where}: verb has no present-tense table")
        if not extras.get("examples"):
            report.warnings.append(f"{where}: no example sentences")

        report.valid_items.append(entry)
    return report


def apply_vocabulary(db: Session, entries: list[dict]) -> int:
    """Insert validated entries. Same code path shape as the seed runner."""
    russian = db.scalar(select(Language).where(Language.code == "ru"))
    if russian is None:
        raise RuntimeError("Language 'ru' not seeded — start the app once first")
    inserted = 0
    for item in entries:
        item = dict(item)
        examples = item.pop("examples", [])
        relations = item.pop("relations", [])
        lexeme = Lexeme(language_id=russian.id, **item)
        db.add(lexeme)
        db.flush()
        for text, translation in examples:
            db.add(ExampleSentence(lexeme_id=lexeme.id, text=text,
                                   translation=translation))
        for relation_type, target, note in relations:
            db.add(LexemeRelation(lexeme_id=lexeme.id,
                                  relation_type=relation_type,
                                  target_lemma=target, note=note))
        inserted += 1
    db.commit()
    return inserted


def validate_text_dataset(items: list, db: Session | None = None) -> ImportReport:
    """Validate a library-text dataset (same shape as seed/library.py)."""
    report = ImportReport()
    seen: set[str] = set()
    existing: set[str] = set()
    if db is not None:
        existing = set(db.scalars(select(Text.slug)))

    for index, item in enumerate(items):
        where = f"text {index}"
        if not isinstance(item, dict):
            report.errors.append(f"{where}: expected an object")
            continue
        missing = [k for k in ("slug", "title", "title_translation", "kind",
                               "cefr_level", "summary", "sentences") if k not in item]
        if missing:
            report.errors.append(f"{where}: missing fields {missing}")
            continue
        where = f"text {index} '{item['slug']}'"
        if item["kind"] not in VALID_KINDS:
            report.errors.append(f"{where}: kind must be one of {sorted(VALID_KINDS)}")
            continue
        if item["cefr_level"] not in VALID_CEFR:
            report.errors.append(f"{where}: invalid CEFR '{item['cefr_level']}'")
            continue
        if item["slug"] in seen:
            report.errors.append(f"{where}: duplicate slug within dataset")
            continue
        seen.add(item["slug"])
        if item["slug"] in existing:
            report.warnings.append(f"{where}: already in database — will be skipped")
            continue

        sentences = item["sentences"]
        if not isinstance(sentences, list) or len(sentences) < 3:
            report.errors.append(f"{where}: needs at least 3 sentences")
            continue
        bad = [i for i, s in enumerate(sentences)
               if not isinstance(s, dict) or not s.get("ru") or not s.get("en")]
        if bad:
            report.errors.append(f"{where}: sentences {bad} missing ru/en")
            continue
        unstressed = [
            i for i, s in enumerate(sentences)
            if any(_syllables(w) >= 2 and STRESS not in w and "ё" not in w.lower()
                   for w in s["ru"].split())
        ]
        if len(unstressed) > len(sentences) // 2:
            report.warnings.append(
                f"{where}: most sentences lack stress marks — learners rely on them"
            )
        normalized = {
            **item,
            "sentences": [
                {"ru": s["ru"], "en": s["en"], "audio_url": s.get("audio_url")}
                for s in sentences
            ],
            "topic": item.get("topic", "general"),
        }
        report.valid_items.append(normalized)
    return report


def apply_texts(db: Session, items: list[dict]) -> int:
    russian = db.scalar(select(Language).where(Language.code == "ru"))
    if russian is None:
        raise RuntimeError("Language 'ru' not seeded — start the app once first")
    inserted = 0
    for item in items:
        word_count = sum(len(s["ru"].split()) for s in item["sentences"])
        db.add(Text(language_id=russian.id, word_count=word_count, **item))
        inserted += 1
    db.commit()
    return inserted
