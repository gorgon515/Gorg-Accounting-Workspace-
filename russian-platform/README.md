# Русский Институт · Russian Language Institute

An AI-powered Russian language learning platform designed to take a learner
from zero knowledge to CEFR C2 without outside resources — combining the
strengths of SRS systems (Anki/FSRS), structured courses (Assimil/Babbel),
comprehensible input (LingQ/Refold), speaking practice (Pimsleur/iTalki),
and AI conversation partners.

**Status: 1.0 — production release.** Four phases complete; see
[docs/PHASE_4_REPORT.md](docs/PHASE_4_REPORT.md) for the final
acceptance-criteria evidence and production-readiness checklist, and
[docs/FINAL_ARCHITECTURE.md](docs/FINAL_ARCHITECTURE.md) for the finished
shape. From here on: content packs and maintenance.

**Headline numbers**: 320 lessons · 16 courses · 6 tracks · 663 dictionary
entries + 5,300 indexed inflected forms · 40 grammar topics A0→C2 · CEFR
exams with certificates · 12 conversation scenarios · offline-first PWA
with local-AI support (llama.cpp/Ollama) · signed content packs with
rollback · encrypted account backups · 200 backend tests at 95% coverage ·
every endpoint under 30 ms median.

## What works today

- **593-entry vocabulary database**: hand-curated core + a compact curated
  wordlist expanded by a rule-based **morphology engine** (transliteration,
  approximate IPA, declension, conjugation, irregular overrides). Every
  entry: stress marks, morphology tables, topic, difficulty, register,
  usage/cultural/etymology notes.
- **Complete grammar curriculum**: 40 interactive topics A0→C2 with
  explanations, auto-graded drills, mastery tracking, and a
  prerequisite-based readiness graph.
- **55 lessons across 4 courses** with strict mastery gating: curated A0/A1
  courses plus data-driven A2/B1 courses generated from the wordlist
  (bidirectional translation exercises, grammar checkpoints).
- **Intelligent SRS**: FSRS-style memory model + adaptive target retention
  from the learner's accuracy, review load balancing across days, and a
  due-forecast chart.
- **Reading/listening library**: 8 graded texts (stories, dialogues, a
  fairy tale, news) with clickable dictionary words, one-tap SRS
  enrollment, sentence TTS with speed control, loop, shadowing, and graded
  dictation modes, and persistent bookmarks.
- **AI tutor & conversation partner**: 4 scripted scenarios offline; with
  an Anthropic key, a full tutor with 6 modes (Socratic, storytelling,
  debate, ...), personality settings, and persistent learner-profile
  memory that targets weak words and grammar. Offline, the tutor still
  produces personalized practice plans.
- **Pronunciation & dictation scoring**: word-alignment feedback (browser
  Web Speech / Whisper-service pluggable).
- **Deep analytics**: CEFR estimate, retention prediction, activity
  heatmap, learning velocity, per-skill strengths, fluency-date projection.
- **Gamification**: XP, levels, streaks, daily quests with claimable
  rewards, achievement collection with rarity tiers.
- **Immersion & accessibility**: UI transitions to Russian at 25/50/75/100%
  presets; font scaling, high contrast, dyslexia-friendly font, reduced
  motion, keyboard-visible focus.

## Quickstart

Backend (Python 3.11+):

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload      # http://localhost:8000, docs at /docs
pytest --cov=app                    # 119 tests, 94% coverage
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
