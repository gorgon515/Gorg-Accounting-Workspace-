# Phase 1 Report

## Completed features

**Backend (FastAPI + SQLAlchemy 2.0, 56 passing tests)**
- JWT auth (register/login/me), bcrypt password hashing.
- Language-agnostic content schema (see docs/DATA_MODEL.md); Russian seeded
  as the first language.
- Vocabulary API: search (RU/EN/translit), CEFR/POS/domain filters, full
  dictionary payloads (stress, IPA, morphology, mnemonics, examples,
  relations), alphabet + pronunciation-rules endpoint.
- Grammar encyclopedia: 36-topic A0→C1 curriculum catalog; 12 topics with
  full interactive content and server-graded drills; EMA mastery tracking
  that feeds the dashboard's weak-topics list.
- Course system: A0 (6 lessons) + A1 (6 lessons) with typed content blocks,
  server-side grading, strict sequential mastery gating, and automatic SRS
  enrollment of lesson vocabulary.
- SRS: FSRS-style stability/difficulty/retrievability model with
  target-retention scheduling, lapse handling, immutable review logs.
- Conversation engine: scripted dialogue trees (4 scenarios) fully
  functional offline with keyword matching, hints, and corrections;
  LLM path (Anthropic Messages API) activates via env config; session
  memory persists across conversations.
- Practice: adaptive vocabulary quiz + cloze drills built from the
  learner's weakest cards; transcript-based pronunciation scoring with
  per-word feedback; writing submissions (LLM feedback when configured).
- Analytics dashboard: CEFR estimate (vocab-size × grammar-mastery),
  predicted collection retention, 7-day review accuracy, weak grammar,
  study time, activity breakdown, achievements.
- Gamification: XP with triangular level curve, daily streaks, 10
  achievements evaluated against live metrics.

**Content database**
- Complete Cyrillic alphabet (33 letters: names, IPA, type, learner notes,
  example words) + 5 core pronunciation rules.
- 95 hand-curated A1 lexemes with full learner payloads (every field in
  the spec: stress, IPA, translit, frequency rank, register, domain,
  morphology incl. aspect pairs/declensions/conjugations/government,
  mnemonics, usage/cultural notes, common mistakes, examples, relations).
- 12 lessons, 4 conversation scenarios, 10 achievements.

**Frontend (React 18 + TS + Tailwind, builds clean, 4 unit tests)**
- Login/register, app shell with immersion-aware navigation.
- Dashboard, Lessons (+ lesson player with all block types), Review
  (SRS flashcards with 4-button grading), Vocabulary browser (+ full
  dictionary modal), Grammar (+ topic pages with drills), Conversation
  (chat UI with voice input/output via Web Speech API, hints,
  corrections), Alphabet explorer.
- Typed API client with auth handling; UI strings flip EN→RU progressively
  with the learner's immersion ratio (unit-tested).

**Infrastructure**
- GitHub Actions CI: backend pytest + frontend typecheck/test/build.
- Idempotent seeding on startup; SQLite dev / PostgreSQL prod via env.

## Architectural decisions
1. Language-agnostic core: content keyed by `language_id`; new languages
   are seed data, not code.
2. Offline-first AI: every AI feature has a deterministic fallback so the
   platform works and tests without network/keys (`LLMProvider.is_generative`).
3. FSRS-style memory model over SM-2 for real forgetting-curve prediction;
   full review logs retained for future per-user parameter fitting.
4. Answer keys stay server-side; the frontend renders typed content blocks.
5. Append-only `learning_events` stream feeds analytics and adaptivity.

## Tests written and passed
- 56 backend tests: SRS math (12: decay, spacing effect, difficulty
  damping, lapse behavior, bounds), auth (6), vocabulary (5), lessons &
  gating (7), reviews (5), conversation (5), grammar (5), practice &
  analytics (9), plus fixtures exercising seeding end-to-end.
- 4 frontend tests (immersion string system).
- Manual end-to-end smoke: server boot, seeding, register, Cyrillic
  search, course listing, conversation session.

## Remaining work
See docs/ROADMAP.md Phases 2–5. Biggest gaps vs. the full vision:
vocabulary scale (95 vs 10k+ — needs the bulk import pipeline), audio
assets (browser TTS only), acoustic pronunciation analysis, listening
library, streaming voice conversation, courses beyond A1.

## Technical debt
- `Base.metadata.create_all` on startup — replace with Alembic before any
  schema change ships (Phase 2, deliberate deferral).
- Grammar drill normalization accepts exact strings only (with ё/case
  normalization); fuzzy/declension-aware matching would reduce false
  negatives.
- The offline conversation engine's keyword matching is intentionally
  simple; the dialogue trees are the contract, matching quality improves
  with the LLM path.
- Frontend has unit tests only for pure logic; component tests (Testing
  Library) should land with Phase 2 UI growth.
- `python-jose`-style key length warning in tests (11-byte dev secret) —
  production requires a ≥32-byte `RLP_SECRET_KEY` (documented, not enforced).

## Suggested next phase
Phase 2 content scale-up, starting with the bulk vocabulary import
pipeline (frequency lists → staged import → review queue) and Alembic,
since both unblock every later phase.
