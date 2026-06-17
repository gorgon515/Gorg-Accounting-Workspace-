# HELIOS — The Personal Intelligence Operating System

> Local-first, voice-enabled, multi-agent intelligence platform that functions as
> a digital chief of staff, accounting advisor, language tutor, research analyst,
> productivity manager, and quantitative investment platform.

This directory is the **HELIOS architecture blueprint** — the design deliverables
(1–20) for the full platform. It is deliberately honest about what exists today
versus what is designed, so it can guide real, incremental delivery rather than
read as vapor.

## How HELIOS relates to ARIA (this repository)

HELIOS is **not** a greenfield project. This repository already contains
[`assistant/`](../../assistant) — **ARIA**, a working local-first Electron
assistant that implements a large slice of the HELIOS foundation:

- A **fully-local brain** (Ollama, no API key) with optional Claude, running a
  manual tool-use loop (`assistant/src/main/brain.js`).
- **On-device voice** — Whisper STT via `@huggingface/transformers`
  (`assistant/src/main/services/stt.js`), browser TTS (`renderer/voice.js`).
- A **pluggable skill registry** (`services/skills.js`) — the seam every HELIOS
  agent plugs into.
- Working pillars: **stocks, trading (approval-gated), accounting ledger,
  study/CPA, productivity, Gmail+Calendar, price alerts, trade ideas**, and
  **persistent memory**.
- **Security primitives** — OS-keychain-encrypted secrets (`store.js`), strict
  CSP, `contextIsolation`, no `nodeIntegration` in the renderer.

**ARIA is the reference runtime of HELIOS.** This blueprint describes how ARIA
grows into the full HELIOS platform: a multi-agent orchestration layer, a
Python/FastAPI compute sidecar, ChromaDB + PostgreSQL persistence, embedded N8N,
the Language Immersion Center, the Accounting Intelligence Center, and a HUD-grade
React/TypeScript front end.

> Branding note: the running app is still named *ARIA* in `package.json` and the
> build config. A product rename to *HELIOS* is a tracked roadmap item
> ([05-roadmap](./05-roadmap.md)); it is cosmetic and touches packaging/CI, so it
> is deliberately separated from the functional work.

## What shipped with this blueprint

Alongside the documents, two concrete, tested increments were added to ARIA to
prove the architecture extends as designed:

| Increment | Files | Status |
|---|---|---|
| **Multi-agent orchestration layer** | `assistant/src/main/services/agents.js` | ✅ working — 15-agent roster with personas/permissions/activity logging, local router, `which_agent` tool, Agent Activity panel |
| **Language Immersion Center** | `assistant/src/main/services/language.js` + IPC/preload/UI | ✅ working — 7 languages, shared SRS, daily missions, CEFR pathway, roleplay seeds |
| **Intelligence Sidecar** (Phase 2) | `backend/` (FastAPI) + `assistant/src/main/services/sidecar.js` | ✅ working — Quant Research Engine + Accounting Intelligence Engine; autostarted/supervised by Electron; 35 backend + 11 Node tests |
| **React HUD Command Center** (Phase 3) | `assistant/frontend-react/` | ✅ builds — React/TS/Tailwind/Framer; design system, 3-column layout, 13 views, typed IPC client, event bus; opt-in via `HELIOS_UI=react` (classic stays default) |
| **Intelligence engines** (Phase 4) | `backend/accounting/`, `backend/quant/`, `backend/n8n/` | ✅ working — accounting collectors/storage/briefing/graph/research, quant fundamentals/signals/market-briefing, N8N client + workflow generator; wired to the HUD; 87 backend tests |

All are wired into the registry, exposed over IPC, surfaced in the UI, and
covered by tests (router 14/14; full language lifecycle; backend 35; registry 11).

### Phase 2 progress (this pass)

The Python/FastAPI **Intelligence Sidecar** (deliverables 3/6/7) landed as real,
tested code — see [`backend/README.md`](../../backend/README.md):

- **Quant Research Engine** — technicals (SMA/EMA/RSI/MACD/Bollinger/momentum/
  volatility/drawdown), transparent value/quality/growth/momentum **factor
  scoring**, risk (Sharpe/Sortino/beta/correlation/VaR), and **portfolio**
  analytics (concentration, sector exposure).
- **Accounting Intelligence Engine** — a citable ASC knowledge base (606/842/326/
  350/718) and a **technical-memo generator** (Issue/Facts/Guidance/Analysis/
  Conclusion/Disclosure/CPA-impact).
- **Market-data connector layer** — provider abstraction + TTL cache +
  normalization (Yahoo today; Alpha Vantage/Polygon/FMP slot in behind it).
- **Agent system upgrade** — 15 specialists (added FASB, SEC, CPA Coach,
  Portfolio, Quant Research) each with persona, system instructions, tool/memory
  permissions, and per-tool-call activity logging.

### Phase 3 progress (React HUD)

The **Command Center** front end (deliverables: React migration, design system,
routing, dashboard + all centers, event bus) was built additively in
`assistant/frontend-react/` — see its [README](../../assistant/frontend-react/README.md):

- **React + TypeScript + Tailwind + Framer Motion**, dark-mode-first HUD; build
  verified (`tsc` clean, `vite build` passes, 428 modules).
- **Design system**: Button/Card/Panel/Drawer/Modal/StatusBadge/AgentCard/
  MetricCard/ActivityFeed/Table/Chart/Timeline/VoiceVisualizer/NotificationPanel.
- **Three-column layout** (nav · workspace · live-intelligence rail) + a typed,
  safe IPC client and a real-time **event bus** (polling + the Electron alert
  push channel) — no reloads.
- **13 views**: Dashboard, Assistant (agent + tool visibility), Markets,
  Portfolio, Accounting (ASC research + memo generator), CPA, Language, Calendar,
  Email, Memory, Agent Activity, Automations, Settings — each wired to real IPC
  with graceful offline states.
- **No regression**: kept opt-in via `HELIOS_UI=react`; the classic renderer
  stays default; the 11 Node tests still pass. Added a small additive Memory IPC.

### Phase 4 progress (intelligence engines)

The differentiating engines behind the UI — real working code, **87 backend
tests** (see [`backend/README.md`](../../backend/README.md)):

- **Accounting Intelligence Engine** — real FASB/SEC/PCAOB/IRS feed collectors
  (SEC-compliant UA, network-guarded, env-overridable), RSS/Atom parsers, a
  normalized `IntelItem` schema with ASC/ASU/effective-date extraction, a SQLite
  store (dedup + historical tracking), and a **daily briefing generator**
  (executive summary, key changes, upcoming effective dates, affected industries,
  CPA impact, emerging risks, action items, confidence).
- **FASB knowledge graph** + **research engine** — ASC ↔ ASU ↔ industry ↔ FS area
  ↔ disclosure ↔ audit ↔ tax graph; implementation checklists and full technical
  memos (Facts/Issue/Guidance/Analysis/Alternatives/Conclusion/References).
- **Quant Research Engine** — fundamentals (ratios/growth/quality/peers), advanced
  technicals (ATR, relative strength, momentum/trend/volume scores), a **signal
  engine** that separates facts/calculations/interpretations/forecasts, and a
  **daily market briefing**.
- **Market-data pipeline** — provider adapters (Yahoo + FMP + Alpha Vantage + SEC
  filings) with normalization, caching, and refresh-time/staleness tracking.
- **N8N integration layer** — a real REST client (list/run/create/monitor) and an
  **AI workflow generator** emitting importable N8N JSON (flagship: the daily
  accounting-briefing workflow).
- **Wired to the HUD, no mock data**: Accounting (live briefing + developments
  feed), Markets (live market briefing), Automations (N8N status + generation),
  exposed as brain tools (`accounting_briefing`, `quant_signal`, `market_briefing`,
  `implementation_checklist`, `generate_workflow`). Network-restricted sandboxes
  degrade gracefully; live sources populate on a networked machine.

## The documents (deliverables 1–20)

| # | Document | Deliverables covered |
|---|---|---|
| 1 | [System Architecture](./01-system-architecture.md) | Software (1), Agent (3), Memory (4), N8N (5), Frontend (6), Backend (7), Security (11) |
| 2 | [Data & API Architecture](./02-data-architecture.md) | Database (2), Schema (14), API specs (15) |
| 3 | [Domain Architecture](./03-domain-architecture.md) | Accounting (8), Trading (9), Language (10) |
| 4 | [UX & Folder Structure](./04-ux-and-structure.md) | Wireframes (12), Folder structure (13) |
| 5 | [Roadmaps](./05-roadmap.md) | Development (16), MVP (17), Phase 2 (18), Enterprise (19) |
| 6 | [Deployment](./06-deployment.md) | Deployment instructions (20) |
| 21 | Implementation code | The `assistant/` codebase + the two increments above; status matrix below |

## Status matrix — real vs. designed

Legend: ✅ implemented in ARIA today · 🟡 partial · ⬜ designed (this blueprint)

| Capability | Spec target | Today | Notes |
|---|---|:--:|---|
| Local brain, no API key | Ollama / llama.cpp / LM Studio | ✅ | `brain.js` auto-detects pulled Ollama models; Claude optional |
| Multi-model routing | Route by task | 🟡 | Engine select (local/Claude) today; per-agent model routing designed |
| Voice STT | Whisper / Faster-Whisper | ✅ | On-device `transformers.js` Whisper |
| Voice TTS | Piper / Coqui | 🟡 | Browser TTS today; Piper sidecar designed |
| Wake word / push-to-talk | both | 🟡 | Push-to-talk works; robust wake word designed |
| Multi-agent system | 11+ agents + orchestration | ✅ | 15 agents w/ personas, permissions, activity logging, router |
| Memory: short/long/project/etc. | ChromaDB + Postgres | 🟡 | Durable JSON memory today; vector + relational designed |
| N8N automation center | embedded N8N | 🟡 | Real REST client + AI workflow generator (importable JSON); embedded editor designed |
| Language Immersion | 7 langs, full pathway | ✅ | `language.js` — SRS, missions, CEFR, roleplay |
| Accounting platform | GL/AP/AR/statements… | 🟡 | Ledger + invoices + P&L today; full GL designed |
| Accounting Intelligence Center | FASB/SEC/IRS monitoring | ✅ | Real collectors + SQLite store + daily briefing + knowledge graph + research engine; live feeds need network |
| CPA Study Center | qbank + simulations | 🟡 | Progress tracker + flashcards + CPA Coach agent; qbank designed |
| Market intelligence | fundamentals→options | 🟡 | Quotes/news/technicals + fundamentals + signals + market briefing; options/insider feeds designed |
| Quant research | backtests/Monte Carlo | 🟡 | Technicals, factors, fundamentals, risk, portfolio, signals; backtests/Monte Carlo next |
| Trade recommendations | gated, with R/R | ✅ | Strategy engine + approval gate; never auto-executes |
| Brokerage integration | IBKR/Alpaca/… | 🟡 | Alpaca paper/live connected; others designed |
| Email | Gmail/Outlook | 🟡 | Gmail read today; drafting/Outlook designed |
| Calendar | Google/Outlook | 🟡 | Google read today; scheduling/Outlook designed |
| Knowledge graph | visual graph | ⬜ | Designed |
| Security: encryption/vault/RBAC/audit | AES-256, audit logs | 🟡 | OS-keychain secrets + CSP today; vault/RBAC/audit designed |
| Front end | React/TS/Tailwind/Framer | 🟡 | React HUD built (`frontend-react/`, opt-in); classic renderer still default until visually validated |
| Backend | Python/FastAPI | 🟡 | FastAPI Intelligence Sidecar live (quant + accounting); more domains designed |

## Reading order

If you are implementing: read [01](./01-system-architecture.md) →
[02](./02-data-architecture.md) → [04](./04-ux-and-structure.md) →
[05](./05-roadmap.md). If you are evaluating: this README + the status matrix is
enough.
