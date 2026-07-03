# Content Pipeline Guide

How Russian content gets into the platform, and how to extend it.

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
