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

### Web sessions: allow the market-data host

Claude Code **web** sessions run behind a network allowlist, which blocks the
market-data feed by default. To let quotes load in a web session, open the
environment's settings → **Network access** → **Custom**, tick *"Also include
default list of common package managers"*, and add:

```text
query1.finance.yahoo.com
query2.finance.yahoo.com
```

This is a web-UI setting (there is no committed config file for it). Local
`npm start` on your own machine is unaffected — it has full network access.

### Voice recognition (push-to-talk) — fully local

The **🎤 Talk** button records your mic and transcribes it **entirely on your
machine** by default — audio never leaves the device and no network is used.
Mic capture (`getUserMedia`) and recognition (a local Vosk model) both run
locally. (The browser `SpeechRecognition` wake-word toggle stays as a fallback,
but it doesn't actually work in vanilla Electron — hence the local engine.)

Recognition uses on-device **Whisper** via `@huggingface/transformers` — no
native compilation, no `ffi-napi`. Setup:

```bash
npm install      # pulls optional @huggingface/transformers (+ onnxruntime)
npm run model    # optional: pre-download the model so it's offline-ready
npm start
```

Click Talk to record, click again to stop → it transcribes **locally** and asks
the brain. The first transcription downloads the model weights once (then it's
offline); `npm run model` does that ahead of time. Set `WHISPER_MODEL` to
`Xenova/whisper-base.en` or `small.en` for more accuracy at some speed cost.

**Prefer the cloud instead?** Set `STT_ENGINE=whisper-api` + `STT_API_KEY` in
`.env` (OpenAI or Groq). Off by default — local is the default.

### The brain — fully local option (no API key)

The brain (`src/main/brain.js`) runs a tool-use loop over the skill registry
with one of two engines:

| Engine | What it is | Needs |
|---|---|---|
| `local` | **Ollama** running on your machine — no API key, no account, audio/text never leave the device | Install <https://ollama.com>, then `ollama pull qwen2.5:7b` |
| `claude` | Anthropic API (`claude-opus-4-8`) — strongest reasoning | `ANTHROPIC_API_KEY` |

Default: `claude` if a key is set, otherwise `local`. Force one with
`BRAIN_ENGINE=local` (or `claude`) in `.env`. For local, `qwen2.5:7b` has solid
tool-calling; larger models (`qwen2.5:14b`, `llama3.1:8b`) improve quality if
your hardware allows. The header shows which engine is live.

With `BRAIN_ENGINE=local` + local voice (default) the entire assistant is
on-device: the only internet use is fetching public market data and any
optional connections you add (Google, Alpaca).

Customize behavior without code via `ARIA_PERSONA` in `.env` (appended to the
system prompt), or extend abilities by adding a skill module (see "Adding a
pillar") — new tools are picked up by both engines automatically.

### Technical analysis (local)

The brain has a local TA engine (`services/analysis.js`) — SMA20/50, RSI(14),
MACD(12/26/9), Bollinger(20,2σ) — computed from public price history, no key:

- *"Analyze NVDA"* → indicators + plain-language signals (trend, momentum,
  overbought/oversold, band position).
- *"Scan my watchlist"* → RSI/trend/momentum/20-day change across every ticker.

Informational only — not financial advice. Pair with `propose_trade` and the
approval gate when you want to act on it.

### Connect a Google account (Gmail + Calendar)

Productivity can read your **unread Gmail** and **today's Calendar** (read-only)
to power the daily briefing and the Today panel.

1. In Google Cloud Console, create an OAuth client of type **Desktop app** and
   enable the **Gmail API** + **Google Calendar API**.
2. Put the client id/secret in `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
3. In the app → **Connections** → **Google: Connect**. A browser opens for
   consent; tokens are stored on-device (refresh token via the OS keychain).

### Connect a trading account (Alpaca)

You can connect a real brokerage account via **Alpaca** — **paper or live**.

- In the app → **Connections** → **Trading account**: pick **Paper** or **Live**,
  paste your Alpaca **Key ID** and **Secret**, and Connect. The credentials are
  validated against Alpaca and stored **encrypted** on-device (Electron
  `safeStorage`); the secret is never sent back to the UI.
- Once connected, the portfolio and fills route through Alpaca instead of the
  built-in simulator — **but the approval gate is unchanged**: the assistant
  still only *stages* orders, and nothing executes until you click **Approve**.
- **Live** orders are real money. Live mode requires an explicit confirm to
  connect, and every live approval card is flagged red ("live · real money").
- Get paper keys at <https://alpaca.markets> (Paper Trading → API keys). Paper
  is strongly recommended until you trust the flow.

### Trading (paper) — approval-gated

The Trading panel runs a **simulated** account (starting cash $100,000). The
safety model is deliberate:

- The Claude brain can only **propose** a trade (`propose_trade`); it has no
  tool that executes. Proposals appear as pending **approval cards**.
- A trade fills **only** when you click **Approve** — re-priced at the live
  quote at that moment. **Reject** discards it. Both AI- and manually-entered
  orders funnel through the same approval gate.
- Real-money brokerage (e.g. Alpaca) would slot in behind the fill step and
  stay gated behind this approval + paper-mode default. It is **not** enabled.

## Packaging — build installers

The app packages into native installers with `electron-builder`.

```bash
npm install            # includes electron-builder (dev dep)
npm run icon           # (re)generate build/icon.png from the SVG mark
npm run dist:linux     # → dist/ARIA-<ver>.AppImage + .deb
npm run dist:win       # → dist/ARIA Setup <ver>.exe   (NSIS; run on Windows)
npm run dist:mac       # → dist/ARIA-<ver>.dmg + .zip   (run on macOS)
npm run pack           # unpacked app only (dist/<platform>-unpacked), for testing
```

Build for each OS on that OS (electron-builder doesn't cross-compile mac/win
reliably). The Linux AppImage build is verified; mac/win use the same standard
config. Outputs land in `dist/` (gitignored). The app icon is generated by
rendering an SVG with Electron (`scripts/make-icon.js`) — no image toolchain
needed — and electron-builder derives the `.icns`/`.ico`/Linux sizes from it.

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

1. **Stocks** ✅ — quotes, search, history, watchlist, voice, **price chart**
   (click any ticker, selectable range, auto-refreshing intraday), **news
   headlines** per ticker, and **price alerts** (above/below thresholds → OS
   notification + chime; the brain can set them by voice).
1b. **Trading (paper)** ✅ — approval-gated buy/sell, live-priced fills, portfolio P/L.
1c. **Trading account (Alpaca)** ✅ — connect a real paper/live brokerage
   account; portfolio + fills route through Alpaca behind the same approval gate.
2. **Productivity** ✅ — tasks, quick notes, daily briefing, and **Google
   (Gmail unread + Calendar today)** via on-device OAuth, surfaced in the Today
   panel and the briefing.
3. **Accounting** ✅ — income/expense ledger with categories, invoices
   (issue/track/mark-paid), and a P&L summary (income, expenses, net, by
   category, cash position, accounts receivable). Local, brain-accessible.
4. **Studying** — notes ingestion, flashcards, spaced repetition, tutor Q&A.
5. **Hardening** — trade/entry approval gates, wake-word engine (Porcupine),
   packaging/auto-update, encrypted local store.

Not financial advice. Market data may be delayed.
