'use strict';

// HELIOS Intelligence Sidecar bridge.
//
// The Quant Research Engine and Accounting Intelligence Engine live in a local
// Python/FastAPI service (../../../../backend). This module is the Electron seam:
//   • supervises the sidecar process (lazy start, health-check, restart backoff)
//   • exposes its compute as brain tools (quant_* / explain_asc / accounting_memo)
//   • degrades gracefully — if Python/the sidecar is unavailable, tools return a
//     clear "compute offline" message and the rest of HELIOS is unaffected.
//
// It follows the skill contract { name, systemPromptFragment, tools, handlers,
// api }. Nothing is spawned at require time — only on first use — so loading the
// registry (and the tests) never starts a process.

const path = require('path');
const { spawn } = require('child_process');
const config = require('../config');

// ---- locating the backend + interpreter --------------------------------------
// Dev layout: <repo>/assistant/src/main/services → up 4 → <repo>/backend
const BACKEND_DIR = config.sidecarDir || path.join(__dirname, '..', '..', '..', '..', 'backend');
const VENV_PY = process.platform === 'win32'
  ? path.join(BACKEND_DIR, '.venv', 'Scripts', 'python.exe')
  : path.join(BACKEND_DIR, '.venv', 'bin', 'python');

function pythonCmd() {
  if (config.sidecarPython) return config.sidecarPython;
  try {
    if (require('fs').existsSync(VENV_PY)) return VENV_PY;
  } catch { /* ignore */ }
  return process.platform === 'win32' ? 'python' : 'python3';
}

const BASE = config.sidecarUrl.replace(/\/$/, '');

// ---- process supervision ------------------------------------------------------
let child = null;
let starting = null; // in-flight start promise (de-dupes concurrent calls)
let lastError = null;
let restartAt = 0; // earliest time we may try to (re)start after a failure

async function ping(timeoutMs = 1200) {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) return false;
    const data = await res.json();
    return data && data.status === 'ok';
  } catch {
    return false;
  }
}

function spawnSidecar() {
  const py = pythonCmd();
  const args = ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(config.sidecarPort)];
  const proc = spawn(py, args, { cwd: BACKEND_DIR, env: { ...process.env }, stdio: 'ignore' });
  proc.on('exit', (code) => {
    if (child === proc) child = null;
    if (code && code !== 0) lastError = `sidecar exited (code ${code})`;
  });
  proc.on('error', (err) => {
    if (child === proc) child = null;
    lastError = `failed to launch python (${err.message})`;
  });
  return proc;
}

// Ensure the sidecar is up. Returns true if reachable, false (with lastError set)
// otherwise. Safe to call on every tool invocation — it no-ops when healthy.
async function ensureUp() {
  if (await ping()) return true;
  if (!config.sidecarAutostart) {
    lastError = 'sidecar not running and autostart disabled';
    return false;
  }
  if (Date.now() < restartAt) return false; // backing off after a recent failure
  if (!starting) {
    starting = (async () => {
      try {
        if (!child) child = spawnSidecar();
        // Poll for health for up to ~15s.
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 500));
          if (await ping()) return true;
          if (!child) break; // process died during startup
        }
        lastError = lastError || 'sidecar did not become healthy in time';
        restartAt = Date.now() + 30000; // 30s backoff before retrying
        return false;
      } finally {
        starting = null;
      }
    })();
  }
  return starting;
}

function stop() {
  if (child) {
    try { child.kill(); } catch { /* ignore */ }
    child = null;
  }
}
// Best-effort cleanup so we don't orphan the python process.
process.on('exit', stop);

async function status() {
  const ready = await ping();
  return {
    ready,
    url: BASE,
    managed: Boolean(child),
    autostart: config.sidecarAutostart,
    reason: ready ? null : (lastError || 'sidecar offline (start it or install backend deps)'),
  };
}

// ---- HTTP helpers -------------------------------------------------------------
async function call(method, route, body) {
  const up = await ensureUp();
  if (!up) {
    throw new Error(
      `Intelligence sidecar is offline (${lastError || 'unavailable'}). ` +
      'Install backend deps (backend/requirements.txt) and ensure Python is available.'
    );
  }
  const res = await fetch(`${BASE}${route}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(20000),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `sidecar ${res.status}`);
  return data;
}

const api = {
  status,
  ensureUp,
  stop,
  analyze: (p) => call('POST', '/quant/analyze', p),
  factors: (p) => call('POST', '/quant/factors', p),
  risk: (p) => call('POST', '/quant/risk', p),
  portfolio: (p) => call('POST', '/quant/portfolio', p),
  quote: (symbol) => call('GET', `/markets/quote/${encodeURIComponent(symbol)}`),
  ascTopics: () => call('GET', '/accounting/topics'),
  explainAsc: (topic) => call('GET', `/accounting/asc/${encodeURIComponent(topic)}`),
  memo: (p) => call('POST', '/accounting/memo', p),
  // Phase 4 — intelligence engines
  accountingBriefing: (refresh) => call('GET', `/accounting/briefing${refresh ? '?refresh=true' : ''}`),
  accountingIntel: (q) => call('GET', '/accounting/intel' + (q ? `?source=${encodeURIComponent(q)}` : '')),
  accountingIntelRefresh: () => call('POST', '/accounting/intel/refresh'),
  accountingGraph: (asc) => call('GET', '/accounting/graph' + (asc ? `?asc=${encodeURIComponent(asc)}` : '')),
  checklist: (topic) => call('POST', '/accounting/checklist', { topic }),
  memoFull: (p) => call('POST', '/accounting/memo/full', p),
  fundamentals: (p) => call('POST', '/quant/fundamentals', p),
  signal: (p) => call('POST', '/quant/signal', p),
  marketBriefing: (p) => call('POST', '/market/briefing', p),
  n8nStatus: () => call('GET', '/n8n/status'),
  n8nWorkflows: () => call('GET', '/n8n/workflows'),
  n8nGenerate: (p) => call('POST', '/n8n/generate', p),
  // Phase 5 — personal chief of staff
  createTask: (p) => call('POST', '/tasks', p),
  listTasks: (status) => call('GET', '/tasks' + (status ? `?status=${encodeURIComponent(status)}` : '')),
  updateTask: (p) => call('POST', '/tasks/update', p),
  completeTask: (tid) => call('POST', `/tasks/${encodeURIComponent(tid)}/complete`),
  deleteTask: (tid) => call('DELETE', `/tasks/${encodeURIComponent(tid)}`),
  recommendTasks: () => call('GET', '/tasks/recommend'),
  createGoal: (p) => call('POST', '/goals', p),
  goalsDashboard: () => call('GET', '/goals'),
  goalProgress: (p) => call('POST', '/goals/progress', p),
  deleteGoal: (gid) => call('DELETE', `/goals/${encodeURIComponent(gid)}`),
  schedulerJobs: () => call('GET', '/scheduler/jobs'),
  schedulerSeed: () => call('POST', '/scheduler/seed'),
  schedulerTick: () => call('POST', '/scheduler/tick'),
  schedulerHistory: () => call('GET', '/scheduler/history'),
  emailTriage: (emails) => call('POST', '/email/triage', { emails }),
  emailBriefing: (emails) => call('POST', '/email/briefing', { emails }),
  calendarPlan: (p) => call('POST', '/calendar/plan', p),
  cosDailyBriefing: (ctx) => call('POST', '/cos/daily-briefing', ctx || {}),
  cosEveningReview: (ctx) => call('POST', '/cos/evening-review', ctx || {}),
  cosPlan: (ctx) => call('POST', '/cos/plan', ctx || {}),
  cosBriefingAuto: () => call('GET', '/cos/briefing/auto'),
  cosPlanAuto: () => call('GET', '/cos/plan/auto'),
  // Phase 6 — accounting platform
  acctSeed: (template) => call('POST', `/platform/coa/seed?template=${encodeURIComponent(template || 'general_small_business')}`),
  acctChart: () => call('GET', '/platform/coa'),
  acctAddAccount: (p) => call('POST', '/platform/coa/account', p),
  acctJournal: (p) => call('POST', '/platform/journal', p),
  acctEntries: (q) => call('GET', '/platform/journal' + (q || '')),
  acctTrialBalance: (asOf) => call('GET', '/platform/trial-balance' + (asOf ? `?as_of=${asOf}` : '')),
  acctBalanceSheet: (asOf) => call('GET', '/platform/statements/balance-sheet' + (asOf ? `?as_of=${asOf}` : '')),
  acctIncome: (start, end) => call('GET', `/platform/statements/income?start=${start}&end=${end}`),
  acctCashFlow: (start, end) => call('GET', `/platform/statements/cash-flow?start=${start}&end=${end}`),
  acctApAging: () => call('GET', '/platform/ap/aging'),
  acctArAging: () => call('GET', '/platform/ar/aging'),
  acctAddVendor: (p) => call('POST', '/platform/ap/vendor', p),
  acctAddBill: (p) => call('POST', '/platform/ap/bill', p),
  acctAddCustomer: (p) => call('POST', '/platform/ar/customer', p),
  acctAddInvoice: (p) => call('POST', '/platform/ar/invoice', p),
  acctAssets: () => call('GET', '/platform/assets'),
  acctAddAsset: (p) => call('POST', '/platform/assets', p),
  acctAssetSchedule: (id) => call('GET', `/platform/assets/${id}/schedule`),
  acctClients: () => call('GET', '/platform/clients'),
  acctImportJournal: (csv) => call('POST', '/platform/import/journal', { csv }),
  acctAudit: () => call('GET', '/platform/audit'),
  acctDashboard: (asOf) => call('GET', '/platform/dashboard' + (asOf ? `?as_of=${asOf}` : '')),
  // Phase 7 — tax & advisory workbench
  ocrStatus: () => call('GET', '/workbench/docs/ocr-status'),
  docProcess: (p) => call('POST', '/workbench/docs/process', p),
  docSearch: (q) => call('GET', '/workbench/docs/search' + (q ? `?q=${encodeURIComponent(q)}` : '')),
  taxTopics: () => call('GET', '/workbench/tax/topics'),
  taxResearch: (query) => call('POST', '/workbench/tax/research', { query }),
  taxMemo: (p) => call('POST', '/workbench/tax/memo', p),
  orgClient: (p) => call('POST', '/workbench/tax/organizer/client', p),
  orgDashboard: () => call('GET', '/workbench/tax/organizer/dashboard'),
  wpTrialBalance: (asOf) => call('GET', '/workbench/workpapers/trial-balance' + (asOf ? `?as_of=${asOf}` : '')),
  wpLead: (type, asOf) => call('GET', `/workbench/workpapers/lead/${type}` + (asOf ? `?as_of=${asOf}` : '')),
  wpDepreciation: () => call('GET', '/workbench/workpapers/depreciation'),
  wpTax: (year) => call('GET', `/workbench/workpapers/tax/${year}`),
  advisoryAnalysis: (asOf) => call('GET', `/workbench/advisory/analysis?as_of=${asOf}`),
  advisoryDD: (year) => call('GET', `/workbench/advisory/due-diligence?year=${year}`),
  globalSearch: (q) => call('GET', `/workbench/search?q=${encodeURIComponent(q)}`),
};

const tools = [
  {
    name: 'quant_analyze',
    description:
      'Quant Research Engine: full technical analysis (SMA, RSI, MACD, Bollinger, momentum, volatility, max drawdown) with plain-language signals. Pass a symbol (fetched) or an explicit price series.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        prices: { type: 'array', items: { type: 'number' } },
        range: { type: 'string', description: 'e.g. 1mo, 6mo, 1y' },
      },
    },
  },
  {
    name: 'quant_factors',
    description:
      'Score a stock on transparent value/quality/growth/momentum factors from supplied fundamentals (pe, peg, roe, margins, growth, debt…) plus price momentum. Returns a composite 0–100 with per-factor breakdown.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        fundamentals: { type: 'object' },
        prices: { type: 'array', items: { type: 'number' } },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'quant_risk',
    description:
      'Risk analytics for a price series or symbol: annualized volatility, Sharpe, Sortino, max drawdown, 95% VaR, and beta/correlation vs a benchmark.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        prices: { type: 'array', items: { type: 'number' } },
        benchmark_symbol: { type: 'string' },
        risk_free: { type: 'number' },
      },
    },
  },
  {
    name: 'quant_portfolio',
    description:
      'Analyze a portfolio: weights, concentration (HHI / effective positions), sector exposure, and a blended risk profile. Holdings: [{symbol, weight|value, sector, prices?}].',
    input_schema: {
      type: 'object',
      properties: {
        holdings: { type: 'array', items: { type: 'object' } },
        benchmark_symbol: { type: 'string' },
      },
      required: ['holdings'],
    },
  },
  {
    name: 'explain_asc',
    description:
      'Accounting Intelligence: explain an ASC/GAAP topic from the knowledge base (e.g. "606"/"revenue", "842"/"leases", "326"/"CECL", "350"/"goodwill", "718"/"stock comp") — summary, framework, FS impact, disclosures, and CPA-exam relevance.',
    input_schema: {
      type: 'object',
      properties: { topic: { type: 'string' } },
      required: ['topic'],
    },
  },
  {
    name: 'accounting_memo',
    description:
      'Generate a technical accounting memo grounded in the cited ASC topic, in the standard structure: Issue, Facts, Guidance, Analysis, Conclusion, Disclosure impact, CPA-exam impact, Citations.',
    input_schema: {
      type: 'object',
      properties: {
        issue: { type: 'string' },
        facts: { type: 'string' },
        topic: { type: 'string', description: 'ASC topic, e.g. "606"' },
        conclusion: { type: 'string' },
      },
      required: ['issue', 'facts', 'topic'],
    },
  },
  {
    name: 'accounting_briefing',
    description:
      'Generate the daily accounting-intelligence briefing from monitored FASB/SEC/PCAOB/IRS sources: executive summary, key changes, upcoming effective dates, affected industries, CPA impact, emerging risks, action items, and a confidence level. Pass refresh=true to pull the latest before generating.',
    input_schema: { type: 'object', properties: { refresh: { type: 'boolean' } } },
  },
  {
    name: 'implementation_checklist',
    description: 'Produce a practical adoption/implementation checklist for an ASC topic (e.g. "606", "842"), grounded in its framework, with policy choices and disclosure steps.',
    input_schema: { type: 'object', properties: { topic: { type: 'string' } }, required: ['topic'] },
  },
  {
    name: 'quant_signal',
    description:
      'Generate a research signal for a stock: bull case, bear case, risk factors, catalysts, valuation/technical views, portfolio fit, and a confidence score — separating facts, calculations, interpretations, and forecasts. Not a trade recommendation. Pass a symbol (fetched) or an explicit price series.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        prices: { type: 'array', items: { type: 'number' } },
        benchmark_symbol: { type: 'string' },
        fundamentals: { type: 'object' },
        sector: { type: 'string' },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'market_briefing',
    description:
      'Generate a daily market briefing (overview, sector rotation, top movers, opportunities, portfolio risks) from a set of symbols or quotes.',
    input_schema: {
      type: 'object',
      properties: {
        symbols: { type: 'array', items: { type: 'string' } },
        quotes: { type: 'array', items: { type: 'object' } },
        portfolio: { type: 'array', items: { type: 'object' } },
      },
    },
  },
  {
    name: 'generate_workflow',
    description:
      'Generate an importable N8N workflow JSON from a high-level spec. Use kind="accounting_briefing" for the daily-briefing automation, or supply name/schedule/collect_url/email_to for a custom collect→process→distribute workflow.',
    input_schema: {
      type: 'object',
      properties: {
        kind: { type: 'string' },
        name: { type: 'string' },
        schedule: { type: 'string', description: 'cron, e.g. "0 7 * * *"' },
        collect_url: { type: 'string' },
        email_to: { type: 'string' },
      },
    },
  },
  {
    name: 'chief_of_staff_briefing',
    description:
      "The Chief of Staff's daily briefing assembled from your tasks and goals (the app adds your calendar/email): executive summary, today's priorities, deadlines, risks, opportunities, energy allocation, and recommended actions.",
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'plan_my_day',
    description:
      'Memory-driven autonomous day plan: derives the daily pace needed for your deadline-bearing goals (e.g. "CPA in 45 days"), schedules focus blocks, and recommends task-priority adjustments.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'add_priority_task',
    description:
      'Add a task to the Task Intelligence System (priority/deadline scoring, dependencies, recurrence, auto-categorization). Use for things to track and prioritize, not throwaway notes.',
    input_schema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        priority: { type: 'number', description: '1–5' },
        due: { type: 'string', description: 'YYYY-MM-DD' },
        recurrence: { type: 'string', enum: ['none', 'daily', 'weekly', 'monthly'] },
        project: { type: 'string' },
      },
      required: ['title'],
    },
  },
  {
    name: 'prioritized_tasks',
    description: 'Get the ranked, actionable (unblocked) tasks to work on now — overdue first, then by priority/deadline score.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'track_goal',
    description: 'Create a personal goal with an optional deadline (e.g. CPA, language, fitness, financial). Enables deadline-aware forecasting and day planning.',
    input_schema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        category: { type: 'string' },
        target: { type: 'number' },
        unit: { type: 'string' },
        deadline: { type: 'string', description: 'YYYY-MM-DD' },
      },
      required: ['title'],
    },
  },
  {
    name: 'goals_status',
    description: 'Get the goals dashboard with progress, deadline-aware forecast (ahead/on-track/behind), and recommendations.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'post_journal_entry',
    description:
      'Post a balanced double-entry journal entry to the accounting platform GL. Lines reference accounts by number (e.g. "1000") with a debit OR credit; debits must equal credits. Use for adjusting/accrual/manual entries.',
    input_schema: {
      type: 'object',
      properties: {
        date: { type: 'string', description: 'YYYY-MM-DD' },
        memo: { type: 'string' },
        lines: {
          type: 'array',
          items: {
            type: 'object',
            properties: { account: { type: 'string' }, debit: { type: 'number' }, credit: { type: 'number' }, memo: { type: 'string' } },
          },
        },
      },
      required: ['date', 'lines'],
    },
  },
  {
    name: 'financial_statement',
    description: 'Generate a financial statement from the GL: kind = balance_sheet | income | cash_flow | trial_balance. Provide start/end for income & cash flow.',
    input_schema: {
      type: 'object',
      properties: {
        kind: { type: 'string', enum: ['balance_sheet', 'income', 'cash_flow', 'trial_balance'] },
        as_of: { type: 'string' }, start: { type: 'string' }, end: { type: 'string' },
      },
      required: ['kind'],
    },
  },
  {
    name: 'accounting_dashboard',
    description: 'Live accounting dashboard: cash position, AR/AP aging, MTD/YTD profitability, balance-sheet summary, recent entries, alerts.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'process_document',
    description:
      'Run document intelligence on a document: extract real text (PDF/Excel/Word/email/text), classify it (invoice/W-2/1099/K-1/bank statement/contract/…), extract fields, and validate — with confidence. Pass text directly, or base64 file content. Scanned images need OCR (reports unavailable rather than guessing).',
    input_schema: {
      type: 'object',
      properties: { text: { type: 'string' }, base64: { type: 'string' }, filename: { type: 'string' } },
    },
  },
  {
    name: 'tax_research',
    description: 'Research a tax issue against primary authorities (IRC/Treasury Regs/rulings/cases), ranked by authority hierarchy, with planning opportunities and risk. Topics include home office, business meals, §179, QBI/§199A, S-corp reasonable comp, hobby loss.',
    input_schema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] },
  },
  {
    name: 'tax_memo',
    description: 'Generate a tax memo (Facts/Issues/Authorities/Analysis/Alternatives/Conclusion/Recommendations/References) grounded in the cited authorities.',
    input_schema: {
      type: 'object',
      properties: { facts: { type: 'string' }, issues: { type: 'string' }, topic: { type: 'string' } },
      required: ['facts', 'issues', 'topic'],
    },
  },
  {
    name: 'generate_workpaper',
    description: 'Generate a workpaper from the books: kind = trial_balance | lead (account_type) | depreciation | tax (year). Schedules tie to the trial balance.',
    input_schema: {
      type: 'object',
      properties: { kind: { type: 'string' }, account_type: { type: 'string' }, year: { type: 'number' }, as_of: { type: 'string' } },
      required: ['kind'],
    },
  },
  {
    name: 'financial_analysis',
    description: 'Financial statement analysis as of a date: liquidity, profitability, leverage, efficiency, cash-flow & earnings quality, with executive/board summaries.',
    input_schema: { type: 'object', properties: { as_of: { type: 'string' } }, required: ['as_of'] },
  },
  {
    name: 'due_diligence',
    description: 'Run a due-diligence review for a year: ratios, customer/vendor concentration, working capital, quality of earnings, and risk flags.',
    input_schema: { type: 'object', properties: { year: { type: 'number' } }, required: ['year'] },
  },
  {
    name: 'global_search',
    description: 'Search across documents, accounting records, tax research, and clients with one ranked query.',
    input_schema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] },
  },
];

const handlers = {
  quant_analyze: (i) => api.analyze(i || {}),
  quant_factors: (i) => api.factors(i || {}),
  quant_risk: (i) => api.risk(i || {}),
  quant_portfolio: (i) => api.portfolio(i || {}),
  explain_asc: (i) => api.explainAsc(i.topic),
  accounting_memo: (i) => api.memo(i || {}),
  accounting_briefing: (i) => api.accountingBriefing(i && i.refresh),
  implementation_checklist: (i) => api.checklist(i.topic),
  quant_signal: (i) => api.signal(i || {}),
  market_briefing: (i) => api.marketBriefing(i || {}),
  generate_workflow: (i) => api.n8nGenerate(i || {}),
  chief_of_staff_briefing: () => api.cosBriefingAuto(),
  plan_my_day: () => api.cosPlanAuto(),
  add_priority_task: (i) => api.createTask(i || {}),
  prioritized_tasks: () => api.recommendTasks(),
  track_goal: (i) => api.createGoal(i || {}),
  goals_status: () => api.goalsDashboard(),
  post_journal_entry: (i) => api.acctJournal(i || {}),
  financial_statement: (i) => {
    const k = (i && i.kind) || 'trial_balance';
    if (k === 'balance_sheet') return api.acctBalanceSheet(i.as_of);
    if (k === 'income') return api.acctIncome(i.start, i.end);
    if (k === 'cash_flow') return api.acctCashFlow(i.start, i.end);
    return api.acctTrialBalance(i.as_of);
  },
  accounting_dashboard: () => api.acctDashboard(),
  process_document: (i) => api.docProcess(i || {}),
  tax_research: (i) => api.taxResearch(i.query),
  tax_memo: (i) => api.taxMemo(i || {}),
  generate_workpaper: (i) => {
    const k = (i && i.kind) || 'trial_balance';
    if (k === 'lead') return api.wpLead(i.account_type || 'asset', i.as_of);
    if (k === 'depreciation') return api.wpDepreciation();
    if (k === 'tax') return api.wpTax(i.year || new Date().getFullYear());
    return api.wpTrialBalance(i.as_of);
  },
  financial_analysis: (i) => api.advisoryAnalysis(i.as_of),
  due_diligence: (i) => api.advisoryDD(i.year || new Date().getFullYear()),
  global_search: (i) => api.globalSearch(i.query),
};

module.exports = {
  name: 'sidecar',
  systemPromptFragment:
    'You have a local Intelligence Sidecar (Python/FastAPI) for heavy compute and research. For markets: quant_analyze, quant_factors, quant_risk, quant_portfolio, quant_signal (bull/bear/risks/catalysts/confidence), and market_briefing. For accounting research: explain_asc, accounting_memo, implementation_checklist, and accounting_briefing (the daily FASB/SEC/PCAOB/IRS intelligence digest). You also run a REAL double-entry accounting platform: post_journal_entry (debits must equal credits), financial_statement (balance_sheet/income/cash_flow/trial_balance), and accounting_dashboard (cash, AR/AP aging, profitability). For automation: generate_workflow. It runs locally; if it is offline or a data source is unreachable, say so briefly and continue. Always separate facts/calculations from interpretations/forecasts, and never present a forecast as certainty.',
  tools,
  handlers,
  api,
};
