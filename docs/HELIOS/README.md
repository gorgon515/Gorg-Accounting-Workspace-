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
| **Multi-agent orchestration layer** | `assistant/src/main/services/agents.js` | ✅ working — 11-agent roster, local router, system-prompt team framing, `which_agent` tool, Agent Activity panel |
| **Language Immersion Center** | `assistant/src/main/services/language.js` + IPC/preload/UI | ✅ working — 7 languages, shared SRS, daily missions, CEFR pathway, roleplay seeds |

Both are wired into the registry, exposed over IPC, surfaced in the UI, and
covered by logic tests (router 11/11; full language lifecycle).

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
| Multi-agent system | 11 agents + orchestration | ✅ | `agents.js` roster + router + team prompt |
| Memory: short/long/project/etc. | ChromaDB + Postgres | 🟡 | Durable JSON memory today; vector + relational designed |
| N8N automation center | embedded N8N | ⬜ | Designed (Automation Agent stubs the seam) |
| Language Immersion | 7 langs, full pathway | ✅ | `language.js` — SRS, missions, CEFR, roleplay |
| Accounting platform | GL/AP/AR/statements… | 🟡 | Ledger + invoices + P&L today; full GL designed |
| Accounting Intelligence Center | FASB/SEC/IRS monitoring | ⬜ | Designed (Tax/Accounting agents) |
| CPA Study Center | qbank + simulations | 🟡 | Progress tracker + flashcards today; qbank designed |
| Market intelligence | fundamentals→options | 🟡 | Quotes/news/technicals today; full factor stack designed |
| Quant research | backtests/Monte Carlo | ⬜ | Designed (Python sidecar) |
| Trade recommendations | gated, with R/R | ✅ | Strategy engine + approval gate; never auto-executes |
| Brokerage integration | IBKR/Alpaca/… | 🟡 | Alpaca paper/live connected; others designed |
| Email | Gmail/Outlook | 🟡 | Gmail read today; drafting/Outlook designed |
| Calendar | Google/Outlook | 🟡 | Google read today; scheduling/Outlook designed |
| Knowledge graph | visual graph | ⬜ | Designed |
| Security: encryption/vault/RBAC/audit | AES-256, audit logs | 🟡 | OS-keychain secrets + CSP today; vault/RBAC/audit designed |
| Front end | React/TS/Tailwind/Framer | ⬜ | Vanilla HTML/CSS/JS today; React/TS migration designed |
| Backend | Python/FastAPI | ⬜ | Electron-main Node services today; FastAPI sidecar designed |

## Reading order

If you are implementing: read [01](./01-system-architecture.md) →
[02](./02-data-architecture.md) → [04](./04-ux-and-structure.md) →
[05](./05-roadmap.md). If you are evaluating: this README + the status matrix is
enough.
