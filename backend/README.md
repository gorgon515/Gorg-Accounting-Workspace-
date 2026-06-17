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

Tests: **131 passing** (`pytest -q`) across the Phase 1–4 engines plus Phase-5
tasks/goals, scheduler (next-run + cron + recovery), integrations normalization,
email & calendar intelligence, chief-of-staff briefing/review/planner, and routers.

## Adding a market-data provider

Implement a class with `quote(symbol)` and `history(symbol, range, interval)`
returning the normalized shapes in `market_data.py`, then pass it to
`MarketData(provider=...)`. Alpha Vantage / Polygon / Financial Modeling Prep
slot in this way behind the same interface (add the API key via env).
