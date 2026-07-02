# Русский Институт · Russian Language Institute

An AI-powered Russian language learning platform designed to take a learner
from zero knowledge to CEFR C2 without outside resources — combining the
strengths of SRS systems (Anki/FSRS), structured courses (Assimil/Babbel),
comprehensible input (LingQ/Refold), speaking practice (Pimsleur/iTalki),
and AI conversation partners.

**Status: Phase 1 complete** — see [docs/PHASE_1_REPORT.md](docs/PHASE_1_REPORT.md)
and the multi-year plan in [docs/ROADMAP.md](docs/ROADMAP.md).

## What works today

- **Cyrillic → first conversations**: two full courses (A0 Foundations,
  A1 Survival Russian) with strict mastery gating — lessons unlock only
  after passing the previous mastery test.
- **Rich vocabulary database**: 95 hand-curated core entries, each with
  stress marks, IPA, transliteration, frequency rank, morphology
  (declensions/conjugations/aspect pairs), register, mnemonics, example
  sentences, common-mistake warnings, and cultural notes.
- **Grammar encyclopedia**: full A0→C1 curriculum catalog (36 topics) with
  12 fully interactive topics (explanations + auto-graded drills) and
  per-topic mastery tracking.
- **Adaptive SRS**: FSRS-style two-component memory model (stability +
  difficulty + retrievability), forgetting-curve prediction, target-retention
  scheduling. Lesson vocabulary auto-enrolls into the review queue.
- **AI conversation partner**: 4 scripted roleplay scenarios (café, taxi,
  hotel, meeting someone) that work fully offline; plugging in an Anthropic
  API key upgrades the partner to free-form LLM roleplay with corrections.
  Browser speech recognition + synthesis for voice conversations.
- **Pronunciation feedback**: transcript-based scoring with per-word
  verdicts (browser Web Speech / Whisper-service pluggable).
- **Analytics dashboard**: CEFR estimate, known words, predicted retention,
  review accuracy, weak grammar topics, study time, achievements.
- **Gamification**: XP, levels, streaks, 10 achievements.
- **Immersion mode foundation**: every UI string exists in EN+RU and flips
  to Russian progressively as the learner's immersion ratio rises.

## Quickstart

Backend (Python 3.11+):

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload      # http://localhost:8000, docs at /docs
pytest                              # 56 tests
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxies /api)
npm test && npm run build
```

The database (SQLite by default) is created and seeded automatically on
first startup. For PostgreSQL: `export RLP_DATABASE_URL=postgresql+psycopg://...`.

To enable generative AI features (free-form conversation, story generation,
writing feedback):

```bash
export RLP_LLM_PROVIDER=anthropic
export RLP_ANTHROPIC_API_KEY=sk-ant-...
```

## Repository layout

```
russian-platform/
├── backend/            FastAPI + SQLAlchemy 2.0
│   ├── app/core/       config, database, security
│   ├── app/models/     language-agnostic ORM schema
│   ├── app/services/   SRS engine, CEFR estimator, conversation engine,
│   │                   LLM/STT/TTS abstractions, content generation
│   ├── app/api/routes/ auth, vocabulary, grammar, lessons, reviews,
│   │                   conversation, practice, analytics
│   ├── app/seed/       the built-in Russian content database
│   └── tests/          pytest suite
├── frontend/           React 18 + TypeScript + Tailwind (Vite)
└── docs/               architecture, data model, roadmap, phase reports
```

## Design principles

1. **Language-agnostic core** — every content table is keyed by language;
   adding a language means adding seed content, not code (docs/DATA_MODEL.md).
2. **Offline-first AI** — every AI feature has a deterministic fallback so
   the platform is fully usable (and CI-testable) without network or keys.
3. **Mastery gating** — progress is earned, not scrolled past.
4. **Everything is an event** — all interactions land in an append-only
   event stream that feeds the adaptive algorithms and analytics.
