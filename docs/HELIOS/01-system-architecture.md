# 01 — System Architecture

Covers deliverables **1 (software), 3 (agent), 4 (memory), 5 (N8N), 6 (frontend),
7 (backend), 11 (security)**.

---

## 1. Software architecture (the big picture)

HELIOS is a **local-first desktop application**. Everything required for core
functionality runs on the user's machine; the network is used only for explicitly
opted-in connectors (market data, Gmail/Calendar, brokerage).

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ELECTRON SHELL                                                           │
│                                                                           │
│  ┌────────────────────────┐        IPC (contextBridge)   ┌─────────────┐ │
│  │  Renderer (Chromium)    │ ◄──────────────────────────► │ Main (Node) │ │
│  │  React + TS + Tailwind  │   window.helios.* channels    │  process    │ │
│  │  Framer Motion HUD      │                               └──────┬──────┘ │
│  │  - Command Center        │                                      │        │
│  │  - Voice UI              │                                      │        │
│  │  - Domain panels         │                            Orchestration layer│
│  └────────────────────────┘                              (agents + skills) │
│                                                                  │          │
│        ┌─────────────────────────────────────────────────────────┘         │
│        ▼                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Brain        │   │ Skill        │   │ Memory       │   │ Connectors   │ │
│  │ (tool loop)  │   │ registry     │   │ services     │   │ Gmail/Cal/   │ │
│  │ local|claude │   │ (12 skills)  │   │              │   │ broker/N8N   │ │
│  └──────┬───────┘   └──────────────┘   └──────┬───────┘   └──────────────┘ │
│         │                                      │                            │
└─────────┼──────────────────────────────────────┼───────────────────────────┘
          │ HTTP (localhost)                      │ drivers
          ▼                                       ▼
   ┌──────────────────────────┐         ┌──────────────────────────────┐
   │ Local model servers      │         │ Local data plane             │
   │ • Ollama   :11434        │         │ • PostgreSQL  :5432 (relational)│
   │ • llama.cpp/LM Studio    │         │ • ChromaDB    (vector/memory) │
   │ • Piper/Coqui TTS        │         │ • JSON store  (today's seam)  │
   │ • Whisper STT (in-proc)  │         │ • Encrypted vault (OS keychain)│
   └──────────────────────────┘         └──────────────────────────────┘
          ▲
          │ HTTP (localhost :8420)
   ┌──────┴───────────────────────────────────────────────┐
   │ HELIOS Compute Sidecar (Python / FastAPI)             │
   │ • Quant: factor models, backtests, Monte Carlo (numpy │
   │   / pandas / scipy)                                    │
   │ • Heavy NLP / embeddings, document parsing            │
   │ • N8N control + accounting-intelligence crawlers      │
   └───────────────────────────────────────────────────────┘
```

### Why this shape

- **Electron main is the trust boundary.** All tools, secrets, file access, and
  network egress live in the main process. The renderer is sandboxed
  (`contextIsolation: true`, `nodeIntegration: false`) and can only call the
  typed `window.helios.*` bridge (today `window.aria` in `preload.js`).
- **The brain can only do what skills expose.** It runs a manual tool-use loop
  (not an autonomous agent runner) so human-approval gates sit on the critical
  path for money actions. See `assistant/src/main/brain.js`.
- **Compute that doesn't belong in Node goes to a Python sidecar.** Quant math,
  embeddings, and document parsing are Python's strength. The sidecar is a
  localhost FastAPI process the main process spawns and supervises; it is
  optional and the app degrades gracefully without it.
- **Two data planes.** Relational truth (PostgreSQL) for the accounting/trading
  ledgers; a vector store (ChromaDB) for semantic memory and research. Today
  both are stood in for by a single JSON document store (`store.js`), whose
  header comment already names the upgrade path.

### Process lifecycle & performance

- Cold start budget **< 10 s**: render the shell immediately, then hydrate panels
  asynchronously (the renderer already does this — panels load independently of
  the brain). Model servers are detected, not blocked on.
- The sidecar and model servers are **lazy**: started on first use, health-checked
  with short timeouts (`brain.localReady()` uses a 1.5 s `AbortSignal.timeout`).
- Heavy jobs (backtests, crawls) run in the sidecar / worker threads and stream
  progress over IPC, never blocking the UI thread.

---

## 3. Agent architecture

HELIOS presents as a **team of specialists coordinated by a Chief of Staff**,
even though a single brain executes the loop. The orchestration layer
(`assistant/src/main/services/agents.js`, shipped with this blueprint) makes this
real:

```
                         ┌───────────────────────┐
   user (text/voice) ──► │  Chief of Staff        │  coordinates, briefs,
                         │  (orchestration)       │  routes, synthesizes
                         └───────────┬───────────┘
            local router (keyword-scored, deterministic, no model)
        ┌──────────┬──────────┬──────────┬──────────┬──────────┬─────────┐
        ▼          ▼          ▼          ▼          ▼          ▼         ▼
   Accounting   Tax      Research    Quant     Trading   Language   Knowledge
     Agent     Agent      Agent      Agent      Agent     Coach      Agent
        │          │          │          │          │          │         │
        └──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘
                     each agent owns a set of SKILLS (tool groups)
                     Email + Calendar + Automation agents also present
```

### The contract

Every skill module exports `{ name, systemPromptFragment, tools, handlers, api }`
and is registered in `services/skills.js`. An **agent** is a named grouping of
skills plus a role description and router keywords:

```js
{ key: 'quant', name: 'Quant Agent',
  role: 'Quantitative market analysis…',
  skills: ['analysis', 'strategy'],
  keywords: ['analyze','rsi','macd','backtest','factor', …] }
```

- **Routing** (`agents.route(text)`) is a fast, local, deterministic classifier —
  it never needs a model. Used to label which specialist handled a turn (Agent
  Activity panel) and to introspect via the `which_agent` tool. Tested: 11/11
  representative cases.
- **Orchestration in the prompt** (`agents.promptBlock()`) tells the single brain
  to *adopt the mindset* of the owning specialist, coordinate across agents for
  multi-part requests, and never narrate handoffs. Injected into
  `skills.systemPrompt()`.
- **Future per-agent model routing**: the agent definition is the natural place
  to pin a model (e.g. a small fast model for routing/email, a strong model for
  quant/tax memos). The seam exists; the policy is a roadmap item.

### The 11 agents

Chief of Staff · Accounting · Tax · Research · Quant · Trading · Language Coach ·
Email · Calendar · Automation · Knowledge. Mapping to skills and live tool counts
is computed by `agents.roster(skills)` and surfaced in the **Agents** panel
(online / idle / planned).

---

## 4. Memory architecture

Six memory types over two stores, with a single retrieval API.

| Type | Holds | Store | Today |
|---|---|---|---|
| **Short-term** | the active conversation | in-process history | ✅ brain history |
| **Long-term** | durable user facts/preferences | Postgres + Chroma | 🟡 `memory.js` JSON |
| **Project** | ongoing projects & their state | Postgres | ⬜ |
| **Relationship** | people, orgs, interactions | Postgres + graph | ⬜ |
| **Knowledge** | learned facts, research, docs | Chroma (vectors) | ⬜ |
| **Behavioral** | preferences/habits learned over time | Postgres | 🟡 implicit via facts |

```
 write path:  fact/event ──► classifier ──► {relational row, vector embedding}
 read  path:  query ──► hybrid retrieve (BM25/SQL + vector kNN)
                     ──► rerank ──► inject top-k into system prompt
```

- **Today**: `memory.js` stores capped, de-duplicated facts as JSON and injects
  them into every system prompt (`promptBlock()`), giving real cross-session
  recall with zero infra. This is the working short/long-term layer.
- **Designed scale-up**: facts and documents are embedded (local embedder via
  Ollama, e.g. `nomic-embed-text`) into **ChromaDB** collections per memory type;
  structured entities (projects, people) live in **PostgreSQL**. Retrieval is
  hybrid (SQL/keyword + vector kNN) and reranked before injection.
- **User controls** (spec requirement): search, edit, delete, and visualize.
  `recall`/`forget` tools exist today; a Memory panel + the Knowledge Graph
  ([04](./04-ux-and-structure.md)) provide visualization.
- **Privacy**: memory never leaves the device. Embeddings are computed locally.

---

## 5. N8N automation architecture

The **Automation Agent** turns natural language into N8N workflows and manages
their lifecycle.

```
 "download invoice attachments from Gmail and file them by vendor"
        │
        ▼  Automation Agent (LLM → N8N workflow JSON)
   ┌─────────────────────┐   REST/API key   ┌──────────────────────────┐
   │ HELIOS main process  │ ───────────────► │ N8N (local, :5678)        │
   │ workflow builder     │ ◄─────────────── │ embedded via <webview>    │
   └─────────────────────┘   webhooks/exec   │ editor + execution engine │
                                             └──────────────────────────┘
```

- **Embedding**: N8N runs as a local service (Docker or the bundled binary) and
  is shown inside HELIOS in a sandboxed `<webview>` for full create/modify/debug,
  matching the "fully visible N8N environment" requirement.
- **NL → workflow**: the agent has tools `create_workflow(spec)`,
  `update_workflow(id, patch)`, `execute_workflow(id, input)`,
  `list_workflows()`, `get_executions(id)`. It generates N8N's node-graph JSON and
  posts it through the N8N REST API; HELIOS keeps a registry mapping intents →
  workflow ids.
- **Credentials**: N8N credentials are provisioned from the HELIOS vault, never
  hand-typed twice. Execution that touches money/email respects the same approval
  gates as the agents.
- **Status today**: the Automation Agent exists in the roster as `planned`; the
  N8N service + tools are the next automation milestone
  ([05-roadmap](./05-roadmap.md), Phase 2).

---

## 6. Frontend architecture

**Target stack**: Electron + React + TypeScript + TailwindCSS + Framer Motion,
"Iron Man HUD" aesthetic (dark, glassmorphism, animated, premium).

```
renderer/
  app/                 React app root, routing (panel layout)
  hud/                 shell: top status bar, command palette, voice orb
  panels/              one component per Command Center widget
    BriefingPanel.tsx  CalendarPanel.tsx  MarketPanel.tsx  AccountingPanel.tsx
    LanguagePanel.tsx  AgentsPanel.tsx    MemoryPanel.tsx  KnowledgeGraph.tsx …
  voice/               wake word, STT capture, TTS playback, barge-in
  state/               typed stores (zustand/redux), IPC hooks
  ipc/                 typed window.helios.* client (mirrors preload)
  theme/               Tailwind tokens (obsidian/charcoal/gold) + motion presets
```

- **HUD design system**: tokens already exist in `renderer/styles.css`
  (`--obsidian #0E0E10`, `--charcoal`, `--gold #B8976A`, hairline borders,
  JetBrains Mono for numbers). The React migration carries these tokens into
  Tailwind config so the look is preserved, then layers glassmorphism
  (`backdrop-blur`, translucent panels) and Framer Motion transitions
  (respecting `prefers-reduced-motion`).
- **Security in the renderer**: strict CSP (`default-src 'self'`, no remote
  scripts), `contextIsolation`, no Node. All privilege is behind the bridge.
- **Today**: the renderer is **vanilla HTML/CSS/JS** (`renderer/index.html`,
  `renderer.js`, `styles.css`) — fast and dependency-free, ideal for the vertical
  slice. The React/TS migration is a roadmap item; the panel boundaries and IPC
  surface are already factored to make it mechanical.
- **Real-time updates**: main→renderer push channels (e.g. `alert:triggered`
  today) carry agent activity, alert fires, and job progress; panels also poll on
  staggered intervals (trades 15 s, watchlist 60 s).

---

## 7. Backend architecture

HELIOS has **two backend tiers**, both local:

### Tier A — Electron main (Node) — *the orchestrator*
The system of record for app behavior: brain, skill registry, agents, connectors,
IPC, vault, lifecycle. This is where the working code lives today
(`assistant/src/main/`). It is intentionally thin and orchestration-focused.

### Tier B — Python / FastAPI compute sidecar — *the heavy lifting*
A localhost service (`:8420`) the main process spawns. It owns work that is
awkward or slow in Node:

```
POST /quant/backtest        run a strategy over history → equity curve, stats
POST /quant/factors         compute factor exposures for a universe
POST /quant/montecarlo      portfolio simulation → distribution of outcomes
POST /quant/optimize        portfolio construction (mean-variance / risk parity)
POST /nlp/embed             local embeddings for memory/RAG
POST /docs/parse            PDF/Excel/CSV → structured rows (statements, imports)
POST /intel/crawl           accounting-intelligence source crawl → normalized items
GET  /health                liveness for supervision
```

- **Contract**: JSON in/out over localhost only; bound to `127.0.0.1`, no auth
  needed because it is unreachable off-box, but it still validates inputs.
- **Libraries**: `fastapi`, `uvicorn`, `pandas`, `numpy`, `scipy`, `pydantic`;
  optional `faster-whisper`, `chromadb`, `piper-tts`.
- **Degradation**: if the sidecar is absent, quant/research panels show "compute
  offline" and the rest of HELIOS is unaffected — same philosophy as the brain.
- **Status today**: not yet present. Node services cover the current pillars;
  the sidecar lands when quant/backtesting and document import arrive (Phase 2).

The API surface (IPC + FastAPI + REST connectors) is specified in
[02-data-architecture](./02-data-architecture.md).

---

## 11. Security architecture

Local-first is the headline security property: **your data never has to leave
your machine.**

| Control | Design | Today |
|---|---|---|
| **Local-first / data ownership** | all core features offline; data on device | ✅ |
| **Renderer sandbox** | `contextIsolation`, no `nodeIntegration`, strict CSP | ✅ |
| **Secret storage** | OS keychain via Electron `safeStorage` (AES-class, OS-managed keys) | ✅ `store.setSecret` |
| **Credential vault** | dedicated encrypted vault, secrets never returned to renderer | 🟡 secrets layer exists; unified vault designed |
| **AES-256 at rest** | encrypt the data store with a key sealed by the OS keychain / passphrase | 🟡 secrets encrypted; full-DB encryption designed |
| **Role-based permissions** | per-capability scopes (read email vs send, propose vs execute) | 🟡 approval gate is the first scope; RBAC designed |
| **Audit logging** | append-only log of tool calls, money actions, connector access | ⬜ designed (every `runTool` is a natural hook) |
| **Approval gates** | money actions only *proposed* by AI; user approves to execute | ✅ trading approval gate |
| **Backup / disaster recovery** | encrypted local snapshots + export/import | ⬜ designed |
| **Network egress** | only opted-in connectors; market-data host allowlist in web sessions | ✅ |

### Principles

1. **The AI cannot spend money or send irreversibly without you.** The brain has
   no execute tool — only `propose_trade`; fills require an explicit Approve
   click. Live brokerage is flagged red and double-confirmed. This pattern
   generalizes to email send, ledger posting, and workflow execution.
2. **Secrets are write-only from the UI's perspective.** Broker secrets, OAuth
   tokens, and API keys are encrypted with the OS keychain and never sent back to
   the renderer (`store.js`, `broker.js`).
3. **Every tool call is auditable.** `brain.runTool` already returns
   `{ok, error}` per call — the designed audit log taps exactly here, recording
   actor (agent), tool, inputs (redacted), result, and timestamp to an append-only
   store.
4. **Least privilege connectors.** Gmail/Calendar use read-only scopes today;
   write scopes (drafting, scheduling) are added per-capability and gated.

See [02-data-architecture](./02-data-architecture.md) for the vault schema and
audit-log table, and [06-deployment](./06-deployment.md) for hardening at install
time.
