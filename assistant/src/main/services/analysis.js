'use strict';

// Technical analysis — computed locally from price history (no API, no key).
// Indicators: SMA, EMA, RSI(14), MACD(12/26/9), Bollinger(20,2σ).
// Exposes analyze_stock and scan_watchlist to the brain, plus a raw API for
// future UI overlays. Informational only — not financial advice, and the
// skill prompt says so.

const stocks = require('./stocks');

// ---------- indicator math ----------
function sma(values, n) {
  if (values.length < n) return null;
  let s = 0;
  for (let i = values.length - n; i < values.length; i++) s += values[i];
  return s / n;
}

function emaSeries(values, n) {
  if (values.length < n) return [];
  const k = 2 / (n + 1);
  const out = [];
  let prev = values.slice(0, n).reduce((a, b) => a + b, 0) / n;
  out.push(prev);
  for (let i = n; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out.push(prev);
  }
  return out;
}

function rsi(values, n = 14) {
  if (values.length < n + 1) return null;
  let gain = 0;
  let loss = 0;
  for (let i = 1; i <= n; i++) {
    const d = values[i] - values[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  let avgGain = gain / n;
  let avgLoss = loss / n;
  for (let i = n + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    avgGain = (avgGain * (n - 1) + Math.max(d, 0)) / n;
    avgLoss = (avgLoss * (n - 1) + Math.max(-d, 0)) / n;
  }
  if (avgLoss === 0) return 100;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

function macd(values, fast = 12, slow = 26, signal = 9) {
  if (values.length < slow + signal) return null;
  const emaFast = emaSeries(values, fast);
  const emaSlow = emaSeries(values, slow);
  // align series tails
  const len = Math.min(emaFast.length, emaSlow.length);
  const line = [];
  for (let i = 0; i < len; i++) {
    line.push(emaFast[emaFast.length - len + i] - emaSlow[emaSlow.length - len + i]);
  }
  const sig = emaSeries(line, signal);
  if (!sig.length) return null;
  const m = line[line.length - 1];
  const s = sig[sig.length - 1];
  return { macd: m, signal: s, histogram: m - s };
}

function bollinger(values, n = 20, mult = 2) {
  if (values.length < n) return null;
  const mid = sma(values, n);
  const tail = values.slice(-n);
  const variance = tail.reduce((a, v) => a + (v - mid) ** 2, 0) / n;
  const sd = Math.sqrt(variance);
  return { upper: mid + mult * sd, middle: mid, lower: mid - mult * sd };
}

// ---------- analysis ----------
async function analyze(symbol, range = '6mo') {
  const hist = await stocks.api.getHistory(symbol, range);
  const closes = hist.points.map((p) => p.close);
  if (closes.length < 30) throw new Error(`Not enough history for ${symbol} (${closes.length} points).`);

  const price = closes[closes.length - 1];
  const sma20 = sma(closes, 20);
  const sma50 = sma(closes, 50);
  const r = rsi(closes);
  const m = macd(closes);
  const bb = bollinger(closes);
  const chg = (n) =>
    closes.length > n ? ((price - closes[closes.length - 1 - n]) / closes[closes.length - 1 - n]) * 100 : null;

  const signals = [];
  if (r != null) {
    if (r >= 70) signals.push(`RSI ${r.toFixed(0)} — overbought territory`);
    else if (r <= 30) signals.push(`RSI ${r.toFixed(0)} — oversold territory`);
    else signals.push(`RSI ${r.toFixed(0)} — neutral`);
  }
  if (sma20 && sma50) {
    signals.push(sma20 > sma50 ? 'SMA20 above SMA50 — short-term uptrend' : 'SMA20 below SMA50 — short-term downtrend');
  }
  if (sma50) signals.push(price > sma50 ? 'Price above SMA50' : 'Price below SMA50');
  if (m) {
    signals.push(m.histogram >= 0 ? 'MACD histogram positive — bullish momentum' : 'MACD histogram negative — bearish momentum');
  }
  if (bb) {
    if (price >= bb.upper) signals.push('Price at/above upper Bollinger band');
    else if (price <= bb.lower) signals.push('Price at/below lower Bollinger band');
  }

  return {
    symbol: hist.symbol,
    range,
    price,
    changePct: { d5: chg(5), d20: chg(20) },
    indicators: {
      sma20, sma50,
      rsi14: r,
      macd: m,
      bollinger: bb,
    },
    signals,
    note: 'Computed locally from public price history. Informational only — not financial advice.',
  };
}

async function scanWatchlist() {
  const symbols = stocks.api.getWatchlist();
  if (!symbols.length) return { results: [], note: 'Watchlist is empty.' };
  const settled = await Promise.allSettled(
    symbols.map(async (s) => {
      const a = await analyze(s, '3mo');
      return {
        symbol: a.symbol,
        price: a.price,
        rsi14: a.indicators.rsi14,
        trend: a.indicators.sma20 && a.indicators.sma50
          ? (a.indicators.sma20 > a.indicators.sma50 ? 'up' : 'down')
          : null,
        momentum: a.indicators.macd ? (a.indicators.macd.histogram >= 0 ? 'bullish' : 'bearish') : null,
        d20Pct: a.changePct.d20,
      };
    })
  );
  const results = settled.map((s, i) =>
    s.status === 'fulfilled' ? s.value : { symbol: symbols[i], error: s.reason.message }
  );
  return { results, note: 'Local technical scan. Informational only — not financial advice.' };
}

const tools = [
  {
    name: 'analyze_stock',
    description:
      'Run local technical analysis on a ticker: SMA20/50, RSI(14), MACD, Bollinger bands, recent momentum, and plain-language signals. Call when the user asks for analysis, technicals, whether something is overbought/oversold, or "what do the charts say".',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string', description: 'Ticker symbol' },
        range: { type: 'string', enum: ['3mo', '6mo', '1y'], description: 'History window; default 6mo' },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'scan_watchlist',
    description:
      'Scan every watchlist ticker with local technicals (RSI, trend, MACD momentum, 20-day change). Call when the user asks to scan the market, find overbought/oversold names, or "anything interesting on my list".',
    input_schema: { type: 'object', properties: {} },
  },
];

const handlers = {
  analyze_stock: ({ symbol, range }) => analyze(symbol, range || '6mo'),
  scan_watchlist: () => scanWatchlist(),
};

module.exports = {
  name: 'analysis',
  systemPromptFragment:
    'You can run local technical analysis (SMA/EMA, RSI, MACD, Bollinger) on any ticker and scan the whole watchlist. Summarize signals in plain language and always note this is informational, not financial advice. Pair analysis with propose_trade only when the user asks to act.',
  tools,
  handlers,
  api: { analyze, scanWatchlist },
};
