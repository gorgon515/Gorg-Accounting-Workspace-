# 05 — Roadmaps

Covers deliverables **16 (development), 17 (MVP), 18 (Phase 2), 19 (enterprise)**.

The guiding principle: **every milestone ships a runnable app.** HELIOS grows from
ARIA by extension, never by a rewrite that leaves the product non-functional.

---

## 16. Development roadmap (the whole arc)

```
 Phase 0  Foundation (ARIA)            ✅ DONE — this repository
 Phase 1  MVP: HELIOS core             ◀ now (orchestration + language shipped)
 Phase 2  Flagships & compute
 Phase 3  Intelligence & polish
 Phase 4  Enterprise & commercialization
```

| Phase | Theme | Exit criteria |
|---|---|---|
| 0 | Local-first assistant | ✅ brain, voice, skills, trading gate, memory |
| 1 | Multi-agent OS + UX | orchestration, language center, React HUD, briefings |
| 2 | Compute + automation | Python sidecar, quant, N8N, accounting intelligence, Postgres/Chroma |
| 3 | Depth + proactivity | knowledge graph, CPA qbank, Piper TTS, pronunciation, Outlook |
| 4 | Multi-user + commercial | RBAC, audit, sync, licensing, firm features |

---

## 17. MVP roadmap (Phase 1 — "HELIOS core")

Goal: the app *feels* like a personal intelligence OS — a coordinated agent team,
voice-first, with the Command Center and the flagship Language Center.

**Done in this blueprint pass**
- ✅ Multi-agent **orchestration layer** (`agents.js`) — 11-agent roster, local
  router, team system-prompt, `which_agent` tool, Agent Activity panel.
- ✅ **Language Immersion Center** (`language.js`) — 7 languages, shared SRS, daily
  missions, CEFR pathway, roleplay, progress; wired into IPC/preload/UI.
- ✅ This **architecture blueprint** (deliverables 1–20).

**Remaining MVP work**
1. **React/TS/Tailwind/Framer migration** of the renderer (carry existing tokens;
   panel boundaries already factored). _Largest item._
2. **Daily Briefing + End-of-Day Review** as first-class Chief-of-Staff flows
   (data already exists across productivity/google/markets/study/language).
3. **Memory panel** — search/edit/delete UI over the existing `memory` tools.
4. **Voice polish** — robust push-to-talk UX, interruptible TTS (barge-in),
   command palette (`⌘K`) sharing the router.
5. **Repository interface** seam (`store.js` → `Repository`) ahead of Postgres.

Exit: a user can speak to HELIOS, get a coordinated briefing, study a language
end-to-end, manage tasks/accounting/trading ideas — all local, no API key.

---

## 18. Phase 2 roadmap — "Flagships & compute"

1. **Python/FastAPI sidecar** (`/health` first, supervised by main).
2. **Quant Research System** — screening, factor models, **backtesting**,
   correlation/risk, portfolio construction, **Monte Carlo**, attribution →
   institutional dashboards in the Quant panel.
3. **Market Intelligence depth** — fundamentals/valuation/quality/sentiment/
   insider/options feeds behind the `stocks.js` provider abstraction.
4. **N8N Automation Center** — embed N8N (`<webview>`), Automation Agent tools
   (`create/update/execute/monitor workflow`), NL→workflow generation, credential
   provisioning from the vault.
5. **Accounting Intelligence Center** — crawlers (sidecar `/intel/crawl` and/or
   N8N) for FASB/SEC/PCAOB/IRS/AICPA/Big4+, `intel_item` store, the **Daily
   Accounting Briefing**, effective-date tracker.
6. **General Ledger upgrade** — double-entry (`journal_entry`/`journal_line`),
   COA, derived Balance Sheet / Income Statement / Cash Flow; QuickBooks/Excel/CSV
   import via `/docs/parse`.
7. **PostgreSQL + ChromaDB** behind the `Repository` interface; memory gains
   project/relationship/knowledge/behavioral types with hybrid retrieval.
8. **Email/Calendar write** — drafting, scheduling, conflict detection; begin
   Outlook/Graph connector.

Exit: the quant, automation, and accounting-intelligence flagships are live; data
runs on Postgres+Chroma; the accounting platform is firm-credible.

---

## 19. Enterprise roadmap (Phase 4) — "Multi-user & commercialization"

For small-firm / CPA-practice usage and future commercial sale:

1. **Role-based access control** — per-capability scopes (view vs. post ledger,
   read vs. send email, propose vs. approve trades), staff vs. partner roles.
2. **Full audit trail** — append-only `audit_event` for every tool call, money
   action, and connector access; exportable for review/SOX-style controls.
3. **Encryption & key management** — full data-store AES-256 at rest, vault keys
   sealed by OS keychain or org passphrase; backup/restore and disaster recovery.
4. **Client management at scale** — multi-client books, document storage, per-
   client research memos and disclosure checklists.
5. **Sync & multi-device** — optional encrypted sync (E2E) so a workstation and
   laptop share state without a third party reading it.
6. **Licensing & packaging** — signed installers (code-signing certs), license
   keys/activation, tiered features, telemetry that is opt-in and privacy-first.
7. **Performance at enterprise scale** — large memory DBs (Chroma sharding,
   Postgres indexing), background job queue for crawls/backtests, multi-model
   routing policy (small model for routing/email, strong model for memos/quant).
8. **Compliance posture** — data-residency guarantees (local-first is the moat),
   documented security architecture for firm IT review.

Exit: HELIOS is deployable in a small accounting firm with multiple staff,
auditable, licensable, and defensible to a security review.

---

## Risks & sequencing notes

- **Biggest single effort** is the React migration; do it early in Phase 1 so all
  later panels are built once, in the target stack.
- **Quant/quant-data licensing**: free endpoints are fine for personal use; firm/
  commercial use needs licensed market data — gate behind the provider
  abstraction so it's a config change.
- **Accounting correctness** is non-negotiable: the double-entry GL must be
  validated (debits = credits, trial balance) with tests before it replaces the
  current single-entry ledger.
- **Don't let the brain execute money/email actions** — preserve the propose/approve
  invariant through every phase; it is the product's trust foundation.
