'use strict';

// Stocks skill — the first vertical slice.
//
// Data source: Yahoo Finance public JSON endpoints. No API key required.
// The v8 chart endpoint is the most reliable un-authenticated source for a
// live price; v1 search is used for symbol lookup. If Yahoo changes or blocks
// these, this is the single file to swap for a keyed provider (Finnhub,
// Alpha Vantage, Polygon) — the tool surface below stays identical.

const store = require('../store');

const UA = 'Mozilla/5.0 (compatible; ARIA-Assistant/0.1)';
const CHART = 'https://query1.finance.yahoo.com/v8/finance/chart/';
const SEARCH = 'https://query1.finance.yahoo.com/v1/finance/search';
const OPTIONS = 'https://query1.finance.yahoo.com/v7/finance/options/';
const QUOTE_SUMMARY = 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/';

async function yahoo(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`Yahoo HTTP ${res.status}`);
  return res.json();
}

// quoteSummary often returns 401/redirect without a crumb. Callers must handle
// the throw and fall back to chart meta — never let it break a higher-level
// flow. Yahoo wraps numeric fields as { raw, fmt }; pluck the raw number.
function rawOf(field) {
  if (field == null) return null;
  if (typeof field === 'number') return Number.isFinite(field) ? field : null;
  if (typeof field === 'object' && 'raw' in field) {
    const v = field.raw;
    return typeof v === 'number' && Number.isFinite(v) ? v : null;
  }
  return null;
}

// Parse a bare hostname (e.g. "apple.com") from a website URL. The UI builds a
// logo URL from this, so strip protocol, path, and any leading "www.".
function hostnameOf(website) {
  if (!website || typeof website !== 'string') return null;
  let url = website.trim();
  if (!url) return null;
  if (!/^https?:\/\//i.test(url)) url = `http://${url}`;
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.replace(/^www\./, '') || null;
  } catch {
    return null;
  }
}

// Range -> sensible candle interval for the history chart.
const INTERVALS = {
  '1d': '5m', '5d': '15m', '1mo': '1d', '3mo': '1d',
  '6mo': '1d', '1y': '1wk', '5y': '1mo', max: '3mo',
};

async function getQuote(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  const data = await yahoo(`${CHART}${encodeURIComponent(sym)}?range=1d&interval=1m`);
  const result = data?.chart?.result?.[0];
  if (!result) throw new Error(`No data for "${sym}"`);
  const m = result.meta;
  const price = m.regularMarketPrice;
  const prev = m.chartPreviousClose ?? m.previousClose ?? price;
  const change = price - prev;
  return {
    symbol: m.symbol || sym,
    name: m.longName || m.shortName || sym,
    currency: m.currency || 'USD',
    price,
    previousClose: prev,
    change,
    changePercent: prev ? (change / prev) * 100 : 0,
    marketState: m.marketState || 'UNKNOWN',
    time: m.regularMarketTime ? new Date(m.regularMarketTime * 1000).toISOString() : null,
  };
}

async function getQuotes(symbols) {
  const list = Array.isArray(symbols) ? symbols : [symbols];
  const settled = await Promise.allSettled(list.map(getQuote));
  return settled.map((s, i) =>
    s.status === 'fulfilled'
      ? s.value
      : { symbol: String(list[i]).toUpperCase(), error: s.reason.message }
  );
}

async function searchSymbol(query) {
  const data = await yahoo(`${SEARCH}?q=${encodeURIComponent(query)}&quotesCount=8&newsCount=0`);
  return (data.quotes || [])
    .filter((q) => q.symbol)
    .map((q) => ({
      symbol: q.symbol,
      name: q.longname || q.shortname || q.symbol,
      exchange: q.exchDisp || q.exchange || '',
      type: q.quoteType || '',
    }));
}

function mapOption(o) {
  return {
    contractSymbol: o.contractSymbol,
    strike: o.strike,
    last: o.lastPrice,
    bid: o.bid,
    ask: o.ask,
    mid: o.bid != null && o.ask != null && (o.bid || o.ask) ? (o.bid + o.ask) / 2 : o.lastPrice,
    iv: o.impliedVolatility,
    openInterest: o.openInterest,
    volume: o.volume,
    inTheMoney: o.inTheMoney,
    expiration: o.expiration,
  };
}

// Options chain. dateTs (unix seconds) selects a specific expiry; omit for the
// nearest. Returns underlying price, available expirations, and calls/puts.
async function getOptions(symbol, dateTs) {
  const sym = String(symbol).trim().toUpperCase();
  const url = `${OPTIONS}${encodeURIComponent(sym)}${dateTs ? `?date=${dateTs}` : ''}`;
  const data = await yahoo(url);
  const r = data?.optionChain?.result?.[0];
  if (!r) throw new Error(`No options data for "${sym}".`);
  const chain = (r.options && r.options[0]) || {};
  return {
    symbol: r.underlyingSymbol || sym,
    price: r.quote?.regularMarketPrice ?? null,
    expirationDates: r.expirationDates || [],
    expiration: chain.expirationDate || dateTs || null,
    calls: (chain.calls || []).map(mapOption),
    puts: (chain.puts || []).map(mapOption),
  };
}

async function getNews(query) {
  const data = await yahoo(
    `${SEARCH}?q=${encodeURIComponent(query)}&newsCount=8&quotesCount=0`
  );
  return (data.news || []).map((n) => ({
    title: n.title,
    publisher: n.publisher,
    link: n.link,
    time: n.providerPublishTime ? new Date(n.providerPublishTime * 1000).toISOString() : null,
  }));
}

async function getHistory(symbol, range = '1mo') {
  const sym = String(symbol).trim().toUpperCase();
  const interval = INTERVALS[range] || '1d';
  const data = await yahoo(
    `${CHART}${encodeURIComponent(sym)}?range=${range}&interval=${interval}`
  );
  const result = data?.chart?.result?.[0];
  if (!result) throw new Error(`No history for "${sym}"`);
  const ts = result.timestamp || [];
  const q = result.indicators?.quote?.[0] || {};
  const close = q.close || [];
  const open = q.open || [];
  const high = q.high || [];
  const low = q.low || [];
  const volume = q.volume || [];
  // Additive: open/high/low/volume per point (nullable), keeping { t, close }.
  const points = ts
    .map((t, i) => ({
      t: new Date(t * 1000).toISOString(),
      close: close[i],
      open: open[i] ?? null,
      high: high[i] ?? null,
      low: low[i] ?? null,
      volume: volume[i] ?? null,
    }))
    .filter((p) => p.close != null);
  return { symbol: sym, range, interval, points };
}

// ---------- fundamentals + company profile ----------
// Primary source is Yahoo quoteSummary, which may 401/redirect without a crumb.
// On ANY failure we fall back to whatever the v8 chart meta exposes and null
// the rest. These never throw — callers (analysis.js) depend on that.

async function chartMeta(sym) {
  try {
    const data = await yahoo(`${CHART}${encodeURIComponent(sym)}?range=1d&interval=1d`);
    return data?.chart?.result?.[0]?.meta || null;
  } catch {
    return null;
  }
}

async function getFundamentals(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  const out = {
    symbol: sym,
    marketCap: null,
    peTrailing: null,
    peForward: null,
    eps: null,
    dividendYield: null,
    beta: null,
    week52High: null,
    week52Low: null,
    dayHigh: null,
    dayLow: null,
    volume: null,
    avgVolume: null,
    priceToBook: null,
    profitMargin: null,
  };

  try {
    const url = `${QUOTE_SUMMARY}${encodeURIComponent(sym)}?modules=summaryDetail,defaultKeyStatistics,financialData,price`;
    const data = await yahoo(url);
    const r = data?.quoteSummary?.result?.[0];
    if (r) {
      const sd = r.summaryDetail || {};
      const ks = r.defaultKeyStatistics || {};
      const fd = r.financialData || {};
      const pr = r.price || {};

      out.marketCap = rawOf(sd.marketCap) ?? rawOf(pr.marketCap);
      out.peTrailing = rawOf(sd.trailingPE);
      out.peForward = rawOf(sd.forwardPE) ?? rawOf(ks.forwardPE);
      out.eps = rawOf(ks.trailingEps) ?? rawOf(fd.epsTrailingTwelveMonths);
      // Yahoo dividendYield is a fraction (e.g. 0.0052 -> 0.52%); expose as %.
      {
        const dy = rawOf(sd.dividendYield);
        out.dividendYield = dy != null ? dy * 100 : null;
      }
      out.beta = rawOf(sd.beta) ?? rawOf(ks.beta);
      out.week52High = rawOf(sd.fiftyTwoWeekHigh);
      out.week52Low = rawOf(sd.fiftyTwoWeekLow);
      out.dayHigh = rawOf(sd.dayHigh) ?? rawOf(pr.regularMarketDayHigh);
      out.dayLow = rawOf(sd.dayLow) ?? rawOf(pr.regularMarketDayLow);
      out.volume = rawOf(sd.volume) ?? rawOf(pr.regularMarketVolume);
      out.avgVolume = rawOf(sd.averageVolume) ?? rawOf(sd.averageDailyVolume10Day);
      out.priceToBook = rawOf(ks.priceToBook) ?? rawOf(sd.priceToBook);
      // profitMargins is a fraction (e.g. 0.25 -> 25%); expose as %.
      {
        const pm = rawOf(fd.profitMargins) ?? rawOf(ks.profitMargins);
        out.profitMargin = pm != null ? pm * 100 : null;
      }
    }
  } catch {
    // fall through to chart-meta fallback below
  }

  // Backfill any nulls from the always-available v8 chart meta.
  if (out.week52High == null || out.week52Low == null || out.dayHigh == null ||
      out.dayLow == null || out.volume == null) {
    const m = await chartMeta(sym);
    if (m) {
      out.week52High = out.week52High ?? (Number.isFinite(m.fiftyTwoWeekHigh) ? m.fiftyTwoWeekHigh : null);
      out.week52Low = out.week52Low ?? (Number.isFinite(m.fiftyTwoWeekLow) ? m.fiftyTwoWeekLow : null);
      out.dayHigh = out.dayHigh ?? (Number.isFinite(m.regularMarketDayHigh) ? m.regularMarketDayHigh : null);
      out.dayLow = out.dayLow ?? (Number.isFinite(m.regularMarketDayLow) ? m.regularMarketDayLow : null);
      out.volume = out.volume ?? (Number.isFinite(m.regularMarketVolume) ? m.regularMarketVolume : null);
    }
  }

  return out;
}

async function getProfile(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  const out = {
    symbol: sym,
    name: null,
    sector: null,
    industry: null,
    website: null,
    domain: null,
    description: null,
    country: null,
    employees: null,
  };

  try {
    const url = `${QUOTE_SUMMARY}${encodeURIComponent(sym)}?modules=assetProfile,price`;
    const data = await yahoo(url);
    const r = data?.quoteSummary?.result?.[0];
    if (r) {
      const ap = r.assetProfile || {};
      const pr = r.price || {};
      out.name = pr.longName || pr.shortName || null;
      out.sector = ap.sector || null;
      out.industry = ap.industry || null;
      out.website = ap.website || null;
      out.domain = hostnameOf(ap.website);
      out.description = ap.longBusinessSummary || null;
      out.country = ap.country || null;
      out.employees = rawOf(ap.fullTimeEmployees);
    }
  } catch {
    // fall through to chart-meta fallback for the name at least
  }

  if (!out.name) {
    const m = await chartMeta(sym);
    if (m) out.name = m.longName || m.shortName || null;
  }

  return out;
}

// --- Watchlist (persisted) ---
function getWatchlist() {
  return store.get('watchlist', []);
}
function addToWatchlist(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  const list = getWatchlist();
  if (!list.includes(sym)) list.push(sym);
  return store.set('watchlist', list);
}
function removeFromWatchlist(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  return store.set('watchlist', getWatchlist().filter((s) => s !== sym));
}

// Tool definitions exposed to the Claude brain. Descriptions are prescriptive
// about WHEN to call — recent Opus models reward that with better tool routing.
const tools = [
  {
    name: 'get_quote',
    description:
      'Get the current price, day change, and market state for a single stock ticker. Call this whenever the user asks about the price or performance of one company.',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string', description: 'Ticker symbol, e.g. AAPL' } },
      required: ['symbol'],
    },
  },
  {
    name: 'get_quotes',
    description: 'Get current quotes for several tickers at once. Use for "compare X and Y" or summarizing a basket.',
    input_schema: {
      type: 'object',
      properties: { symbols: { type: 'array', items: { type: 'string' }, description: 'Ticker symbols' } },
      required: ['symbols'],
    },
  },
  {
    name: 'search_symbol',
    description: 'Resolve a company name to its ticker symbol(s). Call this first when the user names a company but not its ticker.',
    input_schema: {
      type: 'object',
      properties: { query: { type: 'string', description: 'Company name or partial ticker' } },
      required: ['query'],
    },
  },
  {
    name: 'get_news',
    description: 'Get recent news headlines for a company or ticker. Call when the user asks what\'s happening with a stock or wants the latest news.',
    input_schema: {
      type: 'object',
      properties: { query: { type: 'string', description: 'Company name or ticker' } },
      required: ['query'],
    },
  },
  {
    name: 'get_history',
    description: 'Get historical OHLCV bars for a ticker over a range, for trend questions ("how has X done this month").',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string' },
        range: { type: 'string', enum: Object.keys(INTERVALS), description: 'Time range; default 1mo' },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'get_fundamentals',
    description:
      'Get fundamental metrics for a ticker: market cap, trailing/forward P/E, EPS, dividend yield, beta, 52-week high/low, day high/low, volume, average volume, price-to-book, and profit margin. Call when the user asks about valuation, fundamentals, market cap, dividend, P/E, or "is it expensive".',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string', description: 'Ticker symbol, e.g. AAPL' } },
      required: ['symbol'],
    },
  },
  {
    name: 'company_profile',
    description:
      "Get a company's profile for a ticker: full name, sector, industry, website, country, employee count, and a business description. Call when the user asks what a company does, what sector it's in, or for background on the business.",
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string', description: 'Ticker symbol, e.g. AAPL' } },
      required: ['symbol'],
    },
  },
  {
    name: 'get_watchlist',
    description: 'Return the user\'s saved watchlist tickers. Call when they ask "what\'s on my watchlist" or "how are my stocks doing".',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'add_to_watchlist',
    description: 'Add a ticker to the saved watchlist.',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string' } },
      required: ['symbol'],
    },
  },
  {
    name: 'remove_from_watchlist',
    description: 'Remove a ticker from the saved watchlist.',
    input_schema: {
      type: 'object',
      properties: { symbol: { type: 'string' } },
      required: ['symbol'],
    },
  },
];

// Maps tool name -> async handler. Each returns JSON-serializable data.
const handlers = {
  get_quote: ({ symbol }) => getQuote(symbol),
  get_quotes: ({ symbols }) => getQuotes(symbols),
  search_symbol: ({ query }) => searchSymbol(query),
  get_news: ({ query }) => getNews(query),
  get_history: ({ symbol, range }) => getHistory(symbol, range),
  get_fundamentals: ({ symbol }) => getFundamentals(symbol),
  company_profile: ({ symbol }) => getProfile(symbol),
  get_watchlist: async () => getQuotes(getWatchlist()),
  add_to_watchlist: async ({ symbol }) => ({ watchlist: addToWatchlist(symbol) }),
  remove_from_watchlist: async ({ symbol }) => ({ watchlist: removeFromWatchlist(symbol) }),
};

module.exports = {
  name: 'stocks',
  systemPromptFragment:
    'You can look up live stock quotes, search tickers, fetch price history, pull fundamentals (P/E, market cap, dividend, 52-week range) and company profiles, and manage a saved watchlist. ' +
    'Prices come from a public market-data feed and may be delayed ~15 minutes. ' +
    'You are not a licensed financial advisor: you may summarize data and explain it, but never tell the user to buy or sell, and add a brief reminder that this is not financial advice when the user asks what to do with their money.',
  tools,
  handlers,
  // Direct API used by UI panels (no AI brain needed):
  api: { getQuote, getQuotes, searchSymbol, getNews, getHistory, getFundamentals, getProfile, getOptions, getWatchlist, addToWatchlist, removeFromWatchlist },
};
