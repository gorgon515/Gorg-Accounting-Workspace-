# ARIA — Integrated Desktop Assistant

A voice-driven desktop assistant for **stocks, accounting, studying, and
productivity**, built as an Electron app with a pluggable skill architecture and
a Claude brain. This repository contains the **first working vertical slice:
Stocks**, with voice enabled from day one.

> Scope note: a "tops any Jarvis" assistant is a platform, not a weekend build.
> This is the foundation done properly — a real, runnable core you extend skill
> by skill. The architecture is designed so the other three pillars drop in
> without rework.

## What works today

- **Electron desktop app** (Win/Mac/Linux) with a tray icon and dashboard.
- **Voice from day one** — wake word ("aria") + speech-to-text + spoken replies,
  using the browser-native Web Speech API (no native dependencies).
- **Claude brain** — natural-language and voice commands run through a manual
  tool-use loop (`claude-opus-4-8`, adaptive thinking) against the skill registry.
- **Stocks skill** — live quotes, ticker search, price history, and a persisted
  watchlist via public market-data endpoints. **The data panels work without an
  API key**; only the conversational/voice brain needs one.

## Run it

```bash
cd assistant
npm install
cp .env.example .env      # then paste your ANTHROPIC_API_KEY (optional but needed for voice/chat)
npm start
```

Node 18+ required (uses global `fetch`).

## Architecture

```
src/
  main/                     Electron main process (Node)
    main.js                 window + tray + lifecycle
    preload.js              secure contextBridge → window.aria
    ipc.js                  renderer↔main channels (data + brain)
    brain.js                Claude tool-use loop
    config.js / store.js    env config + JSON persistence
    services/
      skills.js             skill registry (add pillars here)
      stocks.js             ← the Stocks skill (tools + handlers + data API)
  renderer/                 dashboard UI (Chromium, no Node)
    index.html / styles.css
    renderer.js             panels + chat controller
    voice.js                wake word, STT, TTS
```

**Adding a pillar** (accounting / study / productivity): create
`services/<pillar>.js` exporting `{ name, systemPromptFragment, tools,
handlers, api }`, then register it in `services/skills.js`. The brain picks up
the new tools automatically; add a UI panel if it needs one.

### Design choices worth knowing

- **Manual tool loop, not the auto runner** — gives a natural place to insert
  human-approval gates before sensitive actions (trades, posting ledger
  entries). Money actions should never be blindly autonomous; approval
  checkpoints are built into the design.
- **Stock data is decoupled from the brain** — UI panels call data IPC directly,
  so the app is useful even with no API key and stays responsive.
- **Provider abstraction** — `stocks.js` is the only file to change to swap the
  market-data source for a keyed provider (Finnhub / Polygon / Alpha Vantage).

## Meta glasses — the honest path

Ray-Ban Meta / Meta's display glasses currently have **no open third-party app
SDK**; you cannot deploy a custom app onto them. The realistic integration is a
**voice/notification relay**: the glasses act as mic + speaker + camera, while
ARIA runs on the desktop/phone and answers. When (if) Meta opens a wearable SDK,
the relay slots in behind the existing voice interface — `voice.js` is the seam.

## Roadmap

1. **Stocks** ✅ (this slice) — quotes, search, history, watchlist, voice.
2. **Productivity** — daily briefing, tasks, calendar, Gmail triage.
3. **Accounting** — ledger/invoices, categorization, reports (ties into the
   existing workspace site).
4. **Studying** — notes ingestion, flashcards, spaced repetition, tutor Q&A.
5. **Hardening** — trade/entry approval gates, wake-word engine (Porcupine),
   packaging/auto-update, encrypted local store.

Not financial advice. Market data may be delayed.
