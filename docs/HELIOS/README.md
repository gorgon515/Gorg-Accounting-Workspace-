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
| **Chief of Staff / operational layer** (Phase 5) | `backend/tasks`, `goals`, `scheduler`, `email_intel`, `calendar_intel`, `cos`, `integrations` | ✅ working — task & goal intelligence, timezone-aware scheduler, email/calendar intelligence, daily briefing + evening review + memory-driven planner, Google/Outlook adapters; Chief of Staff HUD view; 131 backend tests |
| **Accounting platform** (Phase 6) | `backend/accounting_platform/` | ✅ working — real double-entry GL, chart of accounts + templates, journal engine, AP/AR (posting to GL), fixed-asset depreciation, bank reconciliation, financial statements (BS/IS/CF), clients/documents, immutable audit trail, dashboard; Ledger HUD view; 159 backend tests |
| **Document intelligence + tax/advisory workbench** (Phase 7) | `backend/document_intelligence/`, `tax_research/`, `workpapers/`, `advisory/`, `global_search.py` | ✅ working — real PDF/Excel/Word/email extraction + gated OCR + classification + field extraction; tax research (authority hierarchy + memo) + organizer; workpaper generator; financial-statement analysis; due diligence; global search; 5 new agents; Workbench HUD view; 181 backend tests |
| **Execution / automation OS** (Phase 8) | `backend/execution/`, `operations/`, `outcomes/` | ✅ working — approval engine with enforced risk tiers (Tier 4 never auto, prepare-only), execution engine (propose/approve/execute/rollback/retry + audit), document→accounting automation, month-end close, outcome tracking + learning calibration, ops dashboards, AI workflow builder; Operations HUD view; 196 backend tests |

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

### Phase 5 progress (chief of staff / operational layer)

The proactive operating layer that runs the day — **131 backend tests**:

- **Task Intelligence** — SQLite tasks with priority/deadline scoring,
  recurrence, dependencies (blocking), auto-categorization, and recommendations.
- **Goal system** — milestones, progress, and **deadline-aware forecasting**
  (ahead / on-track / behind with the required daily pace) + recommendations.
- **Scheduler Engine** — persistent, timezone-aware jobs (interval / daily /
  weekly / cron / once), `run_due` execution with recovery and audit logging, and
  a background loop; seeds the OS jobs (morning briefing, evening review, hourly
  accounting refresh, memory maintenance).
- **Email Intelligence** — categorize, extract tasks/deadlines, detect meetings/
  invoices, prioritize, draft replies, inbox briefing.
- **Calendar Intelligence** — conflict detection, free/focus blocks, task
  time-blocking, travel buffers, meeting prep, daily plan.
- **Chief of Staff** — daily briefing (priorities, deadlines, risks,
  opportunities, energy allocation, recommended actions, confidence), evening
  review, and a **memory-driven planner** ("CPA in 45 days" → required pace →
  scheduled focus blocks + priority bumps).
- **Google + Outlook integrations** — real OAuth + REST clients (network-guarded);
  Gmail/Graph responses normalize to one shape so the intelligence engines are
  provider-agnostic (normalization + OAuth construction fixture-tested).
- **HUD**: a new **Chief of Staff** view (Briefing · Plan · Tasks · Goals ·
  Evening) plus Email Intelligence wired into the inbox; brain tools
  `chief_of_staff_briefing`, `plan_my_day`, `add_priority_task`,
  `prioritized_tasks`, `track_goal`, `goals_status`.

### Phase 6 progress (accounting platform)

A real double-entry accounting platform (`backend/accounting_platform/`) — **159
backend tests**, no network needed:

- **General Ledger** — balanced journal entries (debits = credits enforced),
  posting with **period controls**, account balances by normal-balance sign,
  trial balance, account ledgers, and reversing entries; **immutable audit trail**
  on every action (old → new, user, timestamp).
- **Chart of Accounts** — asset/liability/equity/revenue/expense with subaccounts,
  inactive flags, and firm **templates** (small business / professional / consulting
  / tax firm).
- **AP & AR** — vendors/customers, bills/invoices, payments, **aging schedules**,
  1099 tracking, cash-requirements forecast — each posts a real JE so AP/AR tie to
  the GL and statements.
- **Fixed Assets** — straight-line / double-declining / units-of-production
  depreciation, schedules, and GL-posting.
- **Bank Reconciliation** — CSV + OFX/QFX import, auto-matching to posted cash
  lines, reconciliation report with outstanding/unmatched items.
- **Financial Statements** — Balance Sheet that satisfies **A = L + E + Net
  Income**, Income Statement, **direct-method Cash Flow** that reconciles to the
  cash change, comparative statements.
- **Clients / Document Center** — engagements & deadlines; tagged, versioned,
  linkable documents (OCR-ready).
- **HUD**: a new **Ledger / Books** view (Dashboard · Statements · Journal · AR/AP ·
  Audit); brain tools `post_journal_entry`, `financial_statement`,
  `accounting_dashboard`. The Phase-1/4 accounting *research* (ASC/memo/briefing)
  remains alongside the new transactional platform.

### Phase 7 progress (document intelligence + tax/advisory workbench)

A professional tax & advisory workbench — **181 backend tests**:

- **Document Intelligence** — real text extraction from **PDF (text layer),
  Excel, Word, email, CSV**, a **classifier** (invoice/W-2/1099/K-1/bank
  statement/contract/tax return/financial statement/memo/workpaper/correspondence)
  with confidence, **field extraction** per type, validation, and a linked
  extraction store. **OCR honesty:** Tesseract image OCR is real but
  *availability-gated* — when the binary is absent it reports unavailable and
  raises rather than fabricating text.
- **Tax Research Engine** — citable authority KB (IRC/Treasury Regs/rulings/cases),
  **authority hierarchy**, risk, planning, and a tax-memo generator; plus a
  **Client Tax Organizer** (profiles, document requests, missing-doc tracking).
- **Workpaper Generator** — lead/trial-balance/depreciation/reconciliation/
  book-to-tax workpapers from the live books, cross-referenced + versioned.
- **Financial Statement Analysis** + **Due Diligence Engine** — ratios, cash-flow
  & earnings quality, concentration, working capital, risk flags.
- **Global Search** across documents, accounting records, tax research, clients.
- **5 new agents** (Tax Research, Document, Workpaper, Due Diligence, Advisory) and
  a **Workbench** HUD view; brain tools `process_document`, `tax_research`,
  `tax_memo`, `generate_workpaper`, `financial_analysis`, `due_diligence`,
  `global_search`.

### Phase 8 progress (execution / automation operating system)

HELIOS turns intelligence into *approved* action — **196 backend tests**:

- **Approval + Execution engine** — every action carries a **risk tier**, affected
  records/accounts/documents, confidence, and a full audit trail. Tier 1 may
  auto-execute; Tier 2/3 require human approval; **Tier 4 (broker/tax-filing/
  external) never auto-executes, needs explicit confirm, and only PREPARES** — a
  human performs the external act. Executed accounting actions are **reversible**
  (`rollback` reverses the GL entry); failures are recorded and retryable.
- **Document → Accounting automation** — a processed invoice/receipt becomes a
  *draft* AP bill or journal entry awaiting approval; on approve, it posts to the GL.
- **Month-End Close System** — checklist (JEs/accruals/prepaids/depreciation/
  reconciliations/review/closing/statements), progress, and a close package
  (TB + BS + IS + CF) from the live books.
- **Outcome Tracking + Learning** — records recommendations and outcomes, scores
  accuracy and per-agent performance, and suggests confidence calibration.
- **Operations dashboards** (tax season, firm ops, portfolio ops) + an **AI
  workflow builder** (month-end close workflow + execution plan with dependencies,
  approval gates, and deadlines).
- **HUD**: an **Operations** view (Approvals · Month-End Close · Outcomes). The
  brain may *propose* and *view* the queue (`approval_queue`,
  `process_document_to_books`, `month_end_close_status`, `outcome_metrics`,
  `build_close_workflow`); **approve/execute remain human actions** in the UI.

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
| Accounting platform | GL/AP/AR/statements… | ✅ | Real double-entry GL, COA templates, AP/AR (posted to GL), fixed assets, bank rec, BS/IS/CF, audit trail, dashboard |
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
