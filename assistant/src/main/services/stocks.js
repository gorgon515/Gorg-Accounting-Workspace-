'use strict';

// Stocks skill — the first vertical slice.
//
// Data source: Yahoo Finance public JSON endpoints. No API key required.
// The v8 chart endpoint is the most reliable un-authenticated source for a
// live price; v1 search is used for symbol lookup; v7 quote is used for
// batched multi-symbol fetches (with a per-symbol fallback on auth errors).
// If Yahoo changes or blocks these, this is the single file to swap for a
// keyed provider (Finnhub, Alpha Vantage, Polygon) — the tool surface below
// stays identical.

const store = require('../store');
const { cached } = require('./marketdata');

const UA = 'Mozilla/5.0 (compatible; ARIA-Assistant/0.1)';
const CHART = 'https://query1.finance.yahoo.com/v8/finance/chart/';
const SEARCH = 'https://query1.finance.yahoo.com/v1/finance/search';
const OPTIONS = 'https://query1.finance.yahoo.com/v7/finance/options/';
const QUOTE_BATCH = 'https://query1.finance.yahoo.com/v7/finance/quote';
const CALENDAR = 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/';

async function yahoo(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`Yahoo HTTP ${res.status}`);
  return res.json();
}

// Range -> sensible candle interval for the history chart.
const INTERVALS = {
  '1d': '5m', '5d': '15m', '1mo': '1d', '3mo': '1d',
  '6mo': '1d', '1y': '1wk', '5y': '1mo', max: '3mo',
};

// --- Single-symbol quote (chart v8 path) ---
async function _fetchQuote(symbol) {
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

// Map a v7 batch result item into the canonical quote shape.
function _mapBatchQuote(q) {
  const price = q.regularMarketPrice ?? null;
  const prev = q.regularMarketPreviousClose ?? price;
  const change = price != null && prev != null ? price - prev : null;
  return {
    symbol: q.symbol,
    name: q.longName || q.shortName || q.symbol,
    currency: q.currency || 'USD',
    price,
    previousClose: prev,
    change,
    changePercent: prev && change != null ? (change / prev) * 100 : 0,
    marketState: q.marketState || 'UNKNOWN',
    time: q.regularMarketTime ? new Date(q.regularMarketTime * 1000).toISOString() : null,
  };
}

// Batched v7 fetch — returns an array of quote objects in the same order as
// `syms`. Falls back to per-symbol chart calls on any failure (e.g. 401).
async function _fetchBatch(syms) {
  try {
    const url = `${QUOTE_BATCH}?symbols=${syms.map(encodeURIComponent).join(',')}`;
    const data = await yahoo(url);
    const results = data?.quoteResponse?.result;
    if (!Array.isArray(results) || results.length === 0) {
      throw new Error('Empty batch response');
    }
    // Index by symbol so we can reassemble in original order.
    const bySymbol = Object.fromEntries(results.map((r) => [r.symbol, r]));
    return syms.map((s) => {
      const r = bySymbol[s.toUpperCase()];
      return r ? _mapBatchQuote(r) : { symbol: s.toUpperCase(), error: 'Not in batch response' };
    });
  } catch (batchErr) {
    // Batch call failed (auth, rate-limit, network). Fall back to individual
    // chart calls so the watchlist keeps working regardless.
    console.warn('[stocks] batch quote failed, falling back:', batchErr.message);
    const settled = await Promise.allSettled(syms.map(_fetchQuote));
    return settled.map((s, i) =>
      s.status === 'fulfilled'
        ? s.value
        : { symbol: String(syms[i]).toUpperCase(), error: s.reason.message }
    );
  }
}

// Public API: single quote, cached 4 seconds.
function getQuote(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  return cached(`quote:${sym}`, 4_000, () => _fetchQuote(sym));
}

// Public API: multi-symbol quotes — one batched request, cached 4 seconds.
// Key includes the sorted symbol list so different orderings share cache.
function getQuotes(symbols) {
  const list = (Array.isArray(symbols) ? symbols : [symbols])
    .map((s) => String(s).trim().toUpperCase())
    .filter(Boolean);
  const key = `quotes:${[...list].sort().join(',')}`;
  return cached(key, 4_000, () => _fetchBatch(list));
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

// News for a specific company/ticker, cached 60 seconds.
function getNews(query) {
  return cached(`news:${String(query).trim().toLowerCase()}`, 60_000, async () => {
    const data = await yahoo(
      `${SEARCH}?q=${encodeURIComponent(query)}&newsCount=8&quotesCount=0`
    );
    return (data.news || []).map((n) => ({
      title: n.title,
      publisher: n.publisher,
      link: n.link,
      time: n.providerPublishTime ? new Date(n.providerPublishTime * 1000).toISOString() : null,
    }));
  });
}

// Historical closing prices, cached 45 seconds.
function getHistory(symbol, range = '1mo') {
  const sym = String(symbol).trim().toUpperCase();
  return cached(`history:${sym}:${range}`, 45_000, async () => {
    const interval = INTERVALS[range] || '1d';
    const data = await yahoo(
      `${CHART}${encodeURIComponent(sym)}?range=${range}&interval=${interval}`
    );
    const result = data?.chart?.result?.[0];
    if (!result) throw new Error(`No history for "${sym}"`);
    const ts = result.timestamp || [];
    const close = result.indicators?.quote?.[0]?.close || [];
    const points = ts
      .map((t, i) => ({ t: new Date(t * 1000).toISOString(), close: close[i] }))
      .filter((p) => p.close != null);
    return { symbol: sym, range, interval, points };
  });
}

// OHLCV candles for chart rendering and strategy agents, cached 45 seconds.
// Returns { symbol, range, interval, candles: [{ t, o, h, l, c, v }] }
function getCandles(symbol, range = '6mo') {
  const sym = String(symbol).trim().toUpperCase();
  return cached(`candles:${sym}:${range}`, 45_000, async () => {
    const interval = INTERVALS[range] || '1d';
    const data = await yahoo(
      `${CHART}${encodeURIComponent(sym)}?range=${range}&interval=${interval}`
    );
    const result = data?.chart?.result?.[0];
    if (!result) throw new Error(`No candle data for "${sym}"`);
    const ts = result.timestamp || [];
    const q = result.indicators?.quote?.[0] || {};
    const open = q.open || [];
    const high = q.high || [];
    const low = q.low || [];
    const close = q.close || [];
    const volume = q.volume || [];
    const candles = ts
      .map((t, i) => ({
        t: new Date(t * 1000).toISOString(),
        o: open[i] ?? null,
        h: high[i] ?? null,
        l: low[i] ?? null,
        c: close[i] ?? null,
        v: volume[i] ?? null,
      }))
      .filter((p) => p.c != null); // drop bars with no close price
    return { symbol: sym, range, interval, candles };
  });
}

// Broad market news headlines, cached 60 seconds.
// Fetches news via the ^GSPC (S&P 500) search path — reliable and broad.
function getMarketNews() {
  return cached('market_news', 60_000, async () => {
    const data = await yahoo(
      `${SEARCH}?q=${encodeURIComponent('stock market')}&newsCount=12&quotesCount=0`
    );
    return (data.news || []).map((n) => ({
      title: n.title,
      publisher: n.publisher,
      link: n.link,
      time: n.providerPublishTime ? new Date(n.providerPublishTime * 1000).toISOString() : null,
    }));
  });
}

// Earnings/dividend calendar for a list of symbols, cached 1 hour.
// Returns [{ symbol, earningsDate, exDividendDate, dividendDate }]
// Dates are ISO strings or null. Yahoo earningsDate is an array; we take [0].
function getCalendar(symbols) {
  const list = (Array.isArray(symbols) ? symbols : [symbols])
    .map((s) => String(s).trim().toUpperCase())
    .filter(Boolean);
  const key = `calendar:${[...list].sort().join(',')}`;
  return cached(key, 3_600_000, async () => {
    const settled = await Promise.allSettled(
      list.map(async (sym) => {
        const data = await yahoo(
          `${CALENDAR}${encodeURIComponent(sym)}?modules=calendarEvents`
        );
        const cal = data?.quoteSummary?.result?.[0]?.calendarEvents;
        // Earnings date: array of { raw (unix seconds), fmt } — take first.
        const earnRaw = cal?.earnings?.earningsDate?.[0]?.raw ?? null;
        const exDivRaw = cal?.exDividendDate?.raw ?? null;
        const divRaw = cal?.dividendDate?.raw ?? null;
        return {
          symbol: sym,
          earningsDate: earnRaw ? new Date(earnRaw * 1000).toISOString() : null,
          exDividendDate: exDivRaw ? new Date(exDivRaw * 1000).toISOString() : null,
          dividendDate: divRaw ? new Date(divRaw * 1000).toISOString() : null,
        };
      })
    );
    // Be defensive: return null placeholders for any symbol that errored.
    return settled.map((s, i) =>
      s.status === 'fulfilled'
        ? s.value
        : { symbol: list[i], earningsDate: null, exDividendDate: null, dividendDate: null }
    );
  });
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
    description: 'Get historical closing prices for a ticker over a range, for trend questions ("how has X done this month").',
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
  {
    name: 'get_market_news',
    description:
      'Get top broad market news headlines (not company-specific). Call when the user asks what\'s happening in the market, for general market news, or a daily briefing.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'get_calendar',
    description:
      'Get the earnings date, ex-dividend date, and dividend date for one or more tickers. Call when the user asks when a company reports earnings or pays a dividend.',
    input_schema: {
      type: 'object',
      properties: {
        symbols: {
          type: 'array',
          items: { type: 'string' },
          description: 'Ticker symbols to look up',
        },
      },
      required: ['symbols'],
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
  get_watchlist: async () => getQuotes(getWatchlist()),
  add_to_watchlist: async ({ symbol }) => ({ watchlist: addToWatchlist(symbol) }),
  remove_from_watchlist: async ({ symbol }) => ({ watchlist: removeFromWatchlist(symbol) }),
  get_market_news: async () => getMarketNews(),
  get_calendar: ({ symbols }) => getCalendar(symbols),
};

module.exports = {
  name: 'stocks',
  systemPromptFragment:
    'You can look up live stock quotes, search tickers, fetch price history, OHLCV candles, and manage a saved watchlist. ' +
    'Use get_market_news for broad market headlines and get_calendar to look up earnings or dividend dates. ' +
    'Prices come from a public market-data feed and may be delayed ~15 minutes. ' +
    'You are not a licensed financial advisor: you may summarize data and explain it, but never tell the user to buy or sell, and add a brief reminder that this is not financial advice when the user asks what to do with their money.',
  tools,
  handlers,
  // Direct API used by UI panels and other services (no AI brain needed):
  api: {
    getQuote, getQuotes, searchSymbol, getNews, getHistory, getOptions,
    getCandles, getMarketNews, getCalendar,
    getWatchlist, addToWatchlist, removeFromWatchlist,
  },
};
