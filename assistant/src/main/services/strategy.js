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

const DAY = 86400;
const TARGET_DTE = 35; // swing horizon for option selection

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

const round2 = (n) => Math.round(n * 100) / 100;

async function tradeIdea(symbol, { allowFutures = true } = {}) {
  const sym = String(symbol).trim().toUpperCase();
  const a = await analysis.api.analyze(sym, '6mo');
  const { bias, setupScore, reasons } = scoreFromAnalysis(a);

  const base = {
    symbol: sym,
    price: a.price,
    bias,
    setupScore,
    rationale: reasons,
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
  options_chain: ({ symbol, expiry }) => stocks.api.getOptions(symbol, expiry),
};

module.exports = {
  name: 'strategy',
  systemPromptFragment:
    'You have a trade-idea engine (find_trade_idea, scan_trade_ideas, options_chain). When the user asks what to trade or for a call/put/futures idea, use it and present the bias, the setupScore (explain it is signal-confluence strength, NOT a probability of profit), the specific contract or spread with its breakeven/max-loss and the % move required, and the underlying entry/stop/target. ' +
    'ALWAYS include a brief risk reminder: options/futures can lose 100%, size positions, use stops, this is not financial advice. If the engine says "stand aside", relay that honestly rather than inventing a trade. Never guarantee outcomes or claim an edge you cannot show. To act on an idea, equities go through propose_trade + approval; options/futures are placed manually at the user\'s broker.',
  tools,
  handlers,
  api: { tradeIdea, scanIdeas, scoreFromAnalysis },
};
