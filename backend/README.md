# HELIOS Intelligence Sidecar (Python / FastAPI)

The **compute tier** of HELIOS: the **Quant Research Engine** and **Accounting
Intelligence Engine**, served on localhost for the Electron app to call. It is
the Phase-2 backend described in [`../docs/HELIOS/01-system-architecture.md`](../docs/HELIOS/01-system-architecture.md)
(§7) and [`02-data-architecture.md`](../docs/HELIOS/02-data-architecture.md) (§15B).

Design principles:

- **Pure-Python service layer.** All the math (technicals, factors, risk, ASC
  research) lives in `app/services/` with **no third-party dependencies**, so it
  is unit-testable under the standard library and runs with a minimal install.
- **FastAPI is just the serving layer.** Routers validate input (Pydantic) and
  call the service layer. Bound to `127.0.0.1` only — never reachable off-box.
- **Network is optional.** Every quant endpoint accepts an explicit price series
  as well as a symbol, so the engine is fully usable offline; data-provider
  failures return `503` and the Electron app degrades gracefully.

## Layout

```
backend/
  app/
    main.py              FastAPI app (CORS localhost, error handlers)
    config.py            host/port/version (env-overridable)
    models.py            Pydantic request schemas
    routers/             health, quant, markets, accounting
    services/            ← the engine (pure Python, dependency-free)
      technicals.py      SMA/EMA/RSI/MACD/Bollinger/momentum/volatility/drawdown
      factors.py         transparent value/quality/growth/momentum scoring
      risk.py            Sharpe/Sortino/beta/correlation/VaR + portfolio report
      market_data.py     provider abstraction + TTL cache + normalization (Yahoo)
      accounting_research.py  ASC knowledge base + technical-memo generator
  tests/                 unittest + FastAPI TestClient (35 tests)
  requirements.txt       runtime deps
  requirements-dev.txt   + pytest, httpx
```

## Run

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8420
```

In normal use you don't run this by hand — the Electron app autostarts and
supervises it (`assistant/src/main/services/sidecar.js`); set
`HELIOS_SIDECAR_AUTOSTART=false` to manage it yourself, or `HELIOS_SIDECAR_URL`
to point at an already-running instance.

## Test

```bash
# full suite (needs the venv: fastapi, pytest, httpx)
.venv/bin/python -m pytest -q

# service layer only — no dependencies required
python3 -m unittest discover -s tests -p 'test_*.py'
```

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | liveness (used by the supervisor) |
| POST | `/quant/analyze` | technicals + signals for a symbol or price series |
| POST | `/quant/factors` | value/quality/growth/momentum composite score |
| POST | `/quant/risk` | volatility, Sharpe/Sortino, drawdown, VaR, beta |
| POST | `/quant/portfolio` | concentration (HHI), sector exposure, blended risk |
| GET | `/markets/quote/{symbol}` | normalized quote (Yahoo) |
| GET | `/markets/history/{symbol}` | normalized close history |
| GET | `/accounting/topics` | ASC topics in the knowledge base |
| GET | `/accounting/asc/{topic}` | explain an ASC topic (e.g. `606`, `revenue`) |
| POST | `/accounting/memo` | technical memo (Issue/Facts/Guidance/Analysis/Conclusion/Disclosure/CPA) |
| GET | `/accounting/briefing` | daily accounting-intelligence briefing (`?refresh=true` to pull live) |
| GET/POST | `/accounting/intel`, `/accounting/intel/refresh` | stored developments feed; live collect |
| GET | `/accounting/graph` | FASB knowledge graph (`?asc=606` for a subgraph) |
| POST | `/accounting/checklist` | implementation checklist for an ASC topic |
| POST | `/accounting/memo/full` | full memo (Facts/Issue/Guidance/Analysis/Alternatives/Conclusion/References) |
| POST | `/quant/fundamentals` | ratios, growth, quality, peer comparison |
| POST | `/quant/signal` | research signal (bull/bear/risks/catalysts/confidence) |
| POST | `/market/briefing` | daily market briefing from symbols/quotes |
| GET/POST | `/n8n/status`, `/n8n/workflows`, `/n8n/generate` | N8N connectivity + AI workflow JSON |

Bad/insufficient input → `400`; provider/network failure → `503`.

## Phase 4 — intelligence engines

Three packages (run from `backend/`, on the test path):

```
accounting/                 Accounting Intelligence Engine
  collectors/               real FASB/SEC/PCAOB/IRS feed collectors (SEC-compliant UA,
                            network-guarded, env-overridable URLs: HELIOS_FEEDS_<SRC>)
  parsers/feeds.py          RSS + Atom parsing (stdlib XML) — unit-tested core
  schemas.py                normalized IntelItem + classifiers + ASC/ASU/effective-date extraction
  storage/db.py             SQLite store (dedup by stable id, historical tracking, queries)
  briefing/generator.py     daily briefing (summary/key changes/industries/CPA/actions/confidence)
  knowledge_graph.py        FASB graph: ASC ↔ ASU ↔ industry ↔ FS area ↔ disclosure ↔ audit ↔ tax
  research.py               implementation checklists + full technical memo + ASU summary
quant/                      Quant Research Engine
  technicals.py             ATR, relative strength, momentum/trend/volume scores (+ Phase-2 core)
  fundamentals.py           valuation/profitability/leverage ratios, growth, quality, peers
  signals.py                signal engine (facts/calculations/interpretations/forecasts separated)
  market_briefing.py        market overview, sector rotation, movers, opportunities
n8n/                        N8N Integration Layer
  client.py                 real REST client (list/run/create/monitor; network-guarded)
  generator.py              AI workflow generator → importable N8N JSON (accounting-briefing example)
```

**Network note.** Collectors hit the real standard-setter feeds with a fair-access
User-Agent and run live on a networked machine. In a restricted sandbox the feeds
are blocked, so the engine degrades gracefully (the briefing reports
`confidence: None` with the unreachable sources listed). The parsers are verified
against real-format fixtures; all offline logic (storage, dedup, briefing, graph,
research, quant, signals, market briefing, N8N generation) is fully unit-tested.

Configure live sources/keys via env: `HELIOS_FEEDS_FASB/SEC/IRS/PCAOB`,
`HELIOS_HTTP_UA`, `HELIOS_MARKET_PROVIDER` (+ `FMP_API_KEY` / `ALPHA_VANTAGE_KEY`),
`N8N_URL` / `N8N_API_KEY`, `HELIOS_INTEL_DB`.

## Phase 5 — personal chief of staff (operational layer)

```
tasks/engine.py        Task Intelligence: SQLite store, priority/deadline scoring,
                       recurrence, dependencies (blocking), auto-categorization, recommendations
goals/engine.py        Goal system: milestones, progress, deadline-aware forecasting, recommendations
scheduler/engine.py    persistent, timezone-aware jobs (interval/daily/weekly/cron/once),
                       run_due()+recovery+audit; background loop
email_intel/engine.py  categorize, extract tasks/deadlines, meeting/invoice detection,
                       priority scoring, reply drafting, inbox briefing
calendar_intel/engine.py conflicts, free/focus slots, time-blocking, travel buffers, meeting prep, daily plan
cos/                   Chief of Staff: daily_briefing, evening_review, memory-driven planner
integrations/          google.py + outlook.py (real OAuth + REST, network-guarded) and
                       schemas.py (Gmail/Graph → normalized Email/Event; fixture-tested)
```

Endpoints (`/tasks`, `/goals`, `/scheduler/*`, `/email/*`, `/calendar/plan`,
`/cos/daily-briefing`, `/cos/evening-review`, `/cos/plan`, `/cos/briefing/auto`,
`/cos/plan/auto`). The scheduler seeds default OS jobs (morning briefing, evening
review, hourly accounting refresh, memory maintenance) and `run_due` executes them
via a handler registry with audit logging.

**Network note (same as Phase 4).** Google/Outlook OAuth + REST are real and run
on a configured, networked machine (GOOGLE_CLIENT_ID/SECRET, OUTLOOK_*); the
sandbox can't reach them, so normalization + OAuth-URL/token construction are
verified against real-format fixtures, and all chief-of-staff logic (tasks, goals,
scheduler, email/calendar intelligence, briefing/review/planner) is fully tested.

## Phase 6 — accounting platform (real double-entry)

```
accounting_platform/
  db.py            shared SQLite schema + immutable audit log + period controls
  coa.py           Chart of Accounts: normal-balance rules + firm templates
  gl.py            General Ledger: balanced journal entries, posting w/ period
                   control, account balances, trial balance, reversing entries
  statements.py    Balance Sheet (A = L + E + Net Income), Income Statement,
                   direct-method Cash Flow, comparative
  ap.py / ar.py    AP/AR: vendors/customers, bills/invoices, payments, aging,
                   1099 — every bill/invoice/payment posts a real journal entry
  fixed_assets.py  straight-line / double-declining / units-of-production +
                   depreciation schedules + GL-posting
  bank_rec.py      CSV + OFX/QFX import, auto-matching to GL cash lines, recon report
  clients.py       clients / engagements / deadlines
  documents.py     document center: tags, versioning, linking, search
  importers.py     CSV journal/vendor/customer/bank import (grouped → balanced entries)
  dashboard.py     live overview: cash, AR/AP aging, profitability, alerts
```

Everything ties to one GL: AP/AR/fixed-assets post journal entries, so the trial
balance balances and the balance sheet satisfies **Assets = Liabilities + Equity +
Net Income** (verified in tests). API under `/platform/*` (COA, journal,
trial-balance, statements, AP/AR, assets, bank, clients, documents, import, audit,
dashboard); invalid/unbalanced entries → HTTP 400. Brain tools: `post_journal_entry`,
`financial_statement`, `accounting_dashboard`.

## Phase 7 — document intelligence + tax & advisory workbench

```
document_intelligence/  textextract (real PDF/Excel/Word/email/csv), ocr (Tesseract,
                        availability-gated — never fabricates text), classify, extract,
                        validate, pipeline, store (linked extractions)
tax_research/           authority KB (IRC/Reg/rulings/cases) + hierarchy + memo + risk +
                        planning; organizer (tax profiles, doc requests, missing tracker)
workpapers/             trial-balance / lead / depreciation / reconciliation / tax (M-1)
                        workpapers from the books + cross-ref + version store
advisory/               fs_analysis (liquidity/profitability/leverage/efficiency/quality)
                        + due_diligence (concentration, working capital, QoE, risk)
global_search.py        ranked search across documents, GL, tax research, clients
```

API under `/workbench/*`. **OCR honesty:** Tesseract isn't bundled — image OCR is
reported unavailable and raises rather than inventing text; **digital PDF/Excel/
Word/email extraction is real** (pypdf/openpyxl/python-docx/stdlib email) and
verified by a generated-PDF round-trip test. Brain tools: `process_document`,
`tax_research`, `tax_memo`, `generate_workpaper`, `financial_analysis`,
`due_diligence`, `global_search`.

## Phase 8 — execution / automation operating system

```
execution/      engine.py (approval + execution: risk tiers, propose/approve/reject/
                execute/rollback/retry + audit), registry.py (tier map + executors
                wired to the GL), automation.py (document → draft accounting action)
operations/     close.py (month-end checklist + close package), dashboards.py
                (tax-season / firm-ops / portfolio-ops aggregators)
outcomes/       engine.py (recommendation + outcome tracking, accuracy, agent
                performance, confidence calibration feedback)
n8n/generator.py  + month_end_close_workflow + build_plan (workflow + execution
                plan with dependencies/approvals/deadlines)
```

**Safety model (enforced + tested):** every action has a risk tier — Tier 1 may
auto-execute; Tier 2/3 require human approval before `execute()`; **Tier 4
(broker/tax-filing/external) NEVER auto-executes, requires explicit confirm to
approve, and the executor only PREPARES** (HELIOS never performs the external act).
Executed accounting actions are reversible via `rollback` (reverses the GL entry).
The brain may *propose* and *view* the queue (`approval_queue`,
`process_document_to_books`); approve/execute are human actions in the UI. API
under `/exec/*`, `/close/*`, `/outcomes/*`, `/ops/*`, `/workflow/build`.

Tests: **196 passing** (`pytest -q`) — Phase 1–7 plus Phase-8 approval/execution
(tier enforcement, Tier-4 prepare-only, rollback, failure handling, audit),
document automation, month-end close, outcomes/learning, and the execution router.

## Phase 9 — security, vault, backup, recovery & multi-device sync

Real cryptography — **AES-256-GCM** authenticated encryption with **scrypt**
key derivation. No mock crypto: wrong keys and tampered ciphertext fail
authentication, hash chains and checksums catch corruption.

```
security/       crypto.py (AES-256-GCM + scrypt + SHA-256/HMAC; DecryptionError on
                tamper), vault.py (encrypted credential store: master-password
                unlock, per-secret versioning, secret + master rotation, access
                audit — plaintext never persisted/listed), encrypted_store.py
                (namespaced AES-256-GCM KV for encrypted memory + documents, with
                access logging + re-key), compliance.py (immutable hash-chained
                audit log; verify() detects the first broken link),
                permissions.py (agent permission matrix — invariant: NO agent may
                approve/execute money/filing actions; enforce() at runtime),
                integrity.py (ledger consistency + audit-trail verification),
                health.py (per-store reachability/size + rolled-up status),
                service.py (vault-rooted lifecycle facade: data key keys the
                encrypted store + sync)
backup/         engine.py (encrypted + gzip-compressed, catalogued snapshots;
                full + incremental; checksum verify; retention), restore.py
                (full / selective / point-in-time restore; validates checksum +
                decrypts before writing), recovery.py (disaster recovery: recovery
                points, plan, non-destructive drill, readiness report)
sync/           engine.py (multi-device delta sync: device registration, server
                version clock, encrypted payloads, conflict detection +
                last-write-wins resolution, audit)
```

**Security model:** the vault is the root of trust. The master password derives
(scrypt) a key that unlocks a 256-bit *data key* — itself a vault secret —
which encrypts memory, documents and sync payloads. Locking tears those down.
Backups derive their own key from a backup password. Agents may *propose* and
*view* but never approve/execute money; compliance events are tamper-evident.
API under `/security/*`, `/vault/*`, `/compliance/*`, `/backup/*`, `/restore/*`,
`/recovery/*`, `/sync/*`. Locked-vault access to encrypted/sync surfaces → `423`.

Tests: **230 passing** (`pytest -q`) — the 196 above plus Phase-9 crypto
(roundtrip, wrong-key/AAD/tamper rejection, scrypt determinism), vault
(versioning, unlock guard, master rotation re-keys all), compliance chain
verify + tamper detection, permission invariants, ledger/audit integrity,
encrypted store (no-plaintext-at-rest, re-key), backup/restore (full,
incremental skip, retention, wrong-password rejection, point-in-time),
disaster-recovery plan + drill, sync (delta push/pull, encrypted-at-rest,
conflict resolution), the security service facade, and the Phase-9 router.

---

Tests (historical): **181 passing** — Phase 1–6 plus Phase-6 GL/statements
(balance-sheet identity, cash-flow reconciliation, period controls, reversals),
AP/AR + aging, depreciation, bank reconciliation, audit, importers, dashboard, and
Phase-7 document intelligence (real PDF extraction, classification, field
extraction, gated OCR), tax research + memo + organizer, workpapers, financial
analysis, due diligence, and global search.

## Adding a market-data provider

Implement a class with `quote(symbol)` and `history(symbol, range, interval)`
returning the normalized shapes in `market_data.py`, then pass it to
`MarketData(provider=...)`. Alpha Vantage / Polygon / Financial Modeling Prep
slot in this way behind the same interface (add the API key via env).
