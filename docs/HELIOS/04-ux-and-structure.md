# 04 — UX & Folder Structure

Covers deliverables **12 (UI/UX wireframes), 13 (folder structure)**.

---

## 12. UI/UX wireframes

Aesthetic: futuristic, premium, dark, glassmorphism, **Iron Man HUD**. The design
tokens already exist in `assistant/src/renderer/styles.css` (obsidian/charcoal/
slate base, antique-gold accent, hairline borders, JetBrains Mono for figures).
Wireframes below are the target layout; the current app already implements a
two-column version of the Command Center.

### Home — Command Center

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◎ HELIOS   ───────   PERSONAL INTELLIGENCE OS        ● brain · local · qwen │ status bar
│                                                  ⌘K command palette · 🎙 ◯ │ voice orb
├───────────────────────────────┬──────────────────────────────────────────┤
│  ☀ DAILY BRIEFING              │  AGENT ACTIVITY        11/13 online        │
│  Good morning. 3 meetings,     │  ● Chief of Staff   ● Accounting  ● Quant  │
│  2 due tasks, NVDA +2.1%,      │  ● Trading  ● Language  ● Research ○ Auto.. │
│  1 new FASB ASU, FAR 62%.      │  ────────────────────────────────────────  │
│  [ Brief me ]  [ Plan my day ] │  MEMORY ACTIVITY   +2 facts today          │
├───────────────────────────────┼──────────────────────────────────────────┤
│  ASSISTANT (voice + chat)      │  MARKET DASHBOARD     ▲ watchlist          │
│  ┌──────────────────────────┐  │  AAPL 224.10 +0.8%   NVDA 132.4 +2.1%      │
│  │ transcript …             │  │  ── chart ──────────────────────────────  │
│  │                          │  │  PORTFOLIO   $104,210   +4.21% │ paper     │
│  │ > how is NVDA doing?     │  │  ACCOUNTING ALERTS  ▸ 1 invoice overdue    │
│  └──────────────────────────┘  │  FASB UPDATES  ▸ ASU 2025-xx (eff. 2026)   │
│  [ 🎤 Talk ] [ type here…  ▷ ] │  CPA STUDY  FAR ▓▓▓▓▓▓░░ 62%               │
├───────────────────────────────┼──────────────────────────────────────────┤
│  TASKS · CALENDAR · EMAIL      │  LANGUAGE  🇪🇸 Spanish · 2 due · 4-day 🔥  │
│  ▢ File Q2 sales tax (today)   │  WORKFLOWS  ▸ 2 active                     │
│  ◷ 14:00 Client call           │  NOTIFICATIONS  🔔 alert: NVDA above 130   │
└───────────────────────────────┴──────────────────────────────────────────┘
```

Every block maps to a panel and an IPC source. The **Home Command Center**
surfaces: Daily Briefing, Calendar, Tasks, Emails, Market Dashboard, Portfolio,
Accounting Alerts, FASB Updates, CPA Study, Language, Active Workflows, Agent
Activity, Memory Activity, Notifications — the full required set.

### Voice interaction states

```
   idle ──(wake word / push-to-talk)──► listening ──► transcribing
     ▲                                                     │
     └────────── speaking (interruptible) ◄── thinking ◄───┘
                       ▲ barge-in cancels TTS
```
Voice orb in the status bar reflects state with color + motion (calm pulse when
listening, fast when thinking). Interruptible speech: a new utterance cancels
in-flight TTS. Push-to-talk works today; continuous wake word is hardening work.

### Language Immersion Center (a flagship screen)

```
┌─ LANGUAGE ─────────────────────  🇪🇸 Spanish ▼ ──┐
│ [ Today ] [ Vocab ] [ Pathway ]                    │
│ 🇪🇸 Spanish · 128 words · 6 due · 4-day streak ·  │
│ ~A2 (self A2)                                      │
│ ────────────────────────────────────────────────  │
│ TODAY'S MISSIONS                                   │
│ [SPEAKING] Roleplay: order at a café        ▢      │
│ [LISTENING] Shadow one audio clip           ✓      │
│ [WRITING ] Journal 2 sentences              ▢      │
│ [VOCAB   ] Clear due cards, learn 5 new     ▢      │
└────────────────────────────────────────────────────┘
```
Implemented today (`LanguagePanel`): language selector, Today (progress +
missions), Vocab (add card → shared SRS), Pathway (A1→C2 goals).

### Accounting workspace & Knowledge Graph (designed)

```
ACCOUNTING                                  KNOWLEDGE GRAPH
┌ GL │ COA │ AP/AR │ Statements │ Intel ┐   ┌───────────────────────────────┐
│ Balance Sheet  ▸  Income  ▸  Cash Flow │  │   (Verum Advisory)──works_on──▶│
│ Trial balance ……………………… in balance ✓ │  │      │ owns          (ASC 606) │
│ DAILY ACCOUNTING BRIEFING               │  │   (Invoice #12)   ╲  mentions  │
│  • New FASB ASU 2025-xx                 │  │      relates_to    (Revenue)   │
│  • IRS Notice 2025-xx                   │  │   (Client A)──person──(J. Doe) │
└─────────────────────────────────────────┘  └───────────────────────────────┘
```
Knowledge Graph (`kg_node`/`kg_edge`) renders projects, people, companies, topics,
tasks, and notes as a navigable force-directed graph; clicking a node opens the
related panel.

### Interaction principles

- **Glassmorphism with restraint** — translucent panels over the obsidian base,
  hairline borders, gold used sparingly for emphasis and figures.
- **Motion is informational** — Framer Motion transitions signal state changes
  (panel hydrate, agent active, alert fire); all respect `prefers-reduced-motion`
  (already honored in `styles.css`).
- **Keyboard-first** — `⌘K` command palette routes any request to the right agent;
  voice and palette share the same intent pipeline (`agents.route`).

---

## 13. Folder structure

### Today (this repository)

```
Gorg-Accounting-Workspace-/
├── assistant/                    ARIA — the HELIOS reference runtime (Electron)
│   ├── src/
│   │   ├── main/                 Electron main process (Node) = orchestrator
│   │   │   ├── main.js           window + tray + lifecycle
│   │   │   ├── preload.js        secure contextBridge → window.aria
│   │   │   ├── ipc.js            renderer↔main channels
│   │   │   ├── brain.js          tool-use loop (Ollama | Claude)
│   │   │   ├── config.js         env config
│   │   │   ├── store.js          JSON persistence + OS-keychain secrets
│   │   │   └── services/         the skill registry
│   │   │       ├── skills.js     registry + system prompt
│   │   │       ├── agents.js     ◀ orchestration layer (new)
│   │   │       ├── language.js   ◀ Language Immersion Center (new)
│   │   │       ├── stocks.js trading.js strategy.js analysis.js broker.js
│   │   │       ├── accounting.js study.js productivity.js
│   │   │       ├── google.js alerts.js memory.js stt.js
│   │   │       └── telegram.js imessage.js
│   │   └── renderer/             dashboard UI (Chromium, no Node)
│   │       ├── index.html  styles.css  renderer.js
│   │       └── voice.js  recorder.js
│   ├── scripts/  build/  package.json
│   └── README.md
├── docs/HELIOS/                  ◀ this architecture blueprint (new)
├── (Verum Advisory website)      index.html, practice.html, assets/ …
└── (reference zips)              whisper, yahoo-finance, n8n-related, ui skills…
```

### Target (full HELIOS)

```
helios/
├── desktop/                      Electron shell
│   ├── main/                     (as today; services/ grows per agent)
│   └── renderer/                 React + TS + Tailwind + Framer Motion
│       ├── app/ hud/ panels/ voice/ state/ ipc/ theme/
├── sidecar/                      Python / FastAPI compute service
│   ├── app/ (main.py, routers/)  quant/ nlp/ docs/ intel/
│   ├── quant/ (factors, backtest, montecarlo, optimize)
│   └── pyproject.toml
├── data/                         migrations (Postgres), Chroma config
│   ├── migrations/*.sql
│   └── seed/
├── automation/                   N8N workflow templates + provisioning
├── packages/                     shared TS types (IPC + domain models)
├── docs/                         this blueprint + ADRs
└── infra/                        local install scripts, model bootstrap
```

The target is reached by **renaming/relocating, not rewriting**: `assistant/`
becomes `desktop/`, services stay where they are, and `sidecar/` + `data/` +
`automation/` are additive. The IPC surface and domain models are extracted to
`packages/` as shared TypeScript types so the React renderer and any future
clients share one contract.
