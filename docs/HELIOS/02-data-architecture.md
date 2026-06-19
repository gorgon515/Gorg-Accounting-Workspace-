# 02 — Data & API Architecture

Covers deliverables **2 (database architecture), 14 (database schema), 15 (API
specifications)**.

---

## 2. Database architecture

HELIOS uses **three tiers of persistence**, chosen so the app is useful with zero
infrastructure and scales without rewrites.

```
┌───────────────────────────────────────────────────────────────────┐
│ Tier 0 — JSON document store  (today; zero-config)                  │
│   store.js → <userData>/aria-store.json   + OS-keychain secrets     │
│   The seam: get/set/setSecret/getSecret. Swappable behind one file. │
├───────────────────────────────────────────────────────────────────┤
│ Tier 1 — PostgreSQL  (relational truth)                             │
│   accounting ledger, trading, tasks, projects, people, audit log    │
│   embedded/managed locally (e.g. via an embedded PG or Docker)      │
├───────────────────────────────────────────────────────────────────┤
│ Tier 2 — ChromaDB  (vectors / semantic memory)                      │
│   knowledge memory, research corpus, document chunks, RAG           │
│   local persistent collections; embeddings computed on-device       │
└───────────────────────────────────────────────────────────────────┘
```

### Migration path (no big-bang rewrite)

`store.js` is the single seam. Its own header says *"swap for SQLite when modules
grow."* The plan:

1. **Now**: JSON store. One file, atomic writes, encrypted secrets.
2. **Step 1**: introduce a `Repository` interface (`get/set/query/transaction`)
   with a JSON impl and a PostgreSQL impl. Skills depend on the interface, not the
   file.
3. **Step 2**: move high-volume / relational data (ledger, trades, audit) to
   Postgres; keep small settings in JSON.
4. **Step 3**: add ChromaDB for memory/knowledge; the memory service writes to
   both relational (entity rows) and vector (embeddings) stores.

Each step is shippable and reversible. Domain modules (`accounting.js`, etc.)
already isolate their storage keys, so the blast radius is contained.

---

## 14. Database schema

PostgreSQL DDL for the relational tier. (Today these are JSON arrays under the
keys named in each module; the columns below are the normalized target.)

### Core / identity

```sql
CREATE TABLE app_user (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Encrypted credential vault. ciphertext only; keys sealed by the OS keychain.
CREATE TABLE vault_secret (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ref         TEXT UNIQUE NOT NULL,         -- e.g. 'alpaca.secret', 'google.refresh'
  ciphertext  BYTEA NOT NULL,
  enc         BOOLEAN NOT NULL DEFAULT true, -- false => obfuscation-only fallback
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only audit log. Every tool call / money action / connector access.
CREATE TABLE audit_event (
  id         BIGSERIAL PRIMARY KEY,
  ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
  agent      TEXT,                          -- 'trading', 'email', …
  tool       TEXT,                          -- tool name invoked
  input_redacted JSONB,                     -- inputs with secrets stripped
  ok         BOOLEAN NOT NULL,
  error      TEXT,
  approved_by TEXT                          -- set for gated actions
);
```

### Accounting (general ledger model)

```sql
CREATE TABLE coa_account (                  -- chart of accounts
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code      TEXT UNIQUE NOT NULL,           -- '1000', '4000', …
  name      TEXT NOT NULL,
  type      TEXT NOT NULL CHECK (type IN ('asset','liability','equity','income','expense')),
  parent_id UUID REFERENCES coa_account(id)
);

CREATE TABLE journal_entry (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_date DATE NOT NULL,
  memo       TEXT,
  source     TEXT,                          -- 'manual','invoice','import:quickbooks'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Double-entry lines. SUM(debit) must equal SUM(credit) per entry (enforced in app).
CREATE TABLE journal_line (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id    UUID NOT NULL REFERENCES journal_entry(id) ON DELETE CASCADE,
  account_id  UUID NOT NULL REFERENCES coa_account(id),
  debit       NUMERIC(18,2) NOT NULL DEFAULT 0,
  credit      NUMERIC(18,2) NOT NULL DEFAULT 0,
  CHECK (debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0))
);

CREATE TABLE client (
  id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name  TEXT NOT NULL,
  email TEXT, notes TEXT
);

CREATE TABLE invoice (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id  UUID REFERENCES client(id),
  number     TEXT, amount NUMERIC(18,2) NOT NULL,
  issued_on  DATE NOT NULL, due_on DATE,
  status     TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','paid','void')),
  paid_on    DATE
);

CREATE TABLE fixed_asset (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT NOT NULL, cost NUMERIC(18,2) NOT NULL,
  acquired_on  DATE NOT NULL, useful_life_months INT,
  method       TEXT DEFAULT 'straight_line', salvage NUMERIC(18,2) DEFAULT 0
);
```

### Trading / markets

```sql
CREATE TABLE position (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol    TEXT NOT NULL, qty NUMERIC(18,4) NOT NULL,
  avg_price NUMERIC(18,4) NOT NULL, account TEXT NOT NULL DEFAULT 'paper'
);

CREATE TABLE trade_order (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol      TEXT NOT NULL, side TEXT NOT NULL CHECK (side IN ('buy','sell')),
  qty         NUMERIC(18,4) NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending'     -- pending|approved|filled|rejected
              CHECK (status IN ('pending','approved','filled','rejected')),
  proposed_by TEXT,                                -- agent or 'user'
  proposed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  filled_price NUMERIC(18,4), filled_at TIMESTAMPTZ,
  account     TEXT NOT NULL DEFAULT 'paper'
);

CREATE TABLE watchlist_item ( symbol TEXT PRIMARY KEY );
CREATE TABLE price_alert (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL, direction TEXT CHECK (direction IN ('above','below')),
  price NUMERIC(18,4) NOT NULL, triggered_at TIMESTAMPTZ
);
```

### Productivity / projects / relationships / knowledge graph

```sql
CREATE TABLE task (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL, due DATE, done BOOLEAN NOT NULL DEFAULT false,
  project_id UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE project (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL, status TEXT DEFAULT 'active', summary TEXT
);
CREATE TABLE person (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL, org TEXT, email TEXT, last_interaction DATE, notes TEXT
);

-- Knowledge graph: typed nodes + edges connecting projects/people/topics/companies.
CREATE TABLE kg_node (
  id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind  TEXT NOT NULL,        -- project|person|company|topic|task|note|account
  ref_id UUID,                -- optional link to the concrete row
  label TEXT NOT NULL
);
CREATE TABLE kg_edge (
  src UUID NOT NULL REFERENCES kg_node(id) ON DELETE CASCADE,
  dst UUID NOT NULL REFERENCES kg_node(id) ON DELETE CASCADE,
  rel TEXT NOT NULL,          -- 'works_on','mentions','owns','relates_to'
  weight REAL DEFAULT 1.0,
  PRIMARY KEY (src, dst, rel)
);
```

### Learning (study + language)

```sql
CREATE TABLE flashcard (                     -- shared by Study + Language (SM-2)
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject TEXT NOT NULL,                      -- 'russian','spanish','cpa-far', …
  front TEXT NOT NULL, back TEXT NOT NULL,
  ease REAL NOT NULL DEFAULT 2.5, interval INT NOT NULL DEFAULT 0,
  reps INT NOT NULL DEFAULT 0, due DATE NOT NULL, last_review DATE
);
CREATE TABLE study_session (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject TEXT NOT NULL, minutes INT NOT NULL, topic TEXT, day DATE NOT NULL
);
CREATE TABLE language_profile (
  language TEXT PRIMARY KEY, level TEXT NOT NULL DEFAULT 'A1', started_at TIMESTAMPTZ
);
CREATE TABLE language_mission (
  id TEXT, language TEXT, day DATE, kind TEXT, text TEXT, done BOOLEAN DEFAULT false,
  PRIMARY KEY (language, day, id)
);
CREATE TABLE cpa_progress (
  section TEXT PRIMARY KEY,                    -- AUD|FAR|REG|BAR|ISC|TCP
  progress INT NOT NULL DEFAULT 0, status TEXT, exam_date DATE
);
```

### Memory & accounting-intelligence

```sql
CREATE TABLE memory_fact (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fact TEXT NOT NULL, category TEXT, kind TEXT DEFAULT 'long_term',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- vector twin lives in ChromaDB collection 'memory' (id-linked)

CREATE TABLE intel_item (                     -- Accounting Intelligence Center
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,                        -- FASB|SEC|IRS|PCAOB|AICPA|firm
  doc_type TEXT,                               -- ASU|exposure_draft|notice|ruling…
  title TEXT NOT NULL, url TEXT, published_on DATE,
  effective_on DATE, summary TEXT, seen BOOLEAN DEFAULT false
);
```

### ChromaDB collections (vector tier)

| Collection | Documents | Metadata |
|---|---|---|
| `memory` | user facts/notes | `{kind, category, created_at, fact_id}` |
| `knowledge` | learned info, web/research snippets | `{source, url, topic}` |
| `documents` | parsed PDF/Excel chunks | `{doc_id, page, client_id}` |
| `accounting_intel` | crawled standard-setter text | `{source, doc_type, effective_on}` |

Embeddings are computed locally (e.g. Ollama `nomic-embed-text`); retrieval is
top-k cosine, optionally hybridized with the relational keyword search.

---

## 15. API specifications

Three API surfaces. **(A)** the renderer↔main IPC bridge (the live one), **(B)**
the Python sidecar FastAPI, **(C)** outbound connectors.

### A. IPC bridge — `window.helios.*` (today `window.aria.*`)

Defined in `preload.js`, handled in `ipc.js`. Channels are `domain:action`,
invoked via `ipcRenderer.invoke` and returning JSON. Selected surface (✅ = live):

```
config()                         → { hasBrain, brain, model, wakeWord, stt }   ✅
ask(text, history)               → { ok, text, toolEvents, history }           ✅
stt.transcribe(payload)          → { text }                                    ✅

stocks.quote|quotes|search|news|history|watchlist*(…)                          ✅
trading.portfolio|pending|propose|approve|reject|orders|reset(…)               ✅
accounting.summary|txns|addTxn|invoices|addInvoice|markPaid(…)                 ✅
study.stats|due|review|addVocab|notes|cpa|setCpa(…)                            ✅
productivity.tasks|addTask|completeTask|briefing(…)                            ✅
google.status|connect|agenda|inbox(…)                                          ✅
broker.status|connect|disconnect(…)                                            ✅
strategy.idea|scan(…)                                                          ✅

language.languages|curriculum|profile|setLanguage|progress|missions|           ✅ (new)
         completeMission|addVocab|due(…)
agents.roster|route(…)                                                         ✅ (new)
```

**Contract conventions**: every handler returns a plain JSON-serializable object
or throws an `Error` whose `.message` is surfaced to the UI; never returns secrets
to the renderer; long operations stream progress via main→renderer events
(`channel:progress`).

Example (the new Language surface):

```ts
// renderer
const { missions } = await window.helios.language.missions('spanish');
await window.helios.language.completeMission({ id: 'm0', language: 'spanish' });
const p = await window.helios.language.progress('spanish');
// p => { name, flag, words, dueNow, streakDays, selfLevel, estimatedLevel, … }
```

### B. Python sidecar — FastAPI (localhost :8420)

```
GET  /health                          → { status: "ok", version }
POST /quant/backtest    {strategy, symbols, range}      → {equity, cagr, sharpe, maxDD, trades}
POST /quant/factors     {symbols, factors[]}            → {exposures}
POST /quant/montecarlo  {weights, horizon, n}           → {p5, p50, p95, paths?}
POST /quant/optimize    {symbols, objective}            → {weights, expRet, expVol}
POST /nlp/embed         {texts[]}                        → {vectors[]}
POST /docs/parse        {path, kind}                     → {rows[] | statements}
POST /intel/crawl       {sources[]}                      → {items[]}     (→ intel_item)
```

All endpoints: JSON body validated by Pydantic, bound to `127.0.0.1`, 4xx on bad
input, 503 if a dependency (e.g. data feed) is unavailable. The main process is
the only caller.

### C. Outbound connectors (opted-in)

| Connector | Protocol | Scope | Today |
|---|---|---|---|
| Market data | HTTPS (Yahoo finance endpoints) | read quotes/history/news | ✅ |
| Google | OAuth 2.0 (desktop), Gmail + Calendar | read (write designed) | ✅ |
| Alpaca | REST, key/secret | paper/live portfolio + orders (gated) | ✅ |
| Ollama | HTTP `:11434` | local chat/embeddings | ✅ |
| N8N | REST `:5678`, API key | workflow CRUD + exec | ⬜ |
| Outlook / Graph | OAuth 2.0 | email + calendar | ⬜ |

Connector credentials are provisioned from the vault; egress is limited to the
hosts each connector declares (and, in Claude Code web sessions, the market-data
host must be allowlisted — see `assistant/README.md`).
