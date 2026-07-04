# Development Roadmap

The platform is built in phases; each phase ships a coherent, tested,
usable increment. Phase 1 is complete (see PHASE_1_REPORT.md).

## Phase 1 — Foundation (✅ complete)
Core architecture, auth, language-agnostic data model, FSRS-style SRS,
A0+A1 courses with mastery gating, 12 interactive grammar topics +
36-topic curriculum catalog, 95-entry curated vocabulary with full
morphology, offline conversation partner with 4 scenarios, transcript-based
pronunciation scoring, analytics dashboard, gamification, immersion-aware
UI strings, CI.

## Phase 2 — Content scale-up (✅ complete, see PHASE_2_REPORT.md)
- **Bulk vocabulary import pipeline**: frequency-list driven importer
  (OpenCorpora/Sharoff lists + Wiktionary dumps) targeting top-3k, then
  top-10k lemmas, with human review queue; domain packs (business, medical,
  legal, tech, finance, slang/profanity properly flagged by register).
- **Grammar content sprints**: full interactive content + drills for the
  24 catalog topics (dative → punctuation), sentence diagrams as data.
- **Courses A2–B1** (12–16 lessons each) with dictation blocks.
- **Audio pipeline**: batch TTS (male/female/slow) into object storage,
  populating `lexemes.audio` and `example_sentences.audio_url`; licensed
  native recordings where quality matters most (alphabet, top-1k).
- **Alembic migrations** replace `create_all` for schema evolution.
- **Redis** for review-queue caching and rate limiting.

## Phase 3 — Platform completion (✅ complete, see PHASE_3_REPORT.md)
Curriculum engine v2 (320 lessons / 11 generated families, prerequisite
course gating), bulk import pipelines with validation CLIs, CEFR exam
system with placement and certificates, 12 conversation scenarios with
session reports, Dictionary 2.0 (inflected-form index, wildcards,
families), writing coach with real offline analysis, error-intelligence
reports, pronunciation practice queue, offline PWA with review-write sync,
Exams/Writing/Progress UIs, karaoke reader with A/B repeat and speed
memory, 95% backend coverage, sub-150ms endpoints.

## Phase 4 — Listening & speech depth
- Self-hosted **Whisper service** wired to `WhisperSTTProvider`; serverside
  STT replaces/augments browser recognition.
- **Acoustic pronunciation engine**: forced alignment (MFA) for
  phoneme-level scoring, stress-placement detection, waveform/spectrogram
  comparison UI, mouth/tongue placement diagrams per phoneme.
- **Listening library**: graded podcasts/dialogues with clickable
  transcripts (LingQ-style word lookup → SRS enrollment), shadowing mode,
  loop/AB-repeat, adjustable speed.
- **Per-user memory-model fitting**: re-fit stability growth parameters
  from each learner's `review_logs` (the data is already collected).

## Phase 5 — Generative immersion
- Streaming voice conversations (interruptible, emotional TTS) over the
  LLM provider layer; scenario difficulty auto-adaptation from
  conversation memory.
- Unlimited personalized content: stories, news-style articles, quizzes,
  crosswords, roleplay scripts generated at the learner's exact level from
  their known-word inventory (the `/practice/story` endpoint already
  defines this contract).
- Full **Russian interface mode**: extend the immersion string system to
  all content chrome, with per-learner gradual transition.
- Writing tutor with inline corrections and error-pattern tracking feeding
  `grammar_mastery`.

## Phase 6 — B2→C2 and community
- Courses B2, C1, C2 (academic/business tracks, style & register work).
- Boss exams per level; mock TORFL (ТРКИ) test simulations.
- Skill trees, seasonal events, leaderboards.
- Offline mode (PWA + local queue sync), cloud sync conflict resolution.
- Second language pilot (validates the language-agnostic core end-to-end).

## Ongoing engineering tracks
- Testing: keep every module covered; add load tests before Phase 4.
- Observability: structured logging → OpenTelemetry traces + dashboards.
- Backups: automated Postgres snapshots + content-pack versioning.
