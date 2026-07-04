# Offline Engine

The platform is offline-first: after one online session, a learner can
study for extended periods with no connectivity.

## Layers

| Layer | Mechanism | What it covers |
|---|---|---|
| Static shell | Service worker cache-first (`public/sw.js`, `rli-static-v1`) | app HTML/JS/CSS (hashed filenames) |
| Content API | SW network-first with cache fallback (`rli-api-v1`) | lessons, dictionary, grammar, texts, scenarios, quests, forecasts, tutor plans |
| Prefetch | `src/lib/prefetch.ts` — after login, sequential warm-up of 14 core endpoints | guarantees the cache is populated *before* the connection drops |
| Writes | `src/lib/offline.ts` — durable localStorage queue for review ratings | replayed in order on `online` event / app start; stops at first failure to preserve ordering |
| Speech | Browser SpeechSynthesis/SpeechRecognition | fully local in modern browsers |
| AI | Local provider tier (docs/AI_PROVIDER_GUIDE.md) | tutor/conversation via llama.cpp on localhost, or deterministic offline tier |
| Cache versioning | cache names carry a version; `activate` deletes stale caches | clean upgrades |

## What works with zero connectivity
Reading cached lessons/grammar/texts/dictionary, SRS reviews (queued),
scripted conversation scenarios, offline tutor practice plans, writing
analysis via cached… no — writing analysis needs the API. Honest matrix:

| Fully offline | Needs the local server reachable |
|---|---|
| Reading cached content, TTS playback, review *rating* (queued), navigation, settings | grading (lessons/exams/dictation), writing analysis, search, new content |

The reference deployment for "laptop with no internet" is **backend +
frontend on the same machine** (see DEPLOYMENT_GUIDE): `localhost` is
always reachable, SQLite is the store, and the SW layers add resilience
for the browser-only/hosted deployment mode.

## Progress safety
1. Review writes are queued durably when the API is unreachable and
   replayed in order (`offline.test.ts` covers ordering, partial-failure
   retention, and corrupted-storage recovery).
2. Full account export/restore (`/account/export|import`) uses portable
   identifiers (lemmas/slugs) and stronger-side merge — restoring an old
   backup can never regress progress (tested).
3. Encrypted backups: PBKDF2-SHA256 (600k) → Fernet; wrong password fails
   loudly, never partially applies.

## Known limitations
- Browser localStorage is not encrypted at rest (encrypting it in JS with
  a key held in the same origin is theater); encrypted *backups* are the
  supported mechanism for data leaving the device.
- Resumable chunked downloads are unnecessary at current pack sizes
  (full DB ≈ a few MB of JSON); revisit when audio packs ship.
