'use strict';

// Trading skill — PAPER TRADING with a hard human-approval gate.
//
// Safety model (the whole point of this module):
//   • Default mode is "paper": a simulated cash account. No real brokerage,
//     no real money. Starting cash is $100,000.
//   • The Claude brain can ONLY *propose* a trade. `propose_trade` stages a
//     pending order and returns it — it never moves cash or shares.
//   • A trade is filled ONLY when a human explicitly approves it via the
//     `approve()` path (wired to an Approve button in the UI). The brain has
//     no tool that executes — it is structurally incapable of trading on its
//     own. This is the human-in-the-loop guarantee.
//   • Real-money brokerage (e.g. Alpaca) would slot in behind `fill()` and
//     stay gated behind the same approval + paper-mode default. Not enabled.

const store = require('../store');
const stocks = require('./stocks');
const broker = require('./broker');

function freshAccount() {
  return { mode: 'paper', cash: 100000, positions: {}, history: [] };
}

function account() {
  return store.get('account', freshAccount());
}
function saveAccount(a) {
  return store.set('account', a);
}

// Pending orders live in memory only: if the app restarts before approval,
// the proposal is discarded rather than silently surviving. Safe default.
const pending = new Map();

function newId() {
  return 'ord_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

async function getPortfolio() {
  // Connected broker is the source of truth for the portfolio.
  if (broker.isConnected()) {
    const [a, pos] = await Promise.all([broker.getAccount(), broker.getPositions()]);
    const positions = (pos || []).map((p) => ({
      symbol: p.symbol,
      qty: Number(p.qty),
      avgCost: Number(p.avg_entry_price),
      price: Number(p.current_price),
      value: Number(p.market_value),
      unrealized: Number(p.unrealized_pl),
      unrealizedPct: Number(p.unrealized_plpc) * 100,
    }));
    return {
      mode: broker.mode() === 'live' ? 'live' : 'paper-broker',
      cash: Number(a.cash),
      holdingsValue: positions.reduce((s, x) => s + (x.value || 0), 0),
      totalValue: Number(a.portfolio_value),
      positions,
    };
  }

  const a = account();
  const symbols = Object.keys(a.positions);
  const quotes = symbols.length ? await stocks.api.getQuotes(symbols) : [];
  const bySym = Object.fromEntries(quotes.map((q) => [q.symbol, q]));

  let holdingsValue = 0;
  const positions = symbols.map((sym) => {
    const p = a.positions[sym];
    const price = bySym[sym]?.price ?? null;
    const value = price != null ? price * p.qty : null;
    if (value != null) holdingsValue += value;
    const cost = p.avgCost * p.qty;
    return {
      symbol: sym,
      qty: p.qty,
      avgCost: p.avgCost,
      price,
      value,
      unrealized: value != null ? value - cost : null,
      unrealizedPct: value != null && cost ? ((value - cost) / cost) * 100 : null,
    };
  });

  return {
    mode: a.mode,
    cash: a.cash,
    holdingsValue,
    totalValue: a.cash + holdingsValue,
    positions,
  };
}

// Stage an order for approval. Does NOT execute. Returns the pending order.
async function proposeTrade({ side, symbol, qty }) {
  side = String(side || '').toLowerCase();
  symbol = String(symbol || '').trim().toUpperCase();
  qty = Number(qty);
  if (!['buy', 'sell'].includes(side)) throw new Error('side must be "buy" or "sell"');
  if (!Number.isFinite(qty) || qty <= 0) throw new Error('qty must be a positive number');

  const quote = await stocks.api.getQuote(symbol); // validates the ticker
  const estPrice = quote.price;
  const a = account();
  const warnings = [];
  if (side === 'buy' && estPrice * qty > a.cash) {
    warnings.push('Estimated cost exceeds available cash.');
  }
  if (side === 'sell') {
    const held = a.positions[symbol]?.qty || 0;
    if (qty > held) warnings.push(`You only hold ${held} share(s) of ${symbol}.`);
  }

  const venue = broker.isConnected() ? `alpaca-${broker.mode()}` : 'paper-sim';
  const live = broker.isConnected() && broker.mode() === 'live';
  const order = {
    id: newId(),
    side,
    symbol,
    qty,
    name: quote.name,
    estPrice,
    estValue: estPrice * qty,
    currency: quote.currency,
    status: 'pending',
    venue,
    live,
    createdAt: new Date().toISOString(),
    warnings,
  };
  pending.set(order.id, order);
  return order;
}

function listPending() {
  return [...pending.values()];
}

function recordHistory(a, entry) {
  a.history.unshift(entry);
  if (a.history.length > 100) a.history.length = 100;
}

// Fill an order against the CURRENT live price. Called only on human approval.
async function approve(id) {
  const order = pending.get(id);
  if (!order) throw new Error('No pending order with that id (it may have expired).');

  // Connected broker: submit a real market order. Fills are async at the broker,
  // so we record it as "submitted" and let the portfolio reflect the result.
  if (broker.isConnected()) {
    const placed = await broker.placeOrder({ side: order.side, symbol: order.symbol, qty: order.qty });
    order.status = 'submitted';
    order.brokerOrderId = placed?.id || null;
    order.submittedAt = new Date().toISOString();
    const a = account();
    recordHistory(a, {
      id: order.id,
      side: order.side,
      symbol: order.symbol,
      qty: order.qty,
      price: order.estPrice,
      status: 'submitted',
      venue: order.venue,
      brokerOrderId: order.brokerOrderId,
      at: order.submittedAt,
    });
    saveAccount(a);
    pending.delete(id);
    return { order, portfolio: await getPortfolio() };
  }

  const quote = await stocks.api.getQuote(order.symbol); // re-price at fill time (sim)
  const fillPrice = quote.price;
  const a = account();
  const cost = fillPrice * order.qty;

  if (order.side === 'buy') {
    if (cost > a.cash) {
      pending.delete(id);
      recordHistory(a, histEntry(order, fillPrice, 'rejected', 'Insufficient cash at fill'));
      saveAccount(a);
      throw new Error('Insufficient cash to fill at current price.');
    }
    a.cash -= cost;
    const pos = a.positions[order.symbol] || { qty: 0, avgCost: 0 };
    const newQty = pos.qty + order.qty;
    pos.avgCost = (pos.avgCost * pos.qty + cost) / newQty;
    pos.qty = newQty;
    a.positions[order.symbol] = pos;
  } else {
    const pos = a.positions[order.symbol];
    if (!pos || pos.qty < order.qty) {
      pending.delete(id);
      recordHistory(a, histEntry(order, fillPrice, 'rejected', 'Insufficient shares at fill'));
      saveAccount(a);
      throw new Error('Insufficient shares to fill.');
    }
    a.cash += cost;
    pos.qty -= order.qty;
    if (pos.qty === 0) delete a.positions[order.symbol];
  }

  order.status = 'filled';
  order.fillPrice = fillPrice;
  order.filledAt = new Date().toISOString();
  recordHistory(a, histEntry(order, fillPrice, 'filled'));
  saveAccount(a);
  pending.delete(id);
  return { order, portfolio: await getPortfolio() };
}

function reject(id) {
  const order = pending.get(id);
  if (!order) throw new Error('No pending order with that id.');
  pending.delete(id);
  order.status = 'rejected';
  const a = account();
  recordHistory(a, histEntry(order, order.estPrice, 'rejected', 'Rejected by user'));
  saveAccount(a);
  return order;
}

function histEntry(order, price, status, reason) {
  return {
    id: order.id,
    side: order.side,
    symbol: order.symbol,
    qty: order.qty,
    price,
    value: price * order.qty,
    status,
    reason,
    at: new Date().toISOString(),
  };
}

function getOrders() {
  return account().history;
}

function resetAccount() {
  pending.clear();
  return saveAccount(freshAccount());
}

// --- Brain tools. Note: there is deliberately NO execute/fill tool. ---
const tools = [
  {
    name: 'get_portfolio',
    description:
      'Get the paper-trading account: cash, holdings, each position\'s live value and unrealized P/L, and total account value. Call when the user asks about their portfolio, balance, or how their positions are doing.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'propose_trade',
    description:
      'Stage a buy or sell order for the user to review and approve. This DOES NOT execute the trade — it only creates a pending order that the user must explicitly approve in the Trading panel. Call this when the user asks to buy or sell a stock. After calling it, tell the user the order is staged and waiting for their approval; never say the trade was completed.',
    input_schema: {
      type: 'object',
      properties: {
        side: { type: 'string', enum: ['buy', 'sell'] },
        symbol: { type: 'string', description: 'Ticker symbol, e.g. AAPL' },
        qty: { type: 'number', description: 'Number of shares' },
      },
      required: ['side', 'symbol', 'qty'],
    },
  },
  {
    name: 'get_orders',
    description: 'Get recent filled and rejected orders (trade history) for the paper account.',
    input_schema: { type: 'object', properties: {} },
  },
];

const handlers = {
  get_portfolio: () => getPortfolio(),
  propose_trade: (input) => proposeTrade(input),
  get_orders: async () => getOrders(),
};

module.exports = {
  name: 'trading',
  systemPromptFragment:
    'You manage the user\'s trading account. By default it is a PAPER (simulated) account; if the user has connected a broker (Alpaca) it may be a paper or LIVE real-money account. You can read the portfolio and trade history, and you can STAGE buy/sell orders with propose_trade. ' +
    'Staging is not executing: every order must be explicitly approved by the user in the Trading panel before any shares or cash move — this is true for the simulator AND for a connected real account. ' +
    'When you stage an order, clearly tell the user it is pending their approval and restate the side, quantity, symbol, and estimated cost. If the account is live, remind them it is a real-money order. Never claim a trade executed. ' +
    'You are not a licensed financial advisor — explain and summarize, but do not tell the user to buy or sell, and add a brief "not financial advice" note when they ask what to do.',
  tools,
  handlers,
  api: {
    getPortfolio,
    proposeTrade,
    listPending,
    approve,
    reject,
    getOrders,
    resetAccount,
  },
};
