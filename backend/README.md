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

Bad/insufficient input → `400`; provider/network failure → `503`.

## Adding a market-data provider

Implement a class with `quote(symbol)` and `history(symbol, range, interval)`
returning the normalized shapes in `market_data.py`, then pass it to
`MarketData(provider=...)`. Alpha Vantage / Polygon / Financial Modeling Prep
slot in this way behind the same interface (add the API key via env).
