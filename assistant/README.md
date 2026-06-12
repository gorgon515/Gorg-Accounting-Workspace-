# ARIA — Integrated Desktop Assistant

A voice-driven desktop assistant for **stocks, accounting, studying, and
productivity**, built as an Electron app with a pluggable skill architecture and
a **local-first brain** (built-in on-device model by default; Ollama or Claude
as optional upgrades). This repository contains the **first working vertical
slice: Stocks**, with voice enabled from day one.

> Scope note: a "tops any Jarvis" assistant is a platform, not a weekend build.
> This is the foundation done properly — a real, runnable core you extend skill
> by skill. The architecture is designed so the other three pillars drop in
> without rework.

## What works today

- **Electron desktop app** (Win/Mac/Linux) with a tray icon and dashboard.
- **Voice from day one** — wake word ("aria") + speech-to-text + spoken replies,
  using the browser-native Web Speech API (no native dependencies).
- **Completely local brain, zero setup** — natural-language and voice commands
  run through a manual tool-use loop against the skill registry. A built-in
  on-device model works out of the box (no API key, no installs); Ollama and
  Claude (`claude-opus-4-8`) are optional upgrades.
- **Stocks skill** — live quotes, ticker search, price history, and a persisted
  watchlist via public market-data endpoints. **No API key needed anywhere** —
  panels and brain both work without one.

## Run it

```bash
cd assistant
npm install
npm start                 # that's it — no API key, no .env needed
```

Everything works with zero configuration: panels, voice, and the brain (the
built-in local model downloads once on first use; `npm run model` pre-fetches
it). Copy `.env.example` to `.env` only if you want to customize — e.g. use
Ollama/Claude as the brain, add Google, or enable the phone bridges.

Node 18+ required (uses global `fetch`); CI builds the installers on Node 24.

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

### The brain — completely local, zero setup, no API key

The brain (`src/main/brain.js`) runs a tool-use loop over the skill registry.
**Out of the box it is completely local and needs nothing from you** — no API
key, no account, no separate install:

- **Built-in (default)** — a small instruct model
  (`onnx-community/Qwen2.5-0.5B-Instruct`) runs **in-process on CPU** via
  transformers.js, the same runtime as the local voice. The weights download
  once on first use (`npm run model` pre-fetches them); after that the brain
  works **fully offline**. Upgrade quality with
  `EMBEDDED_MODEL=onnx-community/Qwen2.5-1.5B-Instruct` in `.env`.
- **Ollama (optional upgrade)** — install <https://ollama.com> and
  `ollama pull qwen2.5:7b`; auto mode detects it and prefers it over the
  built-in model. The app picks up whichever chat model you've pulled.
- **Claude (optional, not local)** — add `ANTHROPIC_API_KEY` to `.env` to use
  `claude-opus-4-8` instead — strongest at multi-step tool use. Claude cannot
  run inside Ollama (it is not open-weights); the API is the only way. Leave
  the key blank to stay fully local.

Auto order: Claude if a key is set → Ollama if it's running → built-in. Force
one with `BRAIN_ENGINE=embedded | local | claude`. With local voice
(on-device Whisper), a local brain, and local TTS, the whole assistant runs
on-device — the only internet use is public market data and any connections
you opt into.

Customize behavior without code via `ARIA_PERSONA` in `.env` (appended to the
system prompt), or extend abilities by adding a skill module (see "Adding a
pillar") — new tools are picked up by every engine automatically.

### Trade-idea engine (calls / puts / futures)

`services/strategy.js` forms a directional thesis from local technicals, scores
the **setup quality** (signal confluence — explicitly **not** a probability of
profit), and turns it into concrete, defined-risk ideas using **real options
chains** (Yahoo, no key):

- *"Find a trade on NVDA"* → bias + setup score, underlying entry/stop/target, a
  specific **long call/put** (strike, expiry, break-even, % move required, max
  loss, IV), a **defined-risk vertical spread**, and a **futures** alternative
  for index/commodity proxies (ES/NQ/GC… incl. micros).
- *"Scan for setups"* → watchlist ranked by setup score.
- Returns **"stand aside"** when there's no clean setup — often the best call.

It **generates ideas only**. Equities execute through `propose_trade` + the
approval gate; options/futures are placed manually at your broker. Options and
futures carry substantial risk and can lose 100% — every idea says so. Not
financial advice.

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

### Text ARIA from your phone (iMessage — macOS only)

Apple has **no public iMessage API**. The one workable path is on a **Mac**:
ARIA reads the local Messages database and replies by scripting Messages.app.
Since your iPhone's iMessages sync to the Mac, you can text ARIA from your phone
and get replies back on your phone.

Setup (Mac only):
1. In `.env`: `IMESSAGE_ENABLED=true` and `IMESSAGE_ALLOW=+1yournumber,you@icloud.com`
   (only these handles are answered — empty list = never responds). Optional
   `IMESSAGE_TRIGGER=aria` so only texts starting with "aria" are handled.
2. Grant the app **Full Disk Access** (System Settings → Privacy & Security →
   Full Disk Access) so it can read `~/Library/Messages/chat.db`.
3. Allow **Automation → Messages** when prompted (to send replies).

Then text yourself/your Mac: *"aria how's NVDA"* → ARIA replies on your phone.
Price alerts are also texted to you (`IMESSAGE_ALERTS=true`). The approval gate
still holds — a trade proposed by text waits for your in-app Approve click.
Non-macOS builds show "macOS only" and the bridge stays off.

### Text ARIA from your phone on Windows (Telegram)

**iMessage cannot work on Windows** — Apple provides no API, no Windows client,
and blocks workarounds (the Mac-relay projects like BlueBubbles need an
always-on Mac). The cross-platform phone channel is a **Telegram bot**:

1. In Telegram (free app, works on iPhone): message **@BotFather** → `/newbot`
   → copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.
2. Put your Telegram `@username` (without the @) or chat id in `TELEGRAM_ALLOW`.
3. Restart ARIA, then message your bot: *"how's NVDA?"*, *"scan for trades"*,
   *"add a task: file taxes Friday"*.

ARIA answers only allowlisted users (empty list = answers no one). Price alerts
are also pushed to your phone (`TELEGRAM_ALERTS=true`). The approval gate
holds — trades proposed by text still wait for your in-app Approve click. Uses
outbound long-polling only: no inbound ports, no public server.

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

## Download the desktop app

Installers are produced by the **Build ARIA installers** GitHub Actions
workflow (`.github/workflows/build-installers.yml`) on native runners:

- **Windows** — `ARIA Setup <ver>.exe` (NSIS installer)
- **macOS** — `ARIA-<ver>.dmg` (+ zip), arm64 & Intel
- **Linux** — `ARIA-<ver>.AppImage` + `.deb`

Every run attaches all installers to a **GitHub Release** (Releases page →
Assets). Two ways to trigger one:

1. **Manual:** GitHub → Actions → *Build ARIA installers* → *Run workflow*.
   Releases under `v<version>` from `package.json`; the same files are also
   downloadable as artifacts from the run page.
2. **Versioned tag:** `git tag v0.2.0 && git push origin v0.2.0` → releases
   under that tag.

Builds are unsigned (no certificates), so expect the usual first-run prompts:
Windows SmartScreen → "More info → Run anyway"; macOS → right-click → Open.
Installers bundle the app + Electron (~160 MB; GPU inference libraries are
excluded — the local voice model runs on CPU).

## Packaging — build installers locally

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
4. **Studying** ✅ — notes, spaced-repetition flashcards (SM-2), study log +
   streak, a **Russian** vocab trainer, conversational tutoring, synopsis of
   saved material, and a **Becker CPA** progress tracker (AUD/FAR/REG/BAR/ISC/
   TCP). Becker has no public API, so progress is tracked locally and the panel
   links out to becker.com for the lessons.
5. **Hardening** — wake-word engine, auto-update, broader test coverage.

Not financial advice. Market data may be delayed.
