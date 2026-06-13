'use strict';

// Technical analysis — computed locally from price history (no API, no key).
// Indicators: SMA, EMA(12/26), RSI(14), MACD(12/26/9), Bollinger(20,2σ),
// ATR(14), Stochastic(14,3), ADX/DMI(14), OBV, VWAP, 52-week position.
// Exposes analyze_stock and scan_watchlist to the brain, plus a raw API for
// future UI overlays. Informational only — not financial advice, and the
// skill prompt says so.

const stocks = require('./stocks');

// ---------- small helpers ----------
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

// Standard-deviation (population) of an array of numbers.
function stdev(values) {
  if (!values.length) return null;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, v) => a + (v - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

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

// Last EMA value (the indicator we surface), or null if insufficient data.
function emaLast(values, n) {
  const s = emaSeries(values, n);
  return s.length ? s[s.length - 1] : null;
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

// True Range series. Needs aligned high/low/close arrays; uses the prior close.
// TR_i = max(high-low, |high-prevClose|, |low-prevClose|). First bar = high-low.
function trueRanges(highs, lows, closes) {
  const tr = [];
  for (let i = 0; i < closes.length; i++) {
    const hl = highs[i] - lows[i];
    if (i === 0) { tr.push(hl); continue; }
    const hc = Math.abs(highs[i] - closes[i - 1]);
    const lc = Math.abs(lows[i] - closes[i - 1]);
    tr.push(Math.max(hl, hc, lc));
  }
  return tr;
}

// Wilder-smoothed ATR(14). Returns the latest ATR value or null.
function atr(highs, lows, closes, n = 14) {
  if (!highs.length || highs.length < n + 1) return null;
  const tr = trueRanges(highs, lows, closes);
  // Seed with simple average of the first n TRs, then Wilder smoothing.
  let prev = tr.slice(1, n + 1).reduce((a, b) => a + b, 0) / n;
  for (let i = n + 1; i < tr.length; i++) {
    prev = (prev * (n - 1) + tr[i]) / n;
  }
  return isNum(prev) ? prev : null;
}

// Stochastic oscillator (n=14 lookback, d=3 smoothing). %K uses the highest
// high / lowest low over the window; %D is the SMA(3) of recent %K values.
function stochastic(highs, lows, closes, n = 14, d = 3) {
  if (closes.length < n + d - 1) return null;
  const ks = [];
  for (let i = n - 1; i < closes.length; i++) {
    let hh = -Infinity;
    let ll = Infinity;
    for (let j = i - n + 1; j <= i; j++) {
      if (highs[j] > hh) hh = highs[j];
      if (lows[j] < ll) ll = lows[j];
    }
    const denom = hh - ll;
    ks.push(denom === 0 ? 100 : ((closes[i] - ll) / denom) * 100);
  }
  if (ks.length < d) return null;
  const k = ks[ks.length - 1];
  const dVal = ks.slice(-d).reduce((a, b) => a + b, 0) / d;
  return { k, d: dVal };
}

// ADX / DMI (Wilder, n=14). Returns { adx, plusDI, minusDI } or null.
// Standard directional-movement system: +DM/-DM, Wilder-smoothed alongside TR,
// directional indicators, DX, then Wilder-smoothed DX -> ADX.
function adx(highs, lows, closes, n = 14) {
  const len = closes.length;
  if (len < 2 * n + 1) return null;

  const plusDM = [];
  const minusDM = [];
  const tr = [];
  for (let i = 1; i < len; i++) {
    const up = highs[i] - highs[i - 1];
    const down = lows[i - 1] - lows[i];
    plusDM.push(up > down && up > 0 ? up : 0);
    minusDM.push(down > up && down > 0 ? down : 0);
    const hl = highs[i] - lows[i];
    const hc = Math.abs(highs[i] - closes[i - 1]);
    const lc = Math.abs(lows[i] - closes[i - 1]);
    tr.push(Math.max(hl, hc, lc));
  }
  if (tr.length < n) return null;

  // Wilder smoothing (running totals): seed with the first n, then roll.
  let smTR = tr.slice(0, n).reduce((a, b) => a + b, 0);
  let smPlus = plusDM.slice(0, n).reduce((a, b) => a + b, 0);
  let smMinus = minusDM.slice(0, n).reduce((a, b) => a + b, 0);

  const dxs = [];
  const pushDX = () => {
    const plusDI = smTR === 0 ? 0 : (smPlus / smTR) * 100;
    const minusDI = smTR === 0 ? 0 : (smMinus / smTR) * 100;
    const diSum = plusDI + minusDI;
    const dx = diSum === 0 ? 0 : (Math.abs(plusDI - minusDI) / diSum) * 100;
    dxs.push({ dx, plusDI, minusDI });
  };
  pushDX(); // DX at the seed window

  for (let i = n; i < tr.length; i++) {
    smTR = smTR - smTR / n + tr[i];
    smPlus = smPlus - smPlus / n + plusDM[i];
    smMinus = smMinus - smMinus / n + minusDM[i];
    pushDX();
  }

  if (dxs.length < n) return null;
  // ADX = Wilder-smoothed average of DX: first ADX is the SMA of the first n DX,
  // then Wilder-smoothed thereafter.
  let adxVal = dxs.slice(0, n).reduce((a, b) => a + b.dx, 0) / n;
  for (let i = n; i < dxs.length; i++) {
    adxVal = (adxVal * (n - 1) + dxs[i].dx) / n;
  }
  const last = dxs[dxs.length - 1];
  return { adx: adxVal, plusDI: last.plusDI, minusDI: last.minusDI };
}

// On-Balance Volume. Cumulative volume signed by the close-to-close direction.
// Needs a volume series aligned with closes; null if volume is unavailable.
function obv(closes, volumes) {
  if (!volumes || !volumes.length) return null;
  let usable = false;
  let v = 0;
  for (let i = 1; i < closes.length; i++) {
    const vol = volumes[i];
    if (!isNum(vol)) continue;
    usable = true;
    if (closes[i] > closes[i - 1]) v += vol;
    else if (closes[i] < closes[i - 1]) v -= vol;
  }
  return usable ? v : null;
}

// VWAP — only meaningful intraday (single session). Cumulative typical-price *
// volume over cumulative volume. Returns null when volume is missing or the
// range is not intraday.
function vwap(highs, lows, closes, volumes, intraday) {
  if (!intraday || !volumes || !volumes.length) return null;
  let pv = 0;
  let vol = 0;
  for (let i = 0; i < closes.length; i++) {
    const v = volumes[i];
    if (!isNum(v) || v <= 0) continue;
    const h = isNum(highs[i]) ? highs[i] : closes[i];
    const l = isNum(lows[i]) ? lows[i] : closes[i];
    const typical = (h + l + closes[i]) / 3;
    pv += typical * v;
    vol += v;
  }
  return vol > 0 ? pv / vol : null;
}

// Recent swing pivots for support/resistance. A pivot high/low is a bar whose
// high/low is the extreme of a +/-`w` window. Returns the few most recent
// distinct levels on each side relative to the current price.
function swingLevels(highs, lows, price, w = 3, maxEach = 3) {
  const resistance = [];
  const support = [];
  const n = highs.length;
  for (let i = w; i < n - w; i++) {
    let isHigh = true;
    let isLow = true;
    for (let j = i - w; j <= i + w; j++) {
      if (j === i) continue;
      if (highs[j] >= highs[i]) isHigh = false;
      if (lows[j] <= lows[i]) isLow = false;
    }
    if (isHigh && isNum(highs[i])) resistance.push(highs[i]);
    if (isLow && isNum(lows[i])) support.push(lows[i]);
  }
  // De-dupe near-equal levels (within 0.5%) and split by side of current price.
  const dedupe = (arr) => {
    const out = [];
    for (const v of arr) {
      if (!out.some((x) => Math.abs(x - v) / (v || 1) < 0.005)) out.push(v);
    }
    return out;
  };
  const res = dedupe(resistance)
    .filter((v) => price == null || v >= price)
    .sort((a, b) => a - b)
    .slice(0, maxEach);
  const sup = dedupe(support)
    .filter((v) => price == null || v <= price)
    .sort((a, b) => b - a)
    .slice(0, maxEach);
  return { support: sup, resistance: res };
}

// Annualized volatility (%) from daily simple returns. ~252 trading days/yr.
function annualizedVolatility(closes) {
  if (closes.length < 2) return null;
  const rets = [];
  for (let i = 1; i < closes.length; i++) {
    const prev = closes[i - 1];
    if (prev) rets.push((closes[i] - prev) / prev);
  }
  const sd = stdev(rets);
  return sd == null ? null : sd * Math.sqrt(252) * 100;
}

const round2 = (n) => (isNum(n) ? Math.round(n * 100) / 100 : n);

// ---------- analysis ----------
async function analyze(symbol, range = '6mo') {
  const hist = await stocks.api.getHistory(symbol, range);
  const points = hist.points || [];
  const closes = points.map((p) => p.close);
  if (closes.length < 30) throw new Error(`Not enough history for ${symbol} (${closes.length} points).`);

  // OHLCV from history (additive on the point object). Fall back to close when a
  // high/low is absent so indicators that need them still degrade gracefully.
  const highs = points.map((p) => (isNum(p.high) ? p.high : p.close));
  const lows = points.map((p) => (isNum(p.low) ? p.low : p.close));
  const volumes = points.map((p) => (isNum(p.volume) ? p.volume : null));
  const hasOHLC = points.some((p) => isNum(p.high) && isNum(p.low));
  const intraday = ['1d', '5d'].includes(range);

  const price = closes[closes.length - 1];
  const sma20 = sma(closes, 20);
  const sma50 = sma(closes, 50);
  const r = rsi(closes);
  const m = macd(closes);
  const bb = bollinger(closes);

  const ema12 = emaLast(closes, 12);
  const ema26 = emaLast(closes, 26);
  // ATR needs real highs/lows; if OHLC is absent, approximate from closes
  // (high=low=close makes TR collapse to |close-prevClose|, a close-only proxy).
  const atr14 = atr(highs, lows, closes);
  const stoch = stochastic(highs, lows, closes);
  const adx14 = adx(highs, lows, closes);
  const obvVal = obv(closes, volumes);
  const vwapVal = vwap(highs, lows, closes, volumes, intraday);
  const volPct = annualizedVolatility(closes);
  const sr = swingLevels(highs, lows, price);

  // 52-week range: prefer fundamentals (true 52wk), fall back to this window.
  let week52High = null;
  let week52Low = null;
  try {
    const f = await stocks.api.getFundamentals(symbol);
    if (f) {
      if (isNum(f.week52High)) week52High = f.week52High;
      if (isNum(f.week52Low)) week52Low = f.week52Low;
    }
  } catch {
    // fundamentals are best-effort; fall through to history-derived range
  }
  if (week52High == null) week52High = Math.max(...highs);
  if (week52Low == null) week52Low = Math.min(...lows);
  const week52Position =
    isNum(week52High) && isNum(week52Low) && week52High > week52Low
      ? Math.min(1, Math.max(0, (price - week52Low) / (week52High - week52Low)))
      : null;

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

  // ---- new plain-language signals ----
  if (adx14) {
    const dir = adx14.plusDI >= adx14.minusDI ? 'bullish (+DI > -DI)' : 'bearish (-DI > +DI)';
    if (adx14.adx >= 40) signals.push(`ADX ${adx14.adx.toFixed(0)} — very strong trend, ${dir}`);
    else if (adx14.adx >= 25) signals.push(`ADX ${adx14.adx.toFixed(0)} — trending, ${dir}`);
    else if (adx14.adx >= 20) signals.push(`ADX ${adx14.adx.toFixed(0)} — trend emerging, ${dir}`);
    else signals.push(`ADX ${adx14.adx.toFixed(0)} — weak/no trend (range-bound)`);
  }
  if (stoch) {
    if (stoch.k >= 80) signals.push(`Stochastic %K ${stoch.k.toFixed(0)} — overbought`);
    else if (stoch.k <= 20) signals.push(`Stochastic %K ${stoch.k.toFixed(0)} — oversold`);
    else signals.push(`Stochastic %K ${stoch.k.toFixed(0)} — neutral`);
  }
  if (isNum(atr14) && hasOHLC) {
    const atrPct = price ? (atr14 / price) * 100 : null;
    const longStop = round2(price - 2 * atr14);
    const shortStop = round2(price + 2 * atr14);
    signals.push(
      `ATR ${round2(atr14)}${atrPct != null ? ` (${atrPct.toFixed(1)}% of price)` : ''} — 2× ATR stop ≈ ${longStop} (long) / ${shortStop} (short)`
    );
  }
  if (obvVal != null) {
    signals.push(`OBV ${Math.round(obvVal).toLocaleString('en-US')} — volume flow ${obvVal >= 0 ? 'net accumulation' : 'net distribution'}`);
  }
  if (week52Position != null) {
    signals.push(`Price at ${(week52Position * 100).toFixed(0)}% of its 52-week range`);
  }
  if (isNum(volPct)) {
    signals.push(`Annualized volatility ≈ ${volPct.toFixed(0)}%`);
  }

  // ---- confluence -> technicalScore (0..100) + bias ----
  // technicalScore measures SIGNAL CONFLUENCE STRENGTH (how many technicals
  // agree, weighted by trend strength). It is NOT a probability of profit.
  const conf = confluence({ price, sma20, sma50, macd: m, rsi14: r, adx14, stoch, ema12, ema26 });

  const chg = (n) =>
    closes.length > n ? ((price - closes[closes.length - 1 - n]) / closes[closes.length - 1 - n]) * 100 : null;

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
      // ---- additive technicals ----
      ema12,
      ema26,
      atr14,
      stochastic: stoch,           // { k, d } | null
      adx14,                       // { adx, plusDI, minusDI } | null
      obv: obvVal,                 // number | null
      vwap: vwapVal,               // number | null (intraday only)
      week52: { high: week52High, low: week52Low, position: week52Position },
    },
    technicalScore: conf.score,    // 0..100 confluence strength (NOT win odds)
    bias: conf.bias,               // 'bullish' | 'bearish' | 'neutral'
    volatilityPct: volPct,         // annualized stdev of daily returns, %
    supportResistance: sr,         // { support: [..], resistance: [..] }
    signals,
    note: 'Computed locally from public price history. Informational only — not financial advice.',
  };
}

// Weighted bullish/bearish confluence. Returns a 0..100 strength score plus a
// directional bias. Each agreeing signal pushes net up/down; trend signals are
// trusted more when ADX confirms a real trend (ADX > 20/25). The score is the
// share of the maximum possible confluence weight that actually fired in one
// direction — a measure of agreement, not of expected return.
function confluence({ price, sma20, sma50, macd: m, rsi14, adx14, stoch, ema12, ema26 }) {
  let net = 0; // signed: + bullish, - bearish
  let maxW = 0;

  const trending = adx14 ? adx14.adx >= 20 : false;
  const strongTrend = adx14 ? adx14.adx >= 25 : false;

  // SMA cross (trend) — weight scales up when ADX confirms.
  if (isNum(sma20) && isNum(sma50)) {
    const w = strongTrend ? 3 : trending ? 2 : 1;
    maxW += 3;
    net += (sma20 > sma50 ? 1 : -1) * w;
  }
  // Price vs SMA50 (trend filter).
  if (isNum(sma50) && isNum(price)) {
    const w = trending ? 2 : 1;
    maxW += 2;
    net += (price > sma50 ? 1 : -1) * w;
  }
  // EMA12 vs EMA26 (faster trend).
  if (isNum(ema12) && isNum(ema26)) {
    maxW += 2;
    net += (ema12 > ema26 ? 1 : -1) * (trending ? 2 : 1);
  }
  // MACD momentum.
  if (m && isNum(m.histogram)) {
    maxW += 2;
    net += (m.histogram >= 0 ? 1 : -1) * 2;
  }
  // RSI: extremes are mean-reversion hints (oversold = bullish, overbought = bearish).
  if (isNum(rsi14)) {
    maxW += 1;
    if (rsi14 <= 30) net += 1;
    else if (rsi14 >= 70) net -= 1;
    else if (rsi14 >= 55) net += 0.5;
    else if (rsi14 <= 45) net -= 0.5;
  }
  // ADX directional indicators (only when actually trending).
  if (adx14 && trending) {
    maxW += 2;
    net += (adx14.plusDI >= adx14.minusDI ? 1 : -1) * 2;
  }
  // Stochastic extremes.
  if (stoch && isNum(stoch.k)) {
    maxW += 1;
    if (stoch.k <= 20) net += 1;
    else if (stoch.k >= 80) net -= 1;
  }

  if (maxW === 0) return { score: 0, bias: 'neutral' };
  const score = Math.round((Math.abs(net) / maxW) * 100);
  // Bias threshold: need meaningful net agreement (~25% of max weight) to call a side.
  const bias = net >= maxW * 0.25 ? 'bullish' : net <= -maxW * 0.25 ? 'bearish' : 'neutral';
  return { score, bias };
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
        // additive: confluence score + trend strength for richer scan rows
        technicalScore: a.technicalScore,
        bias: a.bias,
        adx: a.indicators.adx14 ? a.indicators.adx14.adx : null,
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
      'Run local technical analysis on a ticker: SMA20/50, EMA12/26, RSI(14), MACD, Bollinger bands, ATR(14), Stochastic, ADX/DMI trend strength, OBV, 52-week position, a 0-100 confluence score, support/resistance, and plain-language signals. Call when the user asks for analysis, technicals, trend strength, whether something is overbought/oversold, or "what do the charts say".',
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
      'Scan every watchlist ticker with local technicals (RSI, trend, MACD momentum, 20-day change, confluence score, ADX trend strength). Call when the user asks to scan the market, find overbought/oversold names, or "anything interesting on my list".',
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
    'You can run local technical analysis (SMA/EMA, RSI, MACD, Bollinger, ATR, Stochastic, ADX/DMI, OBV, 52-week position) on any ticker and scan the whole watchlist. ' +
    'analyze_stock also returns a 0-100 technicalScore — explain it is signal-confluence strength (how many indicators agree), NOT a probability of profit. ' +
    'Summarize signals in plain language and always note this is informational, not financial advice. Pair analysis with propose_trade only when the user asks to act.',
  tools,
  handlers,
  api: { analyze, scanWatchlist },
};
