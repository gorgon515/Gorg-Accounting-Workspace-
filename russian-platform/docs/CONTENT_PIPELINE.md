# Content Pipeline Guide

How Russian content gets into the platform, and how to extend it.

## Bulk import (Phase 3 — the road to 6–8k words / 150+ texts)

```bash
cd backend
python -m tools.import_vocabulary dataset.json          # validate (dry run)
python -m tools.import_vocabulary dataset.json --apply  # validate + insert
python -m tools.import_texts texts.json --apply
```

**Vocabulary dataset** — JSON array of compact rows, identical semantics
to `seed/wordlist.py`:

```json
[
  ["огуре́ц", "n", "cucumber", "food", "A2",
   {"decl_overrides": {"gen_sg": "огурца́"},
    "examples": [["Я купи́л огурцы́.", "I bought cucumbers."]]}]
]
```

**Text dataset** — JSON array of objects, identical to `seed/library.py`
entries (slug/title/kind/cefr_level/summary/sentences[{ru,en}]).
Valid kinds: story, dialogue, fairy_tale, article, news, recipe, history,
science, culture, blog.

The validators (`app/services/content_import.py`) enforce every invariant
the curated seed obeys — stress marks, POS/CEFR vocabularies, gender for
-ь nouns, duplicate detection (in-file and against the DB), morphology
dry-run expansion, sentence completeness — and refuse the batch on any
error, so imported data is indistinguishable from first-party content to
the SRS, курс builder, dictionary, exams, and writing coach.

**Licensing note**: frequency-ranked wordlists and reader corpora are
typically licensed (e.g. Sharoff/Lyashevskaya-Sharov lists, publisher
graded readers). This pipeline is deliberately format-simple so licensed
or native-reviewed community data drops in without code changes. Do not
bulk-import machine-generated unreviewed entries — wrong stress or forms
poison the SRS.

## Vocabulary

Two tiers, one table:

1. **Curated core** (`seed/vocabulary_core.py`) — fully hand-written
   entries with examples, mnemonics, and mistake notes. Highest quality;
   used by the A0/A1 curated lessons.
2. **Wordlist expansion** (`seed/wordlist.py` → `services/vocab_factory.py`)
   — one compact line per word:

   ```python
   ("огуре́ц", "n", "cucumber", "food", "A2",
    {"decl_overrides": {"gen_sg": "огурца́", ...}})
   ```

   The factory generates transliteration, IPA, declension/conjugation
   tables, and difficulty via `services/morphology.py`.

### Authoring rules
- Stress marks are mandatory (combining U+0301) — они drive IPA and the
  learner-facing display.
- Check generated forms for **mobile stress** (рука́ → ру́ку) and
  **consonant mutations** (плати́ть → плачу́): supply `decl_overrides` /
  `conj_overrides` (per-form merge) or a full `inflections` dict.
- Nouns in -ь must specify `gender`. Animate nouns must set
  `animacy: "animate"` (accusative depends on it).
- No lemma may repeat across core + wordlist — the factory raises on
  duplicates, and a test enforces zero overlap.

## Grammar
Topics live in `seed/grammar_topics.py` (catalog + A0/A1 content) and
`seed/grammar_advanced.py` (A2–C2 content, merged at seed time). Each
topic: markdown sections (rendered by the frontend's minimal renderer:
`**bold**` and `| tables |`) + drills with `answer`/`accept` lists.
Prerequisites form the readiness graph — keep them acyclic.

## Courses
- Curated lessons: `seed/courses.py` (typed blocks: vocabulary, dialogue,
  reading, culture, exercise, mastery_test, grammar_ref).
- Generated lessons: `seed/course_builder.py` groups wordlist topics into
  lessons automatically. New topics/levels added to the wordlist appear
  in courses on next seed.

## Library texts
`seed/library.py`: sentence-aligned `{"ru", "en", "audio_url"}` lists.
Keep sentences ≤ ~14 words for the dictation mode. `audio_url` stays null
until the Phase 3 audio pipeline; the client uses TTS meanwhile.

## Seeding behavior
`seed/runner.py` is idempotent by slug/lemma and safe on every startup.
Grammar topics get a content *upgrade* in place when a previously
catalog-only topic gains content. Existing lexemes are never mutated —
bump content via new lemmas or a migration once Alembic lands.
