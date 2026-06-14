'use strict';

// Technical analysis — computed locally from price history (no API, no key).
// Indicators: SMA, EMA, RSI(14), MACD(12/26/9), Bollinger(20,2σ), ATR(14).
// Also derives structure (swing high/low, support/resistance) and relative
// strength vs SPY — the inputs the strategy engine needs to place stops and
// tranche entries. Exposes analyze_stock and scan_watchlist to the brain, plus
// a raw API for future UI overlays. Informational only — not financial advice,
// and the skill prompt says so.

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

// ---------- volatility + structure (from OHLC candles) ----------
// Average True Range, Wilder smoothing. candles: [{ o, h, l, c }, ...] oldest→newest.
function atr(candles, n = 14) {
  if (!Array.isArray(candles) || candles.length < n + 1) return null;
  const tr = [];
  for (let i = 1; i < candles.length; i++) {
    const h = candles[i].h;
    const l = candles[i].l;
    const pc = candles[i - 1].c;
    if (h == null || l == null || pc == null) continue;
    tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
  }
  if (tr.length < n) return null;
  // seed with simple average of the first n true ranges, then Wilder-smooth
  let a = tr.slice(0, n).reduce((s, v) => s + v, 0) / n;
  for (let i = n; i < tr.length; i++) a = (a * (n - 1) + tr[i]) / n;
  return a;
}

// Recent N-bar extremes — the most useful swing levels for stops/targets.
function swings(candles, lookback = 20) {
  if (!Array.isArray(candles) || !candles.length) return { swingHigh: null, swingLow: null };
  const tail = candles.slice(-lookback);
  let hi = -Infinity;
  let lo = Infinity;
  for (const c of tail) {
    if (c.h != null && c.h > hi) hi = c.h;
    if (c.l != null && c.l < lo) lo = c.l;
  }
  return {
    swingHigh: hi === -Infinity ? null : hi,
    swingLow: lo === Infinity ? null : lo,
  };
}

// Coarse support/resistance: cluster recent pivot highs/lows into a few levels.
// A pivot is a bar whose high (or low) is the local extreme over ±span bars.
function pivotLevels(candles, span = 3, lookback = 60) {
  if (!Array.isArray(candles) || candles.length < span * 2 + 1) return { support: [], resistance: [] };
  const tail = candles.slice(-lookback);
  const highs = [];
  const lows = [];
  for (let i = span; i < tail.length - span; i++) {
    let isHigh = true;
    let isLow = true;
    for (let j = i - span; j <= i + span; j++) {
      if (j === i) continue;
      if (tail[j].h >= tail[i].h) isHigh = false;
      if (tail[j].l <= tail[i].l) isLow = false;
    }
    if (isHigh) highs.push(tail[i].h);
    if (isLow) lows.push(tail[i].l);
  }
  // collapse near-duplicate levels (within ~0.5%) and keep the most recent few
  const dedupe = (arr) => {
    const out = [];
    for (const v of arr) {
      if (!out.some((u) => Math.abs(u - v) / v < 0.005)) out.push(v);
    }
    return out.slice(-4);
  };
  return { support: dedupe(lows), resistance: dedupe(highs) };
}

// % change of `symbol` vs SPY over the candle window. Positive = outperforming.
function relStrength(symCandles, spyCandles) {
  const pct = (cs) => {
    if (!Array.isArray(cs) || cs.length < 2) return null;
    const first = cs.find((c) => c.c != null);
    const last = [...cs].reverse().find((c) => c.c != null);
    if (!first || !last || !first.c) return null;
    return ((last.c - first.c) / first.c) * 100;
  };
  const s = pct(symCandles);
  const b = pct(spyCandles);
  if (s == null || b == null) return null;
  return { symbolPct: s, spyPct: b, diff: s - b, outperforming: s - b > 0 };
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

  // OHLC candles power volatility (ATR), structure (swings/S&R), and relative
  // strength vs SPY. Best-effort: if the candle feed is unavailable, the
  // close-based indicators above still stand on their own.
  let atr14 = null;
  let levels = { swingHigh: null, swingLow: null, support: [], resistance: [] };
  let relStrengthVsSpy = null;
  try {
    const candleRange = range === '1y' ? '1y' : '6mo';
    const [symC, spyC] = await Promise.all([
      stocks.api.getCandles(symbol, candleRange),
      stocks.api.getCandles('SPY', '3mo'),
    ]);
    const candles = (symC && symC.candles) || [];
    if (candles.length) {
      atr14 = atr(candles, 14);
      const sw = swings(candles, 20);
      const piv = pivotLevels(candles);
      levels = { ...sw, ...piv };
    }
    // relative strength over ~3mo: slice both windows to the same recent span
    const symRecent = candles.slice(-63);
    const spyRecent = ((spyC && spyC.candles) || []).slice(-63);
    relStrengthVsSpy = relStrength(symRecent, spyRecent);
    if (relStrengthVsSpy) {
      signals.push(
        relStrengthVsSpy.outperforming
          ? `Outperforming SPY by ${relStrengthVsSpy.diff.toFixed(1)}% (3mo)`
          : `Lagging SPY by ${Math.abs(relStrengthVsSpy.diff).toFixed(1)}% (3mo)`
      );
    }
  } catch (_err) {
    // candle feed unavailable — leave ATR/levels/relStrength null, continue.
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
      atr14,
    },
    levels,
    relStrengthVsSpy,
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
  api: { analyze, scanWatchlist, atr, swings, pivotLevels, relStrength },
};
