# System Architecture

## Overview

The platform is a classic three-tier web application with an AI provider
abstraction layer, designed so that every intelligent feature degrades
gracefully to a deterministic offline implementation.

```
┌──────────────────────────────────────────────────────────┐
│  Frontend · React 18 + TypeScript + Tailwind (Vite)      │
│  Pages: Dashboard · Lessons · Review · Vocabulary ·      │
│         Grammar · Conversation · Alphabet                │
│  Browser APIs: SpeechSynthesis (TTS), SpeechRecognition  │
└──────────────────────┬───────────────────────────────────┘
                       │ REST /api/v1 (JWT bearer)
┌──────────────────────┴───────────────────────────────────┐
│  Backend · FastAPI                                        │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│  │ API routes  │→│ Services     │→│ Provider layer     │ │
│  │ auth        │ │ srs_engine   │ │ LLMProvider        │ │
│  │ vocabulary  │ │ cefr         │ │  · AnthropicProvider│ │
│  │ grammar     │ │ lesson_gate  │ │  · OfflineProvider │ │
│  │ lessons     │ │ conversation │ │ STTProvider        │ │
│  │ reviews     │ │ content_gen  │ │  · WhisperSTT      │ │
│  │ conversation│ │ gamification │ │ TTSProvider        │ │
│  │ practice    │ │ speech       │ │                    │ │
│  │ analytics   │ └──────────────┘ └────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │ SQLAlchemy 2.0
┌──────────────────────┴───────────────────────────────────┐
│  SQLite (dev) / PostgreSQL (prod) — same code path        │
│  Redis (optional, session/queue caching — Phase 2)        │
└──────────────────────────────────────────────────────────┘
```

## Key architectural decisions

### 1. Language-agnostic schema
Every content table (`lexemes`, `grammar_topics`, `courses`, `scenarios`)
carries a `language_id` FK. Alphabets and phonology live on
`languages.metadata_json`. Adding Spanish later = inserting a row + seed
content. No schema migration, no code change in services or routes.

### 2. Provider abstraction for all AI
`services/llm.py` defines `LLMProvider` with two implementations:
- `AnthropicProvider` — Messages API, used when a key is configured.
- `OfflineProvider` — reports `is_generative = False`; feature code then
  routes to deterministic behavior (scripted dialogue trees, template-based
  quizzes/cloze from the seeded DB).

This keeps the entire platform functional and CI-testable with zero network
access, and makes swapping/adding providers a one-file change. STT/TTS
follow the same pattern (`services/speech.py`); in Phase 1 the browser's
Web Speech API does recognition/synthesis client-side, with a
`WhisperSTTProvider` ready for a self-hosted service.

### 3. FSRS-style memory model, not SM-2
`services/srs_engine.py` models each card as (stability, difficulty) with
retrievability `R(t) = exp(ln(0.9)·t/S)`. Scheduling solves for the
interval where R equals the target retention (default 0.9). This gives:
- true forgetting-curve prediction (dashboard shows collection retention),
- the spacing effect (late reviews grow stability more),
- graceful lapses (relearning is faster than initial learning).
Every review is appended to `review_logs`, so parameters can later be
fitted per-user (Phase 3) without losing history.

### 4. Content as data, graded server-side
Lessons and grammar topics store their exercise answer keys in the DB;
API responses strip answers, and grading happens server-side
(`lesson_gate.grade_mastery_test`, grammar drill endpoint). The frontend is
a pure renderer of typed content blocks (`vocabulary`, `dialogue`,
`reading`, `exercise`, `mastery_test`, `culture`, `grammar_ref`), so new
block types extend the enum without breaking old clients.

### 5. Event sourcing for analytics
Every interaction writes a `LearningEvent`. The analytics dashboard and
CEFR estimator are pure queries over this stream plus the SRS/mastery
state — no separate counters to keep in sync.

### 6. Mastery gating
`lesson_gate.is_lesson_unlocked` enforces strict sequential unlocking
within a course and across courses. The CEFR estimator
(`services/cefr.py`) combines known-word counts (vocabulary-size research
thresholds) with grammar mastery so neither can inflate the estimate alone.

## Security
- Passwords: bcrypt (direct, not passlib — see PHASE_1_REPORT).
- Auth: JWT bearer tokens (HS256), 7-day expiry, OAuth2 password flow.
- All content endpoints require auth; per-user resources check ownership.
- Answer keys never leave the server.

## Scaling path (see ROADMAP)
- SQLite → PostgreSQL is a config change (`RLP_DATABASE_URL`).
- Redis for review-queue caching and rate limiting.
- Audio/media in object storage, referenced by `lexemes.audio` URLs.
- Vector DB (pgvector) for semantic search over transcripts in Phase 3.
