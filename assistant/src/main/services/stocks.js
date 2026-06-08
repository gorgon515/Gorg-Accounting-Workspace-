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

async function getHistory(symbol, range = '1mo') {
  const sym = String(symbol).trim().toUpperCase();
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
];

// Maps tool name -> async handler. Each returns JSON-serializable data.
const handlers = {
  get_quote: ({ symbol }) => getQuote(symbol),
  get_quotes: ({ symbols }) => getQuotes(symbols),
  search_symbol: ({ query }) => searchSymbol(query),
  get_history: ({ symbol, range }) => getHistory(symbol, range),
  get_watchlist: async () => getQuotes(getWatchlist()),
  add_to_watchlist: async ({ symbol }) => ({ watchlist: addToWatchlist(symbol) }),
  remove_from_watchlist: async ({ symbol }) => ({ watchlist: removeFromWatchlist(symbol) }),
};

module.exports = {
  name: 'stocks',
  systemPromptFragment:
    'You can look up live stock quotes, search tickers, fetch price history, and manage a saved watchlist. ' +
    'Prices come from a public market-data feed and may be delayed ~15 minutes. ' +
    'You are not a licensed financial advisor: you may summarize data and explain it, but never tell the user to buy or sell, and add a brief reminder that this is not financial advice when the user asks what to do with their money.',
  tools,
  handlers,
  // Direct API used by UI panels (no AI brain needed):
  api: { getQuote, getQuotes, searchSymbol, getHistory, getWatchlist, addToWatchlist, removeFromWatchlist },
};
