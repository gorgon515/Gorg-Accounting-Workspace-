# 03 — Domain Architecture

Covers deliverables **8 (accounting), 9 (trading), 10 (language-learning)**, plus
the Accounting Intelligence Center, CPA Study Center, and Research Engine that
hang off the accounting domain.

---

## 8. Accounting architecture

### Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Accounting Agent + Tax Agent  (NL guidance, memos, briefings)  │
├──────────────────────────────────────────────────────────────┤
│ Accounting Platform           Accounting Intelligence Center    │
│ • General Ledger (double-     • crawlers: FASB/SEC/PCAOB/IRS/    │
│   entry: journal_entry/line)    AICPA/Big4+ → intel_item         │
│ • Chart of Accounts           • daily briefing generator         │
│ • AP / AR / Invoices          • effective-date tracker           │
│ • Bank reconciliation         Research Engine                    │
│ • Financial statements        • ASC/SEC/tax citation + memo gen  │
│   (BS / IS / Cash Flow)       • disclosure checklists            │
│ • Budget / forecast           CPA Study Center                   │
│ • Fixed assets, payroll       • FAR/REG/AUD/TCP qbank+sims       │
│ • Import: QuickBooks/Excel/CSV• weakness tracking, readiness      │
└──────────────────────────────────────────────────────────────┘
                       schema in 02-data-architecture
```

### General Ledger (the core that's currently simplified)

- **Target**: true double-entry. Every economic event is a `journal_entry` with
  ≥2 `journal_line` rows whose debits equal credits, posted to `coa_account`s.
  Financial statements are *derived* (Balance Sheet from asset/liability/equity
  balances; Income Statement from income/expense; Cash Flow from cash-account
  movements).
- **Today** (`assistant/src/main/services/accounting.js`): a single-entry
  income/expense ledger + invoices + a P&L summary (income, expenses, net, by
  category, cash position, AR). It is correct and useful for a sole operator; it
  is the seed the double-entry GL grows from. Migration = treat each current txn
  as a two-line entry against a cash account.

### Imports & exports

- **QuickBooks**: IIF / QBO export parsing, mapping to the COA.
- **Excel / CSV**: column-mapping wizard → `journal_entry` rows; parsing runs in
  the Python sidecar (`/docs/parse`).
- **Exports**: statements to PDF/Excel; trial balance and GL detail to CSV.

### Accounting Intelligence Center

Continuously monitors standard-setters and firms and turns releases into a daily
briefing.

```
sources (FASB, SEC, PCAOB, IRS, Treasury, AICPA, Deloitte, PwC, EY, KPMG, BDO,
         Grant Thornton, Baker Tilly, Moss Adams)
   │ scheduled crawl (sidecar /intel/crawl, or N8N workflow)
   ▼
normalize → intel_item {source, doc_type, title, url, published_on, effective_on}
   │ embed → ChromaDB 'accounting_intel'   (semantic search)
   ▼
Daily Accounting Briefing:
   New FASB updates · SEC developments · IRS changes · upcoming effective dates ·
   emerging issues · tax changes · industry guidance
   └─ each item links to CPA Study Center topics it affects
```

Tracked doc types: Accounting Standards Updates, Exposure Drafts, Proposed Rules,
SEC guidance, PCAOB releases, IRS Notices, Revenue Rulings/Procedures, Tax Court
cases, industry publications. **Status**: designed; the Tax & Accounting agents
own it; crawlers are a Phase-2 sidecar/N8N deliverable.

### Accounting Research Engine

Generates professional memos in the standard structure:

> **Facts · Issue · Guidance · Analysis · Conclusion · Citations**

- Pulls authority from the relational `intel_item` + ChromaDB `accounting_intel`
  and `documents` collections (RAG over the user's saved standards).
- Citation generation for ASC/SEC/PCAOB/IRC references.
- Outputs disclosure checklists and audit-support documentation.
- **Honesty rule**: memos cite sources and flag where guidance is unsettled; the
  engine never fabricates citations — unresolved questions are surfaced, not
  papered over.

### CPA Study Center

- Modes: **FAR, REG, AUD, TCP** (plus the discipline sections already tracked:
  BAR, ISC). Question bank, simulations, flashcards, weakness tracking, adaptive
  learning, exam-readiness scores.
- **Links current developments to exam content**: an `intel_item` tagged to a
  topic surfaces in the matching study section ("this ASU affects FAR — revenue").
- **Today** (`study.js`): per-section progress tracker (`cpa_status`/
  `set_cpa_progress`), SM-2 flashcards, study log + streak. The qbank/simulations
  and adaptive engine are the build-out.

---

## 9. Trading architecture

The defining property: **the AI never executes. It analyzes, proposes, and
explains; you approve.**

```
 Market Intelligence ──► Quant Research ──► Trade Intelligence ──► Recommendation
 (data + signals)        (models)           (portfolio context)    (gated idea)
        │                    │                     │                    │
   stocks.js            analysis.js           trading.js           strategy.js
   (quotes/news/        (SMA/RSI/MACD/         (positions,          (thesis,
    history)             Bollinger)            approval gate)        options/futures)
                         + sidecar /quant      + broker.js (Alpaca)
```

### Market Intelligence Platform

Track NYSE/NASDAQ/AMEX, ETFs, REITs, indexes. Analysis dimensions: fundamentals,
technicals, valuation, momentum, quality, growth, value, macro, sector rotation,
earnings, news, sentiment, insider activity, analyst revisions, options activity,
risk metrics.

- **Today**: live quotes, search, history, news, a local TA engine
  (`analysis.js`: SMA20/50, RSI14, MACD, Bollinger), watchlist, alerts.
- **Designed**: fundamentals/valuation/quality factors and sentiment/insider/
  options feeds via keyed providers and the sidecar; the provider abstraction
  lives in `stocks.js` (single file to swap the data source).

### Quant Research System (Python sidecar)

Stock screening, factor models, backtesting, correlation/risk analysis, portfolio
construction, scenario modeling, Monte Carlo, performance attribution — all in the
FastAPI sidecar (`/quant/*`, see [02](./02-data-architecture.md)). Institutional-
grade dashboards render the results in the Quant panel.

### Trade Intelligence Engine

Analyzes holdings, open positions, watchlists, sector/geographic exposure, and
concentration risk; generates bull/bear cases, risk assessments, valuation models,
position-sizing suggestions, and expected-return estimates.

**Mandatory separation (spec):** every output explicitly labels **Facts ·
Historical Data · Estimates · Forecasts · Opinions** and never presents a forecast
as certainty.

### Trade Recommendation System

Each recommendation includes **Entry Zone · Exit Targets · Stop-Loss · Risk/Reward
· Supporting Evidence · Confidence Score**, drawn from technical + fundamental +
quant + risk + sentiment models.

- **Today** (`strategy.js`): forms a directional thesis from local technicals,
  scores **setup quality** (signal confluence — *explicitly not* a probability of
  profit), and produces concrete defined-risk ideas using **real options chains**
  (strike, expiry, break-even, max loss, IV), plus a futures alternative. Returns
  **"stand aside"** when there's no clean setup. It generates ideas only.

### Brokerage integration & the approval gate

- **Today**: Alpaca **paper or live** connected (`broker.js`); portfolio and fills
  route through Alpaca behind the same gate. Secrets encrypted via OS keychain,
  never returned to the renderer; live mode is double-confirmed and flagged red.
- **Designed**: Interactive Brokers, Fidelity, Schwab, Robinhood — portfolio sync,
  trade tracking, performance/risk monitoring, **order preparation only**.
- **Invariant**: the brain has `propose_trade` but **no execute tool**. Fills
  happen only on an explicit Approve click, re-priced at the live quote. This is
  enforced in `brain.js` (the tool simply doesn't exist) — not merely a prompt
  instruction.

---

## 10. Language-learning architecture

The Language Immersion Center is a flagship, and the part of this domain that
**shipped working** with this blueprint (`assistant/src/main/services/language.js`).

```
┌──────────────────────────────────────────────────────────────┐
│ Language Coach agent  (immersion conversation, correction)     │
├──────────────────────────────────────────────────────────────┤
│ language.js (durable state + structured pathway)               │
│  • 7 languages: Russian, Spanish, French, German, Italian,     │
│    Japanese, Mandarin                                          │
│  • profile: target language + CEFR self-level                  │
│  • vocab SRS  ── delegates to study.js (one shared card store) │
│  • daily missions (speaking/listening/reading/writing/vocab)   │
│  • CEFR pathway A1→C2 (curriculum reference data)              │
│  • roleplay scenario seeds (cafe/hotel/market/…)               │
│  • progress analytics + honest CEFR estimate                   │
├──────────────────────────────────────────────────────────────┤
│ Brain-driven live teaching (the systemPromptFragment):         │
│  conversation · pronunciation feedback · grammar correction ·  │
│  shadowing · reading/listening/writing modes · AI tutor        │
└──────────────────────────────────────────────────────────────┘
```

### Design decisions

- **One SRS, two doorways.** Vocabulary cards are stored once (the SM-2 engine in
  `study.js`), keyed by `subject = language`. `language.addVocab` delegates there,
  so a word learned in a café roleplay shows up in the Study review queue and in
  Language progress alike. No duplicate scheduling logic.
- **Durable state vs. live teaching, split cleanly.** `language.js` owns what must
  persist and be structured: the profile, the missions (deterministic per day so
  they're stable but rotate), progress, and the CEFR curriculum. The *teaching* —
  speaking in the target language, correcting grammar, scoring pronunciation,
  running shadowing — is the brain's job, steered by the `systemPromptFragment`.
  This keeps the durable layer testable and the conversational layer flexible.
- **Daily missions span all four modes.** Each day yields 4 missions drawn
  deterministically (seeded by date + language) across speaking, listening,
  reading, writing, and vocab — the "daily immersion tasks" requirement. Completion
  feeds a streak.
- **Honest progress.** The CEFR level shown is two numbers: the user's self-rated
  level and an *estimate* derived from learned-vocabulary milestones, explicitly
  labelled "a rough guide, not a test score." HELIOS does not pretend to certify
  fluency.
- **Beginner→fluent pathway.** The `CURRICULUM` (A1 Beginner → C2 Mastery) lists
  the communicative goals and vocabulary milestones per level — the spine the AI
  tutor teaches toward and the Pathway tab renders.

### Tools exposed to the brain

`set_target_language`, `language_progress`, `daily_missions`, `complete_mission`,
`language_roleplay` (plus the shared `add_vocab`/`due_flashcards`/`review_flashcard`
from Study). Tool names are deliberately distinct from Study's to avoid registry
shadowing.

### What's live vs. designed

| Capability | Status |
|---|---|
| 7 languages, profile, switching | ✅ |
| Vocabulary tracking (shared SRS) | ✅ |
| Daily missions (4 modes) | ✅ |
| CEFR pathway A1→C2 | ✅ |
| Roleplay scenarios | ✅ |
| Progress analytics + CEFR estimate | ✅ |
| Conversation / grammar correction / tutoring | ✅ (brain-driven) |
| Pronunciation analysis / accent scoring | 🟡 needs audio features (sidecar) |
| Speech shadowing with audio | 🟡 needs TTS clips + alignment |
| Reading/listening content library | ⬜ designed |

Pronunciation scoring and shadowing depend on the Piper/Coqui TTS + audio-feature
pipeline in the sidecar; the text-and-SRS spine they attach to is in place today.
