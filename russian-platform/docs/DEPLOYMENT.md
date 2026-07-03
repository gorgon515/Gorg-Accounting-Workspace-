# Deployment Guide

## Minimum production configuration

```bash
export RLP_SECRET_KEY="$(openssl rand -hex 32)"     # required; startup warns otherwise
export RLP_DATABASE_URL="postgresql+psycopg://user:pass@host/rli"
export RLP_DEBUG=false
# Optional AI features:
export RLP_LLM_PROVIDER=anthropic
export RLP_ANTHROPIC_API_KEY=sk-ant-...
```

Install the Postgres extra: `pip install -e ".[postgres]"`.

## Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
- Startup runs `create_all` + idempotent seeding. **Before the first real
  deployment, introduce Alembic and replace `create_all`** (tracked debt —
  see PHASE_2_REPORT §6). Until then, schema changes require rebuilding
  the database.
- CORS origins are hardcoded for local dev in `app/main.py`; set your
  frontend origin there (or front both behind one domain and drop CORS).

## Frontend
```bash
cd frontend && npm ci && npm run build   # outputs dist/
```
Serve `dist/` statically (nginx, CDN) and proxy `/api` to the backend —
same shape as the dev proxy in `vite.config.ts`.

## Health & observability
- Liveness: `GET /health`.
- Logs: std logging to stdout; set your platform's collector on it.
- Backups: schedule Postgres snapshots; content is reproducible from seed,
  learner data is not.

## Scaling notes
- The API is stateless — scale workers horizontally; sessions are JWTs.
- Redis (config present, unused in Phase 2) is the intended cache for
  review queues and rate limiting in Phase 3.
- Media (audio) belongs in object storage referenced by `lexemes.audio`
  and `texts.sentences[].audio_url`.
