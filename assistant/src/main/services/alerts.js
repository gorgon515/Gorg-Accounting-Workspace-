'use strict';

// Price alerts — notify when a ticker crosses an above/below threshold.
//
// A background checker (started from main.js) polls quotes on an interval and
// fires once per alert. The brain can set alerts by voice; the main process
// turns a trigger into an OS notification + an in-app message.

const store = require('../store');
const stocks = require('./stocks');

function alerts() {
  return store.get('alerts', []);
}
function save(a) {
  return store.set('alerts', a);
}
function newId() {
  return 'alt_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

function addAlert({ symbol, direction, price }) {
  symbol = String(symbol || '').trim().toUpperCase();
  direction = String(direction || '').toLowerCase();
  price = Number(price);
  if (!symbol) throw new Error('symbol is required');
  if (!['above', 'below'].includes(direction)) throw new Error('direction must be "above" or "below"');
  if (!Number.isFinite(price) || price <= 0) throw new Error('price must be a positive number');
  const list = alerts();
  const a = {
    id: newId(),
    symbol,
    direction,
    price,
    active: true,
    createdAt: new Date().toISOString(),
  };
  list.push(a);
  save(list);
  return a;
}

function listAlerts() {
  return alerts();
}

function removeAlert({ id, symbol }) {
  const list = alerts();
  let target = id ? list.find((a) => a.id === id) : null;
  if (!target && symbol) target = list.find((a) => a.symbol === String(symbol).toUpperCase());
  if (!target) throw new Error('No matching alert found.');
  save(list.filter((a) => a.id !== target.id));
  return { removed: target.id };
}

// Evaluate all active alerts against live prices. Returns the ones that fired.
async function checkNow() {
  const list = alerts();
  const active = list.filter((a) => a.active);
  if (!active.length) return [];
  const symbols = [...new Set(active.map((a) => a.symbol))];
  let quotes;
  try {
    quotes = await stocks.api.getQuotes(symbols);
  } catch {
    return []; // market feed unreachable; try again next tick
  }
  const price = Object.fromEntries(quotes.filter((q) => !q.error).map((q) => [q.symbol, q.price]));
  const fired = [];
  for (const a of active) {
    const p = price[a.symbol];
    if (p == null) continue;
    const hit = a.direction === 'above' ? p >= a.price : p <= a.price;
    if (hit) {
      a.active = false; // fire once, then go dormant
      a.triggeredAt = new Date().toISOString();
      a.triggeredPrice = p;
      fired.push({ ...a });
    }
  }
  if (fired.length) save(list);
  return fired;
}

// Poll loop. onTrigger(alert) is called for each newly-fired alert.
function startChecker({ intervalMs = 60000, onTrigger } = {}) {
  const tick = async () => {
    const fired = await checkNow();
    for (const a of fired) {
      try { if (onTrigger) onTrigger(a); } catch { /* ignore */ }
    }
  };
  const handle = setInterval(tick, intervalMs);
  tick(); // run once immediately
  return () => clearInterval(handle);
}

const tools = [
  {
    name: 'set_alert',
    description: 'Create a price alert that notifies the user when a ticker goes above or below a target price. Call when the user asks to be alerted/notified/told when a stock hits a price.',
    input_schema: {
      type: 'object',
      properties: {
        symbol: { type: 'string', description: 'Ticker symbol' },
        direction: { type: 'string', enum: ['above', 'below'] },
        price: { type: 'number', description: 'Target price' },
      },
      required: ['symbol', 'direction', 'price'],
    },
  },
  {
    name: 'list_alerts',
    description: 'List the user\'s price alerts (active and already-triggered).',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'remove_alert',
    description: 'Delete a price alert by id or symbol.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, symbol: { type: 'string' } },
    },
  },
];

const handlers = {
  set_alert: (i) => addAlert(i),
  list_alerts: async () => listAlerts(),
  remove_alert: (i) => removeAlert(i),
};

module.exports = {
  name: 'alerts',
  systemPromptFragment:
    'You can set, list, and remove stock price alerts. An alert fires once when the ticker crosses the target (above or below) and the user gets a desktop notification. When the user asks to be notified about a price, call set_alert and confirm the symbol, direction, and price.',
  tools,
  handlers,
  api: { addAlert, listAlerts, removeAlert, checkNow, startChecker },
};
