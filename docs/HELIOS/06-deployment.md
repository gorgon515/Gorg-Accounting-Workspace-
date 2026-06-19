# 06 — Deployment

Covers deliverable **20 (deployment instructions)**. Two parts: **(A)** running
the working app (ARIA, the HELIOS runtime) today, and **(B)** the deployment
topology for full HELIOS.

---

## A. Run HELIOS core today

The runnable app lives in [`assistant/`](../../assistant). It is **fully local by
default — no API key required.**

### 1. Prerequisites

- **Node 18+** (uses global `fetch`).
- **Ollama** for the local brain — <https://ollama.com> — then pull a model:
  ```bash
  ollama pull qwen2.5:7b        # or llama3.2:3b on lighter hardware
  ```
  (Strong tool-calling families are preferred; `brain.js` auto-detects what you've
  pulled.)

### 2. Install & start

```bash
cd assistant
npm install                 # also pulls optional on-device Whisper (transformers.js)
cp .env.example .env        # optional — leave keys blank to stay fully local
npm start
```

The header shows `brain online · local · <model>` when Ollama is detected. The
data panels (stocks, chart, alerts, tasks, trading, **language**, **agents**) work
even if the brain is offline.

### 3. Optional configuration (`.env`)

| Variable | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | use Claude (`claude-opus-4-8`) instead of local |
| `BRAIN_ENGINE` | force `local` or `claude` |
| `OLLAMA_MODEL` | preferred local model (default `qwen2.5:7b`) |
| `WHISPER_MODEL` | `Xenova/whisper-tiny.en` (default) → `base.en`/`small.en` |
| `STT_ENGINE` | `local` (default, on-device) or `whisper-api` (cloud, opt-in) |
| `GOOGLE_CLIENT_ID` / `_SECRET` | enable Gmail + Calendar (read) |
| `HELIOS_PERSONA` / `ARIA_PERSONA` | extra persona appended to the system prompt |

### 4. Voice & connectors

- **Push-to-talk** (🎤 Talk) records the mic and transcribes **on-device** via
  Whisper — audio never leaves the machine. First run downloads the model once
  (`npm run model` to pre-fetch).
- **Google**: create an OAuth **Desktop app** client (Gmail + Calendar APIs), put
  the id/secret in `.env`, then **Connections → Google: Connect**.
- **Alpaca** (paper/live): **Connections → Trading account** — credentials are
  validated and stored **encrypted** (OS keychain); the secret never returns to
  the UI. Live mode is double-confirmed and flagged red.

### 5. Web sessions (Claude Code on the web)

Web sessions run behind a network allowlist. To let market data load, add to the
environment's **Network access → Custom**:
```
query1.finance.yahoo.com
query2.finance.yahoo.com
```
Local `npm start` on your own machine is unaffected.

### 6. Build installers

```bash
npm run icon                # (re)generate the app icon from SVG
npm run dist:linux          # → dist/*.AppImage + .deb   (verified)
npm run dist:win            # → dist/*.exe (NSIS)         (run on Windows)
npm run dist:mac            # → dist/*.dmg + .zip         (run on macOS)
```
Or use the **Build installers** GitHub Actions workflow
(`.github/workflows/build-installers.yml`) on native runners; tag `vX.Y.Z` to
attach all installers to a Release. Builds are unsigned (expect first-run
SmartScreen/Gatekeeper prompts).

---

## B. Full HELIOS deployment topology

When the Python sidecar, N8N, and the databases land (Phase 2), the local
deployment becomes a small supervised set of localhost processes the Electron main
process manages:

```
 Electron app (main + renderer)            ← user launches this
   │ spawns / supervises (all 127.0.0.1)
   ├─► Python sidecar  (uvicorn :8420)      ← quant, NLP, doc parsing, crawlers
   ├─► PostgreSQL      (:5432)              ← relational truth (or embedded PG)
   ├─► ChromaDB        (persistent dir)     ← vectors / semantic memory
   ├─► N8N             (:5678, via Docker)  ← automation engine (embedded webview)
   └─► Ollama          (:11434)             ← local models (chat + embeddings)
```

### Bootstrap (designed `infra/` scripts)

1. **First-run wizard** detects/installs prerequisites: Ollama (+ pulls a default
   model), and — if the user opts into Phase-2 features — the Python sidecar venv,
   a local Postgres, and N8N (Docker).
2. **Migrations**: `data/migrations/*.sql` run against Postgres on startup; Chroma
   collections are created lazily.
3. **Health gating**: each dependency is health-checked with a short timeout;
   anything down degrades its feature only (the app still launches < 10 s).
4. **Models**: STT (Whisper) runs in-process; TTS (Piper) ships as a sidecar
   binary; embeddings via Ollama. All downloaded once, then offline-capable.

### Supervision & resilience

- The main process owns child-process lifecycles (start, health, restart with
  backoff, graceful shutdown on quit) — the same pattern `brain.localReady()`
  already uses for Ollama.
- **Backups**: scheduled encrypted snapshots of the Postgres data + Chroma dir +
  vault to a user-chosen local/external location; restore from the wizard.
- **Disaster recovery**: export/import of the full encrypted data bundle; the
  vault keys are sealed by the OS keychain (or an org passphrase in enterprise).

### Hardening checklist (install time)

- [ ] All services bound to `127.0.0.1` only (never `0.0.0.0`).
- [ ] CSP strict, `contextIsolation` on, `nodeIntegration` off (already true).
- [ ] Secrets only in the vault; never in `.env` for production installs.
- [ ] Audit log enabled; money/email/workflow actions gated.
- [ ] Code-signing for distributed installers (enterprise/commercial).
- [ ] Egress limited to declared connector hosts.

---

## Performance targets (verification)

| Goal | How it's met |
|---|---|
| Launch < 10 s | shell renders first; panels + models hydrate async, health-gated |
| Multiple local models | Ollama hosts many; per-agent routing selects per task |
| Large memory DBs | Postgres indexing + Chroma persistent collections (Phase 2) |
| Offline core | brain (Ollama), voice (Whisper), all local pillars need no network |
| Enterprise scale | background job queue, RBAC, audit, optional E2E sync (Phase 4) |
