# Phase 2 Report — Production Polish & Completion

## 1. Code audit findings & fixes

| Finding | Fix |
|---|---|
| `list_courses` issued O(n²) queries via per-lesson `is_lesson_unlocked` | `compute_unlock_map` computes all unlock states in 2 queries (`lesson_gate.py`) |
| Answer normalization duplicated in lesson grading + grammar drills | Shared `text_utils.normalize_answer` / `answer_matches` |
| Timezone-coercion logic duplicated in reviews + analytics | Shared `text_utils.ensure_utc` |
| `speak()` duplicated in 5 frontend pages; ad-hoc speech recognition | Shared `lib/speech.ts` (synthesis, async playback, one-shot recognition) |
| Achievement serialization duplicated in 2 routes | `gamification.serialize_achievements` (now with rarity) |
| `level_for_xp` / `xp_progress` duplicated the level-curve loop | `level_for_xp` delegates |
| Inline imports in `practice.py`, dead `datetime` import in `grammar.py` | Hoisted/removed |
| Default JWT secret usable silently in production | Startup warning when secret is default/short and debug is off |
| passlib abandoned upstream (Phase 1 note) | Already replaced with direct bcrypt in Phase 1; verified |
| Frontend loaded every page in one bundle | Route-level `React.lazy` code splitting (main bundle 202 kB → 181 kB with 10 lazy chunks) |

## 2. New features

**Morphology engine** (`services/morphology.py`, 96% covered)
- Rule-based transliteration, approximate IPA (palatalization, vowel
  reduction, final devoicing, stress placement), noun declension
  (all regular paradigms + 7-letter spelling rule + animacy), adjective
  declension, verb conjugation (both conjugations, -овать/-евать, husher
  rules, reflexives, per-form irregular overrides).

**Vocabulary expansion** — 112 → **593 entries**
- `services/vocab_factory.py` expands a compact curated wordlist
  (`seed/wordlist.py`, 481 entries across 18 topics) into full dictionary
  entries: morphology tables, IPA, transliteration, difficulty score,
  topic, register, etymology/cultural notes, mobile-stress and
  consonant-mutation overrides curated by hand.
- New indexed schema fields: `topic`, `difficulty`, `etymology`.

**Grammar curriculum complete** — 36 → **40 topics, 100% interactive**
- Full explanations + drills authored for all 24 former outline topics
  (dative → punctuation) and a new C2 tier (Aktionsart, stylistic syntax,
  phraseology, false friends).
- Prerequisite-based `ready` flag per topic (mastery ≥ 0.6 on all prereqs).

**Course catalog** — 12 → **55 lessons**
- `seed/course_builder.py` generates themed courses (A2 Everyday Life: 35
  lessons; B1 Wider World: 8) from the wordlist with bidirectional
  translation exercises and grammar checkpoints. Scales automatically as
  vocabulary grows.

**Intelligent SRS** (`services/srs_planner.py`)
- Adaptive target retention (0.85–0.95) from the learner's recent accuracy.
- Review load balancing: long intervals nudged ±1 day to the least-loaded
  day (spike/fatigue avoidance).
- 30/90-day due forecast endpoint + dashboard chart.

**Reading/listening library**
- `Text`/`Bookmark` models, 8 hand-authored graded texts (A1–B1: stories,
  dialogues, Репка, article, news) with sentence-aligned translations.
- Reader UI: clickable words with glossary popups and one-tap SRS
  enrollment (LingQ-style), sentence TTS with slow mode and speed slider,
  loop mode, shadowing mode (listen → speak → transcript), dictation mode
  with server-side word-alignment grading, persistent bookmarks.

**AI tutor** (`services/tutor.py`, 100% covered)
- Six modes (free/socratic/storytelling/debate/grammar-help/news), three
  personalities, system prompt built from the live learner profile (CEFR,
  weak grammar, shaky words) with an explicit guide-don't-tell rule.
- Offline practice plan endpoint: personalized speaking prompts, grammar
  targets, and writing prompts derived from actual weaknesses — the tutor
  is useful with zero LLM configuration.

**Gamification**
- 4 daily quests computed from the event stream, claim-once XP grants,
  achievement collection view with rarity tiers.

**Analytics** (`/analytics/trends`)
- 13-week activity heatmap, weekly learning velocity, per-skill scores
  with strongest/weakest detection, fluency projection (estimated date to
  B2 vocabulary at current velocity).

**Dictionary upgrades**
- Fuzzy search fallback (typo-tolerant, difflib-based), topic filter +
  topic listing, aspect-pair browser (`/vocabulary/verb-pairs`).

**Immersion & accessibility**
- Settings page: 0/25/50/75/100% immersion presets (per-string difficulty
  thresholds flip easier strings first), font scaling, high contrast,
  dyslexia-friendly font, reduced motion (+ `prefers-reduced-motion`),
  visible focus rings for keyboard navigation.
- `PATCH /auth/me` with key-merge preference storage.

## 3. Architectural changes
- All content generation remains data-driven and language-agnostic: the
  morphology engine is the only Russian-specific *code*, isolated in one
  module behind the factory.
- The event stream (`learning_events`) now powers quests, heatmap,
  velocity, and skill scores — no new counters were introduced.
- Provider abstraction extended to the tutor; generative wire format
  (`text --- translation ### corrections-json`) is now tested against a
  stub provider without network.

## 4. Test results
- Backend: **119 tests, 94% line coverage** (`pytest --cov=app`).
  Remaining uncovered lines: Anthropic HTTP client body, Whisper HTTP
  client, story-generation happy path — all require live network by design.
- Frontend: 6 unit tests (i18n immersion system, speech utils);
  TypeScript strict build clean; production build clean.
- The 95%/90% targets from the brief were approached but not fully met —
  see §6.

## 5. Remaining long-term roadmap
Unchanged phases 3–5 (docs/ROADMAP.md): real audio pipeline, acoustic
phoneme scoring, Whisper deployment, streaming voice, offline PWA sync
queue, B2–C2 courses, TORFL simulations, second language pilot.

## 6. Technical debt — deliberate deferrals
- **Vocabulary scale**: 593 curated entries vs the 6–8k target. Writing
  thousands of *correct* entries requires licensed frequency data and
  native review; shipping auto-generated unreviewed entries would poison
  the SRS with errors. The factory pipeline makes bulk import a data
  task, not a code task.
- **Lesson count**: 55 vs the 250–400 target — grows mechanically with the
  wordlist via the course builder.
- **Alembic**: still `create_all`; no deployed database exists yet, so
  migrations would version nothing. Must land before first production
  deployment (tracked since Phase 1).
- **Frontend component tests**: logic is unit-tested; Testing-Library
  coverage of page components deferred (jsdom setup + fixtures) — the
  90% frontend target is not met and is the first Phase 3 testing task.
- **Offline mode**: accessibility + caching-friendly API shapes shipped;
  service-worker sync queue deferred to the PWA work in Phase 3.
- **IPA/declension edge cases**: the morphology engine approximates; known
  limits (consonant assimilation clusters, mobile stress beyond curated
  overrides) documented in the module docstring.
