# Testing Guide

## Running

```bash
cd backend && pytest --cov=app          # 171 tests, 95% coverage
cd frontend && npm test                  # vitest unit tests
cd frontend && npm run build             # strict tsc + vite build
```

## Backend layout

| File | Covers |
|---|---|
| `test_srs_engine.py` | memory-model math (decay, spacing, difficulty, bounds) |
| `test_morphology.py` | translit/IPA/declension/conjugation vs dictionary forms |
| `test_auth.py`, `test_vocabulary.py`, `test_lessons.py`, `test_reviews.py`, `test_grammar.py`, `test_conversation.py`, `test_practice_and_analytics.py` | Phase 1 API surfaces |
| `test_phase2_features.py` | planner, library, tutor, quests, trends, dictionary, курс v2 checks |
| `test_phase3_features.py` | exams, session reports, dictionary 2.0, writing coach, error reports, pronunciation queue, gating v3 |
| `test_content_import.py` | dataset validators + apply paths |
| `test_llm_paths.py` | generative wire-format via StubProvider (no network) |
| `test_coverage_gaps.py` | content generation, provider selection, security edges, CLIs |

## Rules
1. **No network in tests.** Generative paths use `StubProvider`; STT/TTS
   are interfaces. If a test needs the internet, the design is wrong.
2. **Per-test in-memory DB** via the `db_session`/`client` fixtures
   (dependency override); seeding runs fresh each test, which also
   regression-tests the seed pipeline itself on every run.
3. **Morphology answers must be dictionary-verified** — cite the form you
   assert (mobile stress and mutations are where bugs hide).
4. **Answer keys never in API assertions** — tests that need keys import
   them from seed modules or rebuild exams via the seeded builder.
5. New features ship with tests in the same commit; coverage may not drop
   below 95% backend.

## Frontend
Unit tests target pure logic (`lib/i18n`, `lib/speech`, `lib/offline`)
under vitest's node environment. Component tests (Testing Library +
jsdom) are the next testing investment — see PHASE_3_REPORT limitations.
