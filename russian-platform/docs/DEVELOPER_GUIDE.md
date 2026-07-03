# Developer Guide

## Setup

```bash
# Backend (Python 3.11+)
cd backend && pip install -e ".[dev]"
uvicorn app.main:app --reload        # http://localhost:8000/docs

# Frontend (Node 20+)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

SQLite is created and seeded on startup. `RLP_*` env vars override
config (`app/core/config.py`); `.env` files are honored.

## Code map

| Layer | Where | Rules |
|---|---|---|
| Config | `app/core/config.py` | All tunables env-overridable, prefix `RLP_` |
| Models | `app/models/` | Typed SQLAlchemy 2.0; content keyed by `language_id`; JSON for per-POS shapes |
| Services | `app/services/` | Pure logic, no FastAPI imports; providers behind ABCs |
| Routes | `app/api/routes/` | Thin: validate → call services → serialize; answer keys never serialized |
| Seed | `app/seed/` | Data only; idempotent by slug/lemma via `runner.seed_all` |
| Frontend | `frontend/src/` | Pages lazy-loaded; shared logic in `lib/`; typed client in `api/client.ts` |

## Conventions
- Answer comparison always via `text_utils.answer_matches` (ё-folding,
  case, whitespace).
- Timestamps stored naive-UTC in SQLite; always pass through
  `text_utils.ensure_utc` before arithmetic.
- Every learner interaction appends a `LearningEvent` — quests, heatmap,
  and skill scores derive from the stream; do not add parallel counters.
- New AI features must work offline: check `provider.is_generative` and
  ship a deterministic fallback (see tutor/conversation for the pattern).
- XP grants go through `gamification.award_xp` + `touch_streak`, then
  `evaluate_achievements`.

## Testing

```bash
cd backend && pytest --cov=app       # 119 tests, 94% coverage
cd frontend && npm test && npm run build
```

- API tests use the in-memory session fixture (`tests/conftest.py`) with
  the dependency override; seeding runs per test.
- Generative paths are tested with `StubProvider`
  (`tests/test_llm_paths.py`) — never hit the network in tests.
- Morphology changes require dictionary-verified expected forms
  (`tests/test_morphology.py`).

## Adding a language (the point of the architecture)
1. Seed a `Language` row with alphabet metadata.
2. Provide content: wordlist (+ a morphology module if you want generated
   inflections), grammar topics, courses, scenarios, texts.
3. No route/service/schema changes should be necessary. If one is, that's
   a bug in the abstraction — fix the abstraction.
