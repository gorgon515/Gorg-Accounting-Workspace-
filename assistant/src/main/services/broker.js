'use strict';

// Broker connection — Alpaca. Lets the user connect a real trading account
// (paper or live) with an API key/secret. The secret is stored encrypted via
// store.setSecret and never returned to the renderer.
//
// SAFETY: this does not change the approval model. The brain still only stages
// orders; a human still clicks Approve. When a broker is connected, Approve
// places the order through Alpaca instead of the simulator. Paper is the
// default; live requires the user to explicitly choose "live" and is flagged in
// the UI before every fill.

const store = require('../store');

// cfg = { provider:'alpaca', keyId, mode:'paper'|'live' }
const cfg = () => store.get('brokerCfg', null);
const secret = () => store.getSecret('brokerSecret');
const isConnected = () => Boolean(cfg() && cfg().keyId && secret());
const mode = () => cfg()?.mode || null;

function baseUrl() {
  return mode() === 'live' ? 'https://api.alpaca.markets' : 'https://paper-api.alpaca.markets';
}

function headers() {
  return {
    'APCA-API-KEY-ID': cfg().keyId,
    'APCA-API-SECRET-KEY': secret(),
    'Content-Type': 'application/json',
  };
}

async function af(path, opts = {}) {
  const res = await fetch(baseUrl() + path, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Alpaca ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.status === 204 ? null : res.json();
}

function mask(k) {
  return k ? `${k.slice(0, 4)}…${k.slice(-3)}` : '';
}

// Validate credentials by hitting /v2/account; persist only on success.
async function connect({ keyId, secret: sec, mode: m }) {
  keyId = String(keyId || '').trim();
  sec = String(sec || '').trim();
  m = m === 'live' ? 'live' : 'paper';
  if (!keyId || !sec) throw new Error('Key ID and secret are required.');
  store.set('brokerCfg', { provider: 'alpaca', keyId, mode: m });
  store.setSecret('brokerSecret', sec);
  try {
    await getAccount(); // throws if invalid
    return status();
  } catch (e) {
    disconnect();
    throw new Error('Connection failed — check the key, secret, and paper/live mode. ' + e.message);
  }
}

function disconnect() {
  store.set('brokerCfg', null);
  store.setSecret('brokerSecret', null);
  return { connected: false };
}

const getAccount = () => af('/v2/account');
const getPositions = () => af('/v2/positions');
const getOrders = () => af('/v2/orders?status=all&limit=50&direction=desc');
const placeOrder = ({ side, symbol, qty }) =>
  af('/v2/orders', {
    method: 'POST',
    body: JSON.stringify({
      symbol: String(symbol).toUpperCase(),
      qty: String(qty),
      side,
      type: 'market',
      time_in_force: 'day',
    }),
  });

async function status() {
  if (!isConnected()) return { connected: false };
  const base = { connected: true, provider: 'alpaca', mode: mode(), keyMasked: mask(cfg().keyId) };
  try {
    const a = await getAccount();
    return {
      ...base,
      account: {
        cash: Number(a.cash),
        portfolioValue: Number(a.portfolio_value),
        buyingPower: Number(a.buying_power),
        status: a.status,
      },
    };
  } catch (e) {
    return { ...base, error: e.message };
  }
}

module.exports = {
  isConnected,
  mode,
  connect,
  disconnect,
  status,
  getAccount,
  getPositions,
  getOrders,
  placeOrder,
};
