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
];

const handlers = {
  quant_analyze: (i) => api.analyze(i || {}),
  quant_factors: (i) => api.factors(i || {}),
  quant_risk: (i) => api.risk(i || {}),
  quant_portfolio: (i) => api.portfolio(i || {}),
  explain_asc: (i) => api.explainAsc(i.topic),
  accounting_memo: (i) => api.memo(i || {}),
};

module.exports = {
  name: 'sidecar',
  systemPromptFragment:
    'You have a local Intelligence Sidecar (Python/FastAPI) for heavy compute. Use quant_analyze, quant_factors, quant_risk, and quant_portfolio for institutional-grade market math, and explain_asc / accounting_memo for ASC/GAAP research and technical memos (Issue/Facts/Guidance/Analysis/Conclusion/Disclosure/CPA-impact). It runs locally; if it is offline, say so briefly and continue with what you can do without it.',
  tools,
  handlers,
  api,
};
