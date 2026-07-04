"""Content pack system: engines and content are separate deliverables.

A pack is a single JSON document:

    {"manifest": {name, version, format, language, counts, checksum,
                  signature?},
     "content": {"vocabulary": [full lexeme entries],
                 "texts": [...], "grammar_topics": [...], "scenarios": [...]}}

* **Integrity**: `checksum` = sha256 of the canonical (sorted-key) JSON of
  `content`. Any bit-flip fails validation.
* **Signature**: optional HMAC-SHA256 of the checksum with a shared pack
  key (RLP_PACK_KEY or explicit key). Unsigned packs install with a
  warning; a bad signature is a hard error.
* **Provenance**: every inserted row id is recorded in `installed_packs`,
  making rollback and upgrades exact.
* **Incremental updates**: installing v2 of a pack inserts only content
  that is new (same skip-existing semantics as the seed runner), then
  updates the provenance record.
* **Progress safety**: rollback refuses (without `force`) to delete
  lexemes the learner has SRS cards on — user progress is never silently
  destroyed.

A new language = a pack with `language: "xx"` + a `Language` row entry in
the pack — no code changes (docs/CONTENT_PACK_SPEC.md).
"""
from __future__ import annotations

import hashlib
import hmac
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Bookmark,
    Card,
    ExampleSentence,
    GrammarTopic,
    InflectionForm,
    InstalledPack,
    Language,
    Lexeme,
    LexemeRelation,
    Scenario,
    Text,
)
from app.services.content_import import ImportReport, validate_text_dataset
from app.services.morphology import STRESS, VOWELS, strip_stress

PACK_FORMAT = 1


def _canonical(content: dict) -> bytes:
    return json.dumps(content, ensure_ascii=False, sort_keys=True).encode()


def checksum(content: dict) -> str:
    return hashlib.sha256(_canonical(content)).hexdigest()


def sign(content_checksum: str, key: str) -> str:
    return hmac.new(key.encode(), content_checksum.encode(), hashlib.sha256).hexdigest()


def build_pack(
    db: Session, name: str, version: str, language: str = "ru",
    signing_key: str | None = None,
) -> dict:
    """Export the current content database as an installable pack."""
    lang = db.scalar(select(Language).where(Language.code == language))
    if lang is None:
        raise ValueError(f"language '{language}' not found")

    vocabulary = []
    for lexeme in db.scalars(select(Lexeme).where(Lexeme.language_id == lang.id)):
        examples = [
            [e.text, e.translation]
            for e in db.scalars(
                select(ExampleSentence).where(ExampleSentence.lexeme_id == lexeme.id)
            )
        ]
        relations = [
            [r.relation_type, r.target_lemma, r.note]
            for r in db.scalars(
                select(LexemeRelation).where(LexemeRelation.lexeme_id == lexeme.id)
            )
        ]
        entry = {
            column.name: getattr(lexeme, column.name)
            for column in Lexeme.__table__.columns
            if column.name not in ("id", "language_id")
        }
        entry["examples"] = examples
        entry["relations"] = relations
        vocabulary.append(entry)

    texts = [
        {
            "slug": t.slug, "title": t.title,
            "title_translation": t.title_translation, "kind": t.kind,
            "cefr_level": t.cefr_level, "topic": t.topic,
            "summary": t.summary, "sentences": t.sentences,
        }
        for t in db.scalars(select(Text).where(Text.language_id == lang.id))
    ]
    grammar_topics = [
        {
            "slug": g.slug, "title": g.title, "title_native": g.title_native,
            "cefr_level": g.cefr_level, "order_index": g.order_index,
            "summary": g.summary, "content": g.content, "drills": g.drills,
            "prerequisites": g.prerequisites,
        }
        for g in db.scalars(
            select(GrammarTopic).where(GrammarTopic.language_id == lang.id)
        )
    ]
    scenarios = [
        {
            "slug": s.slug, "title": s.title, "persona": s.persona,
            "setting": s.setting, "cefr_level": s.cefr_level,
            "description": s.description, "persona_prompt": s.persona_prompt,
            "script": s.script, "key_vocabulary": s.key_vocabulary,
            "goals": s.goals, "grammar_focus": s.grammar_focus,
        }
        for s in db.scalars(select(Scenario).where(Scenario.language_id == lang.id))
    ]

    content = {
        "language_meta": {
            "code": lang.code, "name_english": lang.name_english,
            "name_native": lang.name_native, "script": lang.script,
            "metadata_json": lang.metadata_json,
        },
        "vocabulary": vocabulary,
        "texts": texts,
        "grammar_topics": grammar_topics,
        "scenarios": scenarios,
    }
    digest = checksum(content)
    manifest = {
        "name": name, "version": version, "format": PACK_FORMAT,
        "language": language,
        "counts": {
            "vocabulary": len(vocabulary), "texts": len(texts),
            "grammar_topics": len(grammar_topics), "scenarios": len(scenarios),
        },
        "checksum": digest,
    }
    key = signing_key or get_settings().pack_key
    if key:
        manifest["signature"] = sign(digest, key)
    return {"manifest": manifest, "content": content}


def _validate_full_vocabulary(entries: list, db: Session) -> ImportReport:
    """Validation for the full-entry vocabulary format packs carry
    (superset of the compact importer's checks)."""
    report = ImportReport()
    existing = set(db.scalars(select(Lexeme.lemma)))
    seen: set[str] = set()
    required = ("lemma", "stressed", "ipa", "transliteration",
                "part_of_speech", "cefr_level", "translation")
    for index, entry in enumerate(entries):
        where = f"vocab {index} «{entry.get('lemma', '?')}»"
        missing = [k for k in required if not entry.get(k)]
        if missing:
            report.errors.append(f"{where}: missing {missing}")
            continue
        syllables = sum(1 for ch in strip_stress(entry["stressed"]).lower()
                        if ch in VOWELS)
        if syllables >= 2 and STRESS not in entry["stressed"] \
                and "ё" not in entry["stressed"].lower():
            report.errors.append(f"{where}: missing stress mark")
            continue
        if entry["lemma"] in seen:
            report.errors.append(f"{where}: duplicate within pack")
            continue
        seen.add(entry["lemma"])
        if entry["lemma"] in existing:
            report.warnings.append(f"{where}: already installed — skipped")
            continue
        report.valid_items.append(entry)
    return report


def validate_pack(
    pack: dict, db: Session, signing_key: str | None = None
) -> ImportReport:
    report = ImportReport()
    manifest = pack.get("manifest") or {}
    content = pack.get("content") or {}

    for field in ("name", "version", "format", "language", "checksum"):
        if field not in manifest:
            report.errors.append(f"manifest: missing '{field}'")
    if report.errors:
        return report
    if manifest["format"] != PACK_FORMAT:
        report.errors.append(
            f"manifest: format {manifest['format']} unsupported (expected {PACK_FORMAT})"
        )
        return report
    if checksum(content) != manifest["checksum"]:
        report.errors.append("integrity: content checksum mismatch — pack corrupted")
        return report

    key = signing_key or get_settings().pack_key
    if manifest.get("signature"):
        if not key:
            report.errors.append("signature present but no pack key configured")
            return report
        if not hmac.compare_digest(sign(manifest["checksum"], key),
                                   manifest["signature"]):
            report.errors.append("signature: verification FAILED — do not install")
            return report
    else:
        report.warnings.append("pack is unsigned — install only from trusted sources")

    existing = db.scalar(
        select(InstalledPack).where(InstalledPack.name == manifest["name"])
    )
    if existing and existing.version >= manifest["version"]:
        report.errors.append(
            f"'{manifest['name']}' {existing.version} already installed — "
            f"pack is {manifest['version']} (not newer)"
        )
        return report

    vocab_report = _validate_full_vocabulary(content.get("vocabulary", []), db)
    text_report = validate_text_dataset(content.get("texts", []), db)
    report.errors += vocab_report.errors + text_report.errors
    report.warnings += vocab_report.warnings + text_report.warnings

    existing_grammar = set(db.scalars(select(GrammarTopic.slug)))
    grammar_new = [g for g in content.get("grammar_topics", [])
                   if g.get("slug") and g["slug"] not in existing_grammar]
    existing_scenarios = set(db.scalars(select(Scenario.slug)))
    scenario_new = [s for s in content.get("scenarios", [])
                    if s.get("slug") and s["slug"] not in existing_scenarios]

    if report.errors:
        return report
    report.valid_items = [{
        "manifest": manifest,
        "vocabulary": vocab_report.valid_items,
        "texts": text_report.valid_items,
        "grammar_topics": grammar_new,
        "scenarios": scenario_new,
    }]
    return report


def install_pack(db: Session, pack: dict, signing_key: str | None = None) -> InstalledPack:
    report = validate_pack(pack, db, signing_key)
    if not report.ok:
        raise ValueError("; ".join(report.errors))
    payload = report.valid_items[0]
    manifest = payload["manifest"]

    language = db.scalar(
        select(Language).where(Language.code == manifest["language"])
    )
    if language is None:
        meta = pack["content"].get("language_meta") or {}
        language = Language(
            code=manifest["language"],
            name_english=meta.get("name_english", manifest["language"]),
            name_native=meta.get("name_native", manifest["language"]),
            script=meta.get("script", "unknown"),
            metadata_json=meta.get("metadata_json", {}),
        )
        db.add(language)
        db.flush()

    row_ids: dict[str, list[int]] = {"lexemes": [], "texts": [],
                                     "grammar_topics": [], "scenarios": []}
    for entry in payload["vocabulary"]:
        entry = dict(entry)
        examples = entry.pop("examples", [])
        relations = entry.pop("relations", [])
        lexeme = Lexeme(language_id=language.id, **entry)
        db.add(lexeme)
        db.flush()
        row_ids["lexemes"].append(lexeme.id)
        for text, translation in examples:
            db.add(ExampleSentence(lexeme_id=lexeme.id, text=text,
                                   translation=translation))
        for relation_type, target, note in relations:
            db.add(LexemeRelation(lexeme_id=lexeme.id, relation_type=relation_type,
                                  target_lemma=target, note=note))
        seen_forms = {lexeme.lemma}
        for table_name, forms in (lexeme.inflections or {}).items():
            if not isinstance(forms, dict):
                continue
            for slot, form in forms.items():
                plain = strip_stress(str(form)).lower()
                if plain and plain not in seen_forms:
                    seen_forms.add(plain)
                    db.add(InflectionForm(lexeme_id=lexeme.id, form=plain,
                                          table_name=table_name, slot=str(slot)))

    for item in payload["texts"]:
        word_count = sum(len(s["ru"].split()) for s in item["sentences"])
        text = Text(language_id=language.id, word_count=word_count, **item)
        db.add(text)
        db.flush()
        row_ids["texts"].append(text.id)

    for topic in payload["grammar_topics"]:
        row = GrammarTopic(language_id=language.id, **topic)
        db.add(row)
        db.flush()
        row_ids["grammar_topics"].append(row.id)

    for scenario in payload["scenarios"]:
        row = Scenario(language_id=language.id, **scenario)
        db.add(row)
        db.flush()
        row_ids["scenarios"].append(row.id)

    record = db.scalar(
        select(InstalledPack).where(InstalledPack.name == manifest["name"])
    )
    if record:
        # Incremental upgrade: merge new row ids into the provenance record.
        merged = {k: sorted(set(record.row_ids.get(k, [])) | set(v))
                  for k, v in row_ids.items()}
        record.row_ids = merged
        record.version = manifest["version"]
        record.checksum = manifest["checksum"]
        record.signed = bool(manifest.get("signature"))
    else:
        record = InstalledPack(
            name=manifest["name"], version=manifest["version"],
            language=manifest["language"], checksum=manifest["checksum"],
            signed=bool(manifest.get("signature")), row_ids=row_ids,
        )
        db.add(record)
    db.commit()
    return record


def rollback_pack(db: Session, name: str, force: bool = False) -> dict:
    """Remove everything a pack installed. Refuses (without force) when
    learner SRS cards reference the pack's lexemes — progress is sacred."""
    record = db.scalar(select(InstalledPack).where(InstalledPack.name == name))
    if record is None:
        raise LookupError(f"pack '{name}' is not installed")

    lexeme_ids = record.row_ids.get("lexemes", [])
    cards_on_pack = 0
    if lexeme_ids:
        cards_on_pack = len(list(db.scalars(
            select(Card.id).where(Card.lexeme_id.in_(lexeme_ids))
        )))
    if cards_on_pack and not force:
        raise ValueError(
            f"{cards_on_pack} SRS cards reference this pack's vocabulary; "
            "pass force=True to delete them along with the content"
        )

    removed = {"lexemes": 0, "texts": 0, "grammar_topics": 0, "scenarios": 0,
               "cards": 0}
    if lexeme_ids:
        if cards_on_pack:
            for card in db.scalars(select(Card).where(Card.lexeme_id.in_(lexeme_ids))):
                db.delete(card)
                removed["cards"] += 1
        for model in (ExampleSentence, LexemeRelation, InflectionForm):
            for row in db.scalars(select(model).where(model.lexeme_id.in_(lexeme_ids))):
                db.delete(row)
        for lexeme in db.scalars(select(Lexeme).where(Lexeme.id.in_(lexeme_ids))):
            db.delete(lexeme)
            removed["lexemes"] += 1
    text_ids = record.row_ids.get("texts", [])
    if text_ids:
        for bookmark in db.scalars(select(Bookmark).where(Bookmark.text_id.in_(text_ids))):
            db.delete(bookmark)
        for text in db.scalars(select(Text).where(Text.id.in_(text_ids))):
            db.delete(text)
            removed["texts"] += 1
    for key, model in (("grammar_topics", GrammarTopic), ("scenarios", Scenario)):
        ids = record.row_ids.get(key, [])
        if ids:
            for row in db.scalars(select(model).where(model.id.in_(ids))):
                db.delete(row)
                removed[key] += 1

    db.delete(record)
    db.commit()
    return removed
