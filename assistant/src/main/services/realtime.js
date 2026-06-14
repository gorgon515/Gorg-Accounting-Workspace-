'use strict';

// Real-time price streaming via short-interval REST polling.
//
// Runs entirely in the Electron main process. No websockets, no new npm deps —
// only global fetch (Node 18+). A setInterval fires every ~1 500 ms, fetches
// the latest price from the configured provider, and delivers per-symbol ticks
// via a caller-supplied onTick callback.
//
// Provider is configured in config.js / environment variables:
//   MARKETDATA_PROVIDER  one of: none | finnhub | polygon | alpaca
//   MARKETDATA_API_KEY   provider API key (alpaca: "KEY_ID:SECRET")
//
// Only one active subscription is supported at a time; calling subscribe()
// again replaces any previous one.

const config = require('../config');

const POLL_MS = 1500; // polling interval; polite but still near-real-time

let _interval = null;      // active setInterval handle
let _streaming = false;
let _provider = 'none';

// --- Provider implementations ---

// Finnhub: GET /api/v1/quote?symbol=SYM&token=KEY
// Response: { c: currentPrice, t: unixSeconds, ... }
async function _finnhubTick(symbol, key) {
  const url = `https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}&token=${encodeURIComponent(key)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Finnhub HTTP ${res.status}`);
  const j = await res.json();
  if (j.c == null) throw new Error('Finnhub: no current price');
  return { symbol, price: j.c, time: j.t ? new Date(j.t * 1000).toISOString() : new Date().toISOString() };
}

// Polygon: GET /v2/last/trade/{SYM}?apiKey=KEY
// Response: { results: { p: price, t: nanoseconds, ... } }
async function _polygonTick(symbol, key) {
  // TODO: Polygon's /v2/last/trade endpoint requires a Starter plan or above.
  // The free tier (Delayed) may return 403 for real-time data. If that happens,
  // consider polling /v2/aggs/ticker/{SYM}/prev instead for the prior close.
  const url = `https://api.polygon.io/v2/last/trade/${encodeURIComponent(symbol)}?apiKey=${encodeURIComponent(key)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Polygon HTTP ${res.status}`);
  const j = await res.json();
  const p = j?.results?.p ?? null;
  if (p == null) throw new Error('Polygon: no price in response');
  // Polygon timestamps are nanoseconds since epoch.
  const tNs = j?.results?.t ?? null;
  const time = tNs ? new Date(tNs / 1_000_000).toISOString() : new Date().toISOString();
  return { symbol, price: p, time };
}

// Alpaca: GET /v2/stocks/{SYM}/trades/latest
// Auth: APCA-API-KEY-ID and APCA-API-SECRET-KEY headers.
// MARKETDATA_API_KEY format: "KEY_ID:SECRET" (colon-separated).
async function _alpacaTick(symbol, key) {
  // TODO: Alpaca broker keys (paper or live) are required. Free IEX feed may
  // not include all symbols. SIP feed requires an Alpaca subscription.
  // Split "KEY_ID:SECRET" — if no colon, treat entire string as key id.
  const colonIdx = key.indexOf(':');
  const keyId = colonIdx >= 0 ? key.slice(0, colonIdx) : key;
  const secret = colonIdx >= 0 ? key.slice(colonIdx + 1) : '';
  const url = `https://data.alpaca.markets/v2/stocks/${encodeURIComponent(symbol)}/trades/latest`;
  const res = await fetch(url, {
    headers: {
      'APCA-API-KEY-ID': keyId,
      'APCA-API-SECRET-KEY': secret,
    },
  });
  if (!res.ok) throw new Error(`Alpaca HTTP ${res.status}`);
  const j = await res.json();
  const trade = j?.trade;
  if (!trade || trade.p == null) throw new Error('Alpaca: no trade price');
  return { symbol, price: trade.p, time: trade.t || new Date().toISOString() };
}

// Dispatch to the right provider implementation.
async function _fetchTick(symbol, provider, key) {
  switch (provider) {
    case 'finnhub': return _finnhubTick(symbol, key);
    case 'polygon': return _polygonTick(symbol, key);
    case 'alpaca':  return _alpacaTick(symbol, key);
    default:        throw new Error(`Unknown provider: ${provider}`);
  }
}

// --- Public API ---

/**
 * Start polling prices for the given symbols and calling onTick per update.
 *
 * @param {string[]} symbols    Ticker symbols to stream.
 * @param {Function} onTick     Called with { symbol, price, time } per symbol per tick.
 * @returns {{ streaming: boolean, provider: string }}
 */
function subscribe(symbols, onTick) {
  const provider = config.marketdataProvider || 'none';
  const key = config.marketdataApiKey || '';

  // No-op when no provider configured — return false so callers can degrade gracefully.
  if (provider === 'none' || !key) {
    return { streaming: false, provider };
  }

  // Replace any existing subscription cleanly.
  unsubscribe();

  const syms = (Array.isArray(symbols) ? symbols : [symbols])
    .map((s) => String(s).trim().toUpperCase())
    .filter(Boolean);

  if (!syms.length) return { streaming: false, provider };

  _provider = provider;
  _streaming = true;

  _interval = setInterval(async () => {
    // Fire all ticks concurrently; swallow per-symbol errors so one bad symbol
    // doesn't kill the loop.
    await Promise.allSettled(
      syms.map(async (sym) => {
        try {
          const tick = await _fetchTick(sym, provider, key);
          if (typeof onTick === 'function') onTick(tick);
        } catch (err) {
          // Log quietly; don't rethrow — keeps the loop alive.
          console.warn(`[realtime] tick failed for ${sym}:`, err.message);
        }
      })
    );
  }, POLL_MS);

  return { streaming: true, provider };
}

/**
 * Stop any active polling subscription.
 */
function unsubscribe() {
  if (_interval !== null) {
    clearInterval(_interval);
    _interval = null;
  }
  _streaming = false;
  _provider = 'none';
}

/**
 * Returns the current streaming state.
 * @returns {{ streaming: boolean, provider: string }}
 */
function status() {
  return { streaming: _streaming, provider: _provider };
}

module.exports = { subscribe, unsubscribe, status };
