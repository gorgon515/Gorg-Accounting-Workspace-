# Final Architecture (1.0)

The four-phase evolution is documented in the phase reports; this is the
finished shape. Details: ARCHITECTURE.md (diagrams, decisions 1–8),
DATA_MODEL.md (ER diagram), and the per-system guides.

## The five load-bearing decisions

1. **Language-agnostic core, content as data.** Every content table keys
   on `language_id`; the only Russian-specific code is
   `services/morphology.py`, consumed as data via `vocab_factory`. New
   languages arrive as content packs (CONTENT_PACK_SPEC.md).
2. **Provider abstraction with a deterministic floor.** LLM/STT/TTS sit
   behind interfaces with four tiers (local server / in-process GGUF /
   cloud / deterministic offline). Features check `is_generative` and
   always have a working fallback — the whole platform runs and tests
   with zero network (AI_PROVIDER_GUIDE.md).
3. **One memory model, one grading path, one event stream.** FSRS-style
   scheduling in `srs_engine` (pure math) + `srs_planner` (DB-aware
   heuristics); all answer checking through `text_utils.answer_matches`;
   every interaction appends a `LearningEvent` that feeds quests,
   analytics, error intelligence, and the CEFR estimator.
4. **Generated curriculum.** 320 lessons are compiled from the content DB
   by `seed/course_builder.py` (11 lesson families) — lesson count scales
   with content, and every exercise's answer traces to a verified source.
   Exams are pure functions of (level, seed): rebuilt at grading time,
   keys never stored or shipped.
5. **Offline-first with progress safety.** Service-worker caching +
   post-login prefetch + a durable ordered write queue + portable
   merge-only backups (OFFLINE_ENGINE.md). Rollback and restore paths are
   designed so user progress cannot be silently lost.

## Component map

```
backend/app
├── core/          config (env-driven), db session, JWT+bcrypt
├── models/        18 tables (see DATA_MODEL.md ER diagram)
├── services/      pure logic: morphology, vocab_factory, srs_engine,
│                  srs_planner, cefr, lesson_gate, conversation_engine,
│                  tutor, content_gen, writing_coach, exams, search,
│                  content_import, content_packs, account_backup,
│                  llm/speech providers, gamification, text_utils
├── api/routes/    13 thin routers (validate → service → serialize)
└── seed/          Russian content + course_builder (idempotent)
backend/tools/     import_vocabulary, import_texts, pack, benchmark
frontend/src
├── api/client.ts  typed fetch + offline queueing
├── lib/           i18n (immersion), speech, offline, prefetch
└── pages/         15 lazy-loaded routes
```

## Numbers at 1.0
663 lexemes (+5,300 indexed forms) · 320 lessons / 16 courses / 6 tracks ·
40 grammar topics A0–C2 · 12 scenarios · 8 texts · 6 CEFR exams + placement ·
200 backend tests (95% cov) · 16 frontend tests · all endpoints < 30 ms
median (tools/benchmark.py).
