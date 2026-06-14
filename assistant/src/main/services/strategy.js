'use strict';

// Trade-idea engine ("the mind"). Forms a directional thesis from local
// technicals, scores the setup's QUALITY (not a win probability), and turns it
// into concrete, defined-risk trade ideas using real options chains — or says
// STAND ASIDE when there's no clean setup.
//
// IMPORTANT / HONEST FRAMING (enforced in output + system prompt):
//   • No system predicts markets. "setupScore" measures signal confluence, not
//     the probability of profit.
//   • Options and futures can lose 100% (or more, for some structures). Every
//     idea includes the move required, max risk, and a not-advice disclaimer.
//   • This GENERATES IDEAS ONLY. It does not execute options/futures (those are
//     manual at your broker); equity orders still go through the approval gate.

const stocks = require('./stocks');
const analysis = require('./analysis');
const trading = require('./trading');

const DAY = 86400;
const TARGET_DTE = 35; // swing horizon for option selection

// Position-sizing knobs. riskPct is the fraction of account equity risked if a
// position is stopped out from full size; default 1% (env override). The
// default equity is only used when the portfolio is unavailable or reads $0.
const DEFAULT_RISK_PCT = clampPct(parseFloat(process.env.STRATEGY_RISK_PCT), 0.01);
const DEFAULT_EQUITY = parseFloat(process.env.STRATEGY_DEFAULT_EQUITY) || 100000;

function clampPct(v, fallback) {
  if (!Number.isFinite(v) || v <= 0) return fallback;
  // accept either fraction (0.01) or percent (1) form; normalize to fraction
  return v > 1 ? v / 100 : v;
}

// Futures proxies for common exposures (micro contract noted for sizing).
const FUTURES_MAP = {
  SPY: { sym: 'ES=F', micro: 'MES=F', name: 'S&P 500' },
  QQQ: { sym: 'NQ=F', micro: 'MNQ=F', name: 'Nasdaq 100' },
  DIA: { sym: 'YM=F', micro: 'MYM=F', name: 'Dow' },
  IWM: { sym: 'RTY=F', micro: 'M2K=F', name: 'Russell 2000' },
  GLD: { sym: 'GC=F', micro: 'MGC=F', name: 'Gold' },
  USO: { sym: 'CL=F', micro: 'MCL=F', name: 'Crude oil' },
};

// ---------- directional bias + setup score ----------
function scoreFromAnalysis(a) {
  const ind = a.indicators;
  let score = 0;
  const reasons = [];

  if (ind.sma20 != null && ind.sma50 != null) {
    if (ind.sma20 > ind.sma50) { score += 2; reasons.push('SMA20 > SMA50 (uptrend)'); }
    else { score -= 2; reasons.push('SMA20 < SMA50 (downtrend)'); }
  }
  if (ind.sma50 != null) {
    if (a.price > ind.sma50) { score += 1; reasons.push('price above SMA50'); }
    else { score -= 1; reasons.push('price below SMA50'); }
  }
  if (ind.macd) {
    if (ind.macd.histogram >= 0) { score += 1; reasons.push('MACD momentum positive'); }
    else { score -= 1; reasons.push('MACD momentum negative'); }
  }
  if (ind.rsi14 != null) {
    if (ind.rsi14 >= 70) { score -= 1; reasons.push(`RSI ${ind.rsi14.toFixed(0)} overbought (chase risk)`); }
    else if (ind.rsi14 <= 30) { score += 1; reasons.push(`RSI ${ind.rsi14.toFixed(0)} oversold (bounce potential)`); }
    else reasons.push(`RSI ${ind.rsi14.toFixed(0)} neutral`);
  }

  const max = 5;
  const bias = score >= 2 ? 'bullish' : score <= -2 ? 'bearish' : 'neutral';
  // setupScore: confluence strength 0–100 (NOT probability of profit)
  const setupScore = Math.round((Math.abs(score) / max) * 100);
  return { score, bias, setupScore, reasons };
}

// ---------- option selection ----------
function pickExpiry(expirationDates) {
  if (!expirationDates || !expirationDates.length) return null;
  const targetTs = Date.now() / 1000 + TARGET_DTE * DAY;
  return expirationDates.reduce((best, ts) =>
    Math.abs(ts - targetTs) < Math.abs(best - targetTs) ? ts : best
  );
}

const liquid = (o) => (o.openInterest || 0) >= 50 || (o.volume || 0) >= 25;

// Nearest contract at-or-just-out-of-the-money for a directional play.
function pickDirectional(list, price, isCall) {
  const candidates = list
    .filter((o) => o.strike != null && (o.mid || o.last))
    .sort((a, b) => a.strike - b.strike);
  if (!candidates.length) return null;
  // bullish call: first strike >= price*1.02; bearish put: first strike <= price*0.98
  const otm = isCall
    ? candidates.find((o) => o.strike >= price * 1.02 && liquid(o)) || candidates.find((o) => o.strike >= price)
    : [...candidates].reverse().find((o) => o.strike <= price * 0.98 && liquid(o)) || [...candidates].reverse().find((o) => o.strike <= price);
  return otm || null;
}

// Defined-risk vertical: long the directional strike, short one ~5–8% further OTM.
function buildSpread(list, longLeg, price, isCall) {
  const further = isCall
    ? list.filter((o) => o.strike > longLeg.strike).sort((a, b) => a.strike - b.strike)
    : list.filter((o) => o.strike < longLeg.strike).sort((a, b) => b.strike - a.strike);
  const target = isCall ? longLeg.strike + price * 0.06 : longLeg.strike - price * 0.06;
  const shortLeg = further.reduce(
    (best, o) => (best == null || Math.abs(o.strike - target) < Math.abs(best.strike - target) ? o : best),
    null
  );
  if (!shortLeg) return null;
  const debit = (longLeg.mid || longLeg.last) - (shortLeg.mid || shortLeg.last);
  if (!(debit > 0)) return null;
  const width = Math.abs(shortLeg.strike - longLeg.strike);
  return {
    type: isCall ? 'bull call spread' : 'bear put spread',
    longStrike: longLeg.strike,
    shortStrike: shortLeg.strike,
    netDebit: round2(debit),
    maxProfit: round2(width - debit),
    maxLoss: round2(debit),
    riskReward: round2((width - debit) / debit),
    breakeven: round2(isCall ? longLeg.strike + debit : longLeg.strike - debit),
  };
}

const round2 = (n) => (n == null || !Number.isFinite(n) ? null : Math.round(n * 100) / 100);
const pct = (a, b) => (b ? round2(((a - b) / b) * 100) : null);

// ---------- account equity (for position sizing) ----------
// Pull total account value from the trading portfolio; fall back to the
// configured default if it is unavailable or reads zero. Never throws.
async function getEquity(override) {
  if (Number.isFinite(override) && override > 0) return override;
  try {
    const p = await trading.api.getPortfolio();
    const total = Number(p && p.totalValue);
    if (Number.isFinite(total) && total > 0) return total;
  } catch (_err) {
    // portfolio unavailable — fall through to default
  }
  return DEFAULT_EQUITY;
}

// ---------- tranche plan + position sizing ----------
// Builds a laddered entry/stop/target plan with ATR-based risk and explicit
// share sizing. Bias drives direction; if neutral we plan the long side but
// flag it. This is a PLAN, not a prediction — R-multiples define the targets,
// the stop defines the risk, sizing keeps max loss to riskPct of equity.
async function buildTranchePlan(symbol, opts = {}) {
  const sym = String(symbol).trim().toUpperCase();
  const a = opts.analysis || (await analysis.api.analyze(sym, '6mo'));
  const sc = opts.score || scoreFromAnalysis(a);
  const bias = sc.bias;
  const long = bias !== 'bearish'; // plan the long side unless explicitly bearish
  const direction = bias === 'bearish' ? 'short' : 'long';

  const price = a.price;
  const ind = a.indicators || {};
  const lv = a.levels || {};
  const bb = ind.bollinger || {};
  // ATR drives stop distance; fall back to a 3% proxy if candles were missing.
  const atr = Number.isFinite(ind.atr14) ? ind.atr14 : price * 0.03;

  // Stop: 1.5×ATR beyond entry, against the direction of the trade.
  const stop = long ? price - 1.5 * atr : price + 1.5 * atr;
  const riskPerShare = Math.abs(price - stop);

  // Three laddered entries. Tranche 1 at market, 2 at a shallow pullback
  // (SMA20 or 0.5×ATR), 3 at deeper support (swing / lower band / 1.0×ATR).
  const shallow = long
    ? Math.min(ind.sma20 || Infinity, price - 0.5 * atr)
    : Math.max(ind.sma20 || -Infinity, price + 0.5 * atr);
  const deepCandidates = long
    ? [lv.swingLow, bb.lower, price - 1.0 * atr].filter((x) => Number.isFinite(x) && x < shallow)
    : [lv.swingHigh, bb.upper, price + 1.0 * atr].filter((x) => Number.isFinite(x) && x > shallow);
  const deep = deepCandidates.length
    ? (long ? Math.min(...deepCandidates) : Math.max(...deepCandidates))
    : (long ? price - 1.0 * atr : price + 1.0 * atr);

  const weights = [0.4, 0.35, 0.25];
  const entryPrices = [price, shallow, deep];
  // weighted-average (blended) entry — what sizing and R are measured from
  const blendedEntry = entryPrices.reduce((s, p, i) => s + p * weights[i], 0);
  const blendedRisk = Math.abs(blendedEntry - stop) || riskPerShare;

  // R = entry − stop. Targets at 1R/2R/3R, capped/aligned to resistance.
  const R = blendedRisk;
  const sign = long ? 1 : -1;
  const resist = long ? lv.swingHigh : lv.swingLow;
  const band = long ? bb.upper : bb.lower;
  const rMult = [1, 2, 3];
  const scaleOut = [0.5, 0.3, 0.2]; // take half at T1, then scale the rest
  const targets = rMult.map((m, i) => {
    let t = blendedEntry + sign * m * R;
    // nudge the final target toward structure if it sits beyond our R target
    if (i === rMult.length - 1) {
      const struct = [resist, band].filter((x) => Number.isFinite(x));
      if (struct.length) {
        const furthest = long ? Math.max(...struct) : Math.min(...struct);
        if (long ? furthest > t : furthest < t) t = furthest;
      }
    }
    return {
      label: `T${i + 1}`,
      price: round2(t),
      rMultiple: m,
      gainPct: pct(t, blendedEntry),
      scaleOutPct: Math.round(scaleOut[i] * 100),
    };
  });

  // ----- position sizing -----
  const equity = await getEquity(opts.equity);
  const riskPct = clampPct(opts.riskPct, DEFAULT_RISK_PCT);
  const riskDollars = equity * riskPct;
  const totalShares = blendedRisk > 0 ? Math.floor(riskDollars / blendedRisk) : 0;
  const entries = entryPrices.map((p, i) => {
    const shares = Math.floor(totalShares * weights[i]);
    return {
      label: `Tranche ${i + 1}`,
      weightPct: Math.round(weights[i] * 100),
      price: round2(p),
      fromMarketPct: pct(p, price),
      shares,
      notional: round2(shares * p),
    };
  });
  const sizedShares = entries.reduce((s, e) => s + e.shares, 0);
  const totalNotional = entries.reduce((s, e) => s + (e.notional || 0), 0);
  // worst case: full size taken, then stopped from the blended entry
  const maxRiskDollars = round2(sizedShares * blendedRisk);

  return {
    symbol: sym,
    bias,
    direction,
    biasNote: bias === 'neutral' ? 'Bias is neutral — this long-side ladder is illustrative; wait for confirmation or stand aside.' : null,
    price: round2(price),
    atr14: round2(atr),
    stop: { price: round2(stop), distancePct: pct(stop, price), basis: '1.5×ATR' },
    blendedEntry: round2(blendedEntry),
    riskPerShare: round2(blendedRisk),
    entries,
    targets,
    sizing: {
      equity: round2(equity),
      riskPct: round2(riskPct * 100),
      riskDollars: round2(riskDollars),
      totalShares: sizedShares,
      totalNotional: round2(totalNotional),
      maxRiskDollars,
      basis: opts.equity ? 'equity override' : 'portfolio totalValue (or default if unavailable)',
    },
    disclaimer:
      'A plan, not a prediction. R-multiples and ATR define risk/targets from confluence, NOT a probability of profit. Size to your own risk, use the stop, and never risk money you can\'t lose. Not financial advice.',
  };
}

async function tradeIdea(symbol, { allowFutures = true } = {}) {
  const sym = String(symbol).trim().toUpperCase();
  const a = await analysis.api.analyze(sym, '6mo');
  const score = scoreFromAnalysis(a);
  const { bias, setupScore, reasons } = score;

  // Laddered entry/stop/target plan with share sizing (reuses this analysis).
  const tranchePlan = await buildTranchePlan(sym, { analysis: a, score });

  const base = {
    symbol: sym,
    price: a.price,
    bias,
    setupScore,
    rationale: reasons,
    tranchePlan,
    disclaimer:
      'setupScore is signal-confluence strength, NOT a probability of profit. Options/futures carry substantial risk and can lose 100%. Not financial advice — size positions and use a stop.',
  };

  if (bias === 'neutral' || setupScore < 40) {
    return {
      ...base,
      recommendation: 'stand aside',
      note: 'No clean directional setup right now — the highest-odds move is often no trade.',
    };
  }

  const isCall = bias === 'bullish';
  // Underlying-based plan
  const stop = round2(isCall ? a.price * 0.95 : a.price * 1.05);
  const target = round2(isCall ? a.price * 1.08 : a.price * 0.92);

  // Real options idea (best-effort; underlying plan still returned if chain unavailable)
  let option = null;
  let spread = null;
  let optionError = null;
  try {
    const meta = await stocks.api.getOptions(sym);
    const expTs = pickExpiry(meta.expirationDates);
    const chain = expTs ? await stocks.api.getOptions(sym, expTs) : meta;
    const list = isCall ? chain.calls : chain.puts;
    const leg = pickDirectional(list, a.price, isCall);
    if (leg) {
      const dte = Math.round(((leg.expiration || expTs) - Date.now() / 1000) / DAY);
      const prem = leg.mid || leg.last;
      option = {
        type: isCall ? 'long call' : 'long put',
        strike: leg.strike,
        expiry: new Date((leg.expiration || expTs) * 1000).toISOString().slice(0, 10),
        dte,
        premium: round2(prem),
        breakeven: round2(isCall ? leg.strike + prem : leg.strike - prem),
        moveToBreakevenPct: round2((((isCall ? leg.strike + prem : leg.strike - prem) - a.price) / a.price) * 100),
        maxLossPerContract: round2(prem * 100),
        iv: leg.iv != null ? round2(leg.iv * 100) : null,
        openInterest: leg.openInterest,
        note: 'A single long option loses value to time decay; defined-risk spreads (below) reduce cost and theta.',
      };
      spread = buildSpread(list, leg, a.price, isCall);
    } else {
      optionError = 'No liquid contract found near target strike.';
    }
  } catch (err) {
    optionError = `Options chain unavailable: ${err.message}`;
  }

  // Futures alternative for index/commodity proxies
  let futures = null;
  if (allowFutures && FUTURES_MAP[sym]) {
    const f = FUTURES_MAP[sym];
    futures = {
      direction: isCall ? 'long' : 'short',
      contract: f.sym,
      microContract: f.micro,
      underlying: f.name,
      note: 'Futures are leveraged and marked-to-market daily; use the micro contract for smaller size. Manage with a hard stop.',
    };
  }

  return {
    ...base,
    recommendation: isCall ? 'bullish' : 'bearish',
    underlyingPlan: { entry: a.price, stop, target, riskPerShare: round2(Math.abs(a.price - stop)) },
    option,
    spread,
    optionError,
    futures,
  };
}

async function scanIdeas() {
  const symbols = stocks.api.getWatchlist();
  if (!symbols.length) return { ideas: [], note: 'Watchlist is empty.' };
  const settled = await Promise.allSettled(
    symbols.map(async (s) => {
      const a = await analysis.api.analyze(s, '6mo');
      const sc = scoreFromAnalysis(a);
      return { symbol: a.symbol, price: a.price, bias: sc.bias, setupScore: sc.setupScore, top: sc.reasons.slice(0, 2) };
    })
  );
  const ideas = settled
    .filter((r) => r.status === 'fulfilled')
    .map((r) => r.value)
    .filter((i) => i.bias !== 'neutral' && i.setupScore >= 40)
    .sort((a, b) => b.setupScore - a.setupScore);
  return {
    ideas,
    note: 'Ranked by signal confluence (setupScore), not win probability. Run a full idea on a symbol for specific contracts. Not financial advice.',
  };
}

// ---------- news/event → action plan ----------
// Per-symbol action label from bias + confluence + where price sits in its
// range. NOT a buy/sell command — a stance for a defined-risk plan.
function actionLabel(a, sc) {
  const { bias, setupScore } = sc;
  const lv = a.levels || {};
  const price = a.price;
  // near the top of the recent range = less room to accumulate; near the
  // bottom with a bullish bias = the spot to ladder in.
  const nearHigh = Number.isFinite(lv.swingHigh) && price >= lv.swingHigh * 0.98;
  const nearLow = Number.isFinite(lv.swingLow) && price <= lv.swingLow * 1.02;
  if (bias === 'neutral' || setupScore < 40) return 'stand aside';
  if (bias === 'bullish') return nearHigh ? 'trim' : 'accumulate';
  // bearish
  return nearLow ? 'hold' : 'trim';
}

// Compact summary of a tranche plan for embedding in the action-plan items.
function tranchePlanSummary(tp) {
  if (!tp) return null;
  return {
    entries: (tp.entries || []).map((e) => ({ price: e.price, weightPct: e.weightPct, shares: e.shares })),
    stop: tp.stop ? tp.stop.price : null,
    targets: (tp.targets || []).map((t) => ({ label: t.label, price: t.price, scaleOutPct: t.scaleOutPct })),
  };
}

// Synthesizes real-time news/events into a concrete plan of action across the
// watchlist (or a given symbol list). For each name: directional bias + setup
// score, a short tranche/sizing summary, recent headlines, and the next
// catalyst (earnings / ex-dividend). Defensive throughout — a single bad
// symbol or a missing data feed never sinks the whole plan.
async function buildActionPlan({ symbols } = {}) {
  let list = Array.isArray(symbols) && symbols.length
    ? symbols.map((s) => String(s).trim().toUpperCase()).filter(Boolean)
    : [];
  if (!list.length) {
    try { list = stocks.api.getWatchlist() || []; } catch (_err) { list = []; }
  }
  if (!list.length) {
    return { generatedAt: new Date().toISOString(), marketContext: 'Watchlist is empty — add symbols or pass a list.', items: [], topActions: [] };
  }

  // Brief market context from top broad-market headlines (best-effort).
  let marketContext = 'Market headlines unavailable.';
  try {
    const news = await stocks.api.getMarketNews();
    const heads = (news || []).slice(0, 3).map((n) => n.title).filter(Boolean);
    if (heads.length) marketContext = heads.join(' | ');
  } catch (_err) {
    // leave the default note
  }

  const settled = await Promise.allSettled(list.map(async (sym) => {
    const a = await analysis.api.analyze(sym, '6mo');
    const sc = scoreFromAnalysis(a);

    // Per-symbol extras are independently defensive: news/calendar/plan can
    // each fail without dropping the symbol from the plan.
    const [planR, newsR, calR] = await Promise.allSettled([
      buildTranchePlan(sym, { analysis: a, score: sc }),
      stocks.api.getNews(sym),
      stocks.api.getCalendar([sym]),
    ]);

    const tp = planR.status === 'fulfilled' ? planR.value : null;
    const catalysts = newsR.status === 'fulfilled'
      ? (newsR.value || []).slice(0, 3).map((n) => n.title).filter(Boolean)
      : [];
    const cal = calR.status === 'fulfilled' ? (calR.value || [])[0] : null;
    const nextEvent = cal
      ? (cal.earningsDate
        ? { type: 'earnings', date: cal.earningsDate }
        : cal.exDividendDate
          ? { type: 'ex-dividend', date: cal.exDividendDate }
          : null)
      : null;

    const summary = tranchePlanSummary(tp);
    return {
      symbol: a.symbol,
      price: round2(a.price),
      bias: sc.bias,
      setupScore: sc.setupScore,
      action: actionLabel(a, sc),
      catalysts,
      nextEvent,
      keyLevels: {
        entries: summary ? summary.entries.map((e) => e.price) : [],
        stop: summary ? summary.stop : null,
        targets: summary ? summary.targets.map((t) => t.price) : [],
      },
      sizing: tp ? { totalShares: tp.sizing.totalShares, maxRiskDollars: tp.sizing.maxRiskDollars, riskPct: tp.sizing.riskPct } : null,
    };
  }));

  // Keep error rows in the plan so the UI can surface what failed (rather than
  // silently dropping a symbol the user asked about).
  const items = settled.map((r, i) =>
    r.status === 'fulfilled' ? r.value : { symbol: list[i], error: r.reason && r.reason.message }
  );

  // One-line, ranked, plain-language actions (highest confluence first).
  const topActions = items
    .filter((it) => !it.error && it.action !== 'stand aside')
    .sort((a, b) => (b.setupScore || 0) - (a.setupScore || 0))
    .slice(0, 5)
    .map((it) => {
      const ev = it.nextEvent ? ` — ${it.nextEvent.type} ${String(it.nextEvent.date).slice(0, 10)}` : '';
      const sz = it.sizing ? `, ~${it.sizing.totalShares} sh (max risk $${it.sizing.maxRiskDollars})` : '';
      return `${it.action.toUpperCase()} ${it.symbol} (${it.bias}, score ${it.setupScore})${sz}${ev}`;
    });

  return {
    generatedAt: new Date().toISOString(),
    marketContext,
    items,
    topActions,
    disclaimer:
      'A plan from signal confluence and public events, NOT a prediction or win probability. Scores are confluence strength. Size to your own risk, use the stops, options/futures can lose 100%. Not financial advice.',
  };
}

const tools = [
  {
    name: 'find_trade_idea',
    description:
      'Generate a concrete trade idea for a ticker: directional bias + setup score, an underlying entry/stop/target, a specific real options contract (long call/put) and a defined-risk vertical spread, and a futures alternative for index/commodity proxies. Returns "stand aside" when there is no clean setup. Call when the user asks for a trade idea, a call/put to play, or "what should I trade on X".',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string' } },
      required: ['symbol'],
    },
  },
  {
    name: 'scan_trade_ideas',
    description: 'Scan the watchlist and rank the best directional setups by signal confluence. Call for "find me a trade", "best setups", or "scan for ideas".',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'tranche_plan',
    description:
      'Build a laddered tranche plan for a ticker: an ATR-based hard stop, three weighted entry tranches (at market / shallow pullback / deeper support), three scaled profit targets at R-multiples and structure, and explicit POSITION SIZING (shares per tranche, total shares, notional, max $ risk) from account equity and a risk %. Call when the user asks "how should I scale in", "what are my entries/stops/targets", "how many shares", or "give me a plan to build a position in X". Optional riskPct (fraction or percent) and equity override.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        riskPct: { type: 'number', description: 'Fraction (0.01) or percent (1) of equity to risk; default from STRATEGY_RISK_PCT or 1%' },
        equity: { type: 'number', description: 'Override account equity for sizing; defaults to portfolio totalValue' },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'build_action_plan',
    description:
      'Synthesize real-time news and upcoming events into a concrete plan of action across the watchlist (or a given symbol list). For each name: directional bias + setup score, an action label (accumulate/trim/hold/stand aside), key levels (entries/stop/targets) with share sizing, recent headlines, and the next catalyst (earnings/ex-dividend). Returns ranked one-line topActions. Call for "what\'s my plan today", "what should I do given the news", a morning briefing, or "any action items on my list".',
    input_schema: {
      type: 'object',
      properties: {
        symbols: { type: 'array', items: { type: 'string' }, description: 'Optional tickers; defaults to the saved watchlist' },
      },
    },
  },
  {
    name: 'options_chain',
    description: 'Get the real options chain (calls/puts with strikes, IV, open interest) for a ticker. Optional expiry as a unix timestamp from expirationDates.',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string' }, expiry: { type: 'number' } },
      required: ['symbol'],
    },
  },
];

const handlers = {
  find_trade_idea: ({ symbol }) => tradeIdea(symbol),
  scan_trade_ideas: () => scanIdeas(),
  tranche_plan: ({ symbol, riskPct, equity }) => buildTranchePlan(symbol, { riskPct, equity }),
  build_action_plan: ({ symbols }) => buildActionPlan({ symbols }),
  options_chain: ({ symbol, expiry }) => stocks.api.getOptions(symbol, expiry),
};

module.exports = {
  name: 'strategy',
  systemPromptFragment:
    'You have a trade-idea engine (find_trade_idea, scan_trade_ideas, options_chain), a tranche planner (tranche_plan), and a news/event action-plan synthesizer (build_action_plan). When the user asks what to trade or for a call/put/futures idea, use find_trade_idea and present the bias, the setupScore (explain it is signal-confluence strength, NOT a probability of profit), the specific contract or spread with its breakeven/max-loss and the % move required, and the underlying entry/stop/target. ' +
    'When the user asks how to scale in, for entries/stops/targets, how many shares, or a plan to build a position, use tranche_plan (or read tradeIdea.tranchePlan) and present the LADDER explicitly: the three weighted entry tranches with their prices and SHARE COUNTS, the ATR-based hard stop (price + %), the three scaled profit targets (R-multiple, price, scale-out %), and the sizing block (total shares, total notional, max $ risk). State the key levels concretely. ' +
    'When the user asks "what\'s my plan today", "what should I do given the news", or wants a morning briefing, use build_action_plan: relay the marketContext, the ranked topActions, and per-symbol the action label, key levels with sizing, recent headlines, and the next catalyst (earnings/ex-div). ' +
    'ALWAYS include a brief risk reminder: scores are confluence not win probability, options/futures can lose 100%, size positions, use stops, this is not financial advice. If the engine says "stand aside", relay that honestly rather than inventing a trade. Never guarantee outcomes or claim an edge you cannot show. To act on an idea, equities go through propose_trade + approval; options/futures are placed manually at the user\'s broker.',
  tools,
  handlers,
  api: { tradeIdea, scanIdeas, scoreFromAnalysis, buildTranchePlan, buildActionPlan },
};
