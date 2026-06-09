'use strict';

// Renderer controller. Talks to the main process only through window.aria
// (the preload bridge). No Node access here.

const aria = window.aria;

const els = {
  brainDot: document.getElementById('brain-dot'),
  brainLabel: document.getElementById('brain-label'),
  transcript: document.getElementById('transcript'),
  composer: document.getElementById('composer'),
  composerInput: document.getElementById('composer-input'),
  micBtn: document.getElementById('mic-btn'),
  voiceHint: document.getElementById('voice-hint'),
  watchlist: document.getElementById('watchlist'),
  addInput: document.getElementById('add-input'),
  addBtn: document.getElementById('add-btn'),
  refreshBtn: document.getElementById('refresh-btn'),
  searchInput: document.getElementById('search-input'),
  searchBtn: document.getElementById('search-btn'),
  results: document.getElementById('results'),
  approvals: document.getElementById('approvals'),
  positions: document.getElementById('positions'),
  portfolioTotal: document.getElementById('portfolio-total'),
  tradeMode: document.getElementById('trade-mode'),
  orderForm: document.getElementById('order-form'),
  orderSide: document.getElementById('order-side'),
  orderSymbol: document.getElementById('order-symbol'),
  orderQty: document.getElementById('order-qty'),
  briefBtn: document.getElementById('brief-btn'),
  taskForm: document.getElementById('task-form'),
  taskInput: document.getElementById('task-input'),
  taskDue: document.getElementById('task-due'),
  tasklist: document.getElementById('tasklist'),
  taskCount: document.getElementById('task-count'),
};

let chatHistory = [];
let voice = null;
let cfg = { hasBrain: false, wakeWord: 'aria' };

// ---- helpers ----
const fmtPrice = (q) =>
  q.price != null ? `${q.price.toFixed(2)} ${q.currency || ''}`.trim() : '—';
const fmtChg = (q) => {
  if (q.change == null) return '';
  const sign = q.change >= 0 ? '+' : '';
  return `${sign}${q.change.toFixed(2)} (${sign}${q.changePercent.toFixed(2)}%)`;
};

function quoteRow(q, { removable = false, clickable = false } = {}) {
  const row = document.createElement('div');
  row.className = 'row' + (clickable ? ' clickable' : '');
  if (q.error) {
    row.innerHTML = `<div class="left"><span class="sym">${q.symbol}</span>
      <span class="name err">${q.error}</span></div>`;
    return row;
  }
  const dir = q.change >= 0 ? 'up' : 'down';
  row.innerHTML = `
    <div class="left">
      <span class="sym">${q.symbol}</span>
      <span class="name">${q.name || ''}</span>
    </div>
    <div class="right">
      <span class="price">${fmtPrice(q)}</span>
      <span class="chg ${dir}">${fmtChg(q)}</span>
      ${removable ? '<button class="x" title="Remove">✕</button>' : ''}
    </div>`;
  if (removable) {
    row.querySelector('.x').addEventListener('click', async (e) => {
      e.stopPropagation();
      await aria.stocks.removeFromWatchlist(q.symbol);
      loadWatchlist();
    });
  }
  if (clickable) {
    row.addEventListener('click', async () => {
      await aria.stocks.addToWatchlist(q.symbol);
      loadWatchlist();
    });
  }
  return row;
}

// ---- chat ----
function appendMsg(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  els.transcript.appendChild(div);
  els.transcript.scrollTop = els.transcript.scrollHeight;
  return div;
}

async function sendToBrain(text) {
  appendMsg('user', text);
  const pending = appendMsg('assistant', '…');
  try {
    const res = await aria.ask(text, chatHistory);
    chatHistory = res.history || chatHistory;
    pending.textContent = res.text || '(no reply)';
    if (res.toolEvents && res.toolEvents.length) {
      const tools = res.toolEvents.map((t) => t.name).join(', ');
      const tdiv = document.createElement('div');
      tdiv.className = 'msg tool';
      tdiv.textContent = `↳ used: ${tools}`;
      els.transcript.insertBefore(tdiv, pending);
    }
    if (res.ok && voice && voice.isListening && voice.isListening()) voice.speak(res.text);
    // Refresh panels in case the brain changed the watchlist, staged a trade,
    // or added/completed a task.
    loadWatchlist();
    refreshTrading();
    loadTasks();
  } catch (err) {
    pending.textContent = `Error: ${err.message}`;
  }
}

els.composer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = els.composerInput.value.trim();
  if (!text) return;
  els.composerInput.value = '';
  sendToBrain(text);
});

// ---- watchlist ----
async function loadWatchlist() {
  els.watchlist.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const quotes = await aria.stocks.watchlistQuotes();
    els.watchlist.innerHTML = '';
    if (!quotes.length) {
      els.watchlist.innerHTML = '<p class="muted">No tickers yet. Add one above.</p>';
      return;
    }
    quotes.forEach((q) => els.watchlist.appendChild(quoteRow(q, { removable: true })));
  } catch (err) {
    els.watchlist.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

async function addTicker() {
  const sym = els.addInput.value.trim();
  if (!sym) return;
  els.addInput.value = '';
  await aria.stocks.addToWatchlist(sym);
  loadWatchlist();
}
els.addBtn.addEventListener('click', addTicker);
els.addInput.addEventListener('keydown', (e) => e.key === 'Enter' && addTicker());
els.refreshBtn.addEventListener('click', loadWatchlist);

// ---- search ----
async function doSearch() {
  const q = els.searchInput.value.trim();
  if (!q) return;
  els.results.innerHTML = '<p class="muted">Searching…</p>';
  try {
    const matches = await aria.stocks.search(q);
    els.results.innerHTML = '';
    if (!matches.length) {
      els.results.innerHTML = '<p class="muted">No matches.</p>';
      return;
    }
    // Resolve to live quotes so the user sees a price; click to add.
    const quotes = await aria.stocks.quotes(matches.slice(0, 6).map((m) => m.symbol));
    quotes.forEach((qt) => els.results.appendChild(quoteRow(qt, { clickable: true })));
    const tip = document.createElement('p');
    tip.className = 'muted';
    tip.textContent = 'Click a result to add it to your watchlist.';
    els.results.appendChild(tip);
  } catch (err) {
    els.results.innerHTML = `<p class="err">${err.message}</p>`;
  }
}
els.searchBtn.addEventListener('click', doSearch);
els.searchInput.addEventListener('keydown', (e) => e.key === 'Enter' && doSearch());

// ---- trading (paper, approval-gated) ----
const money = (n, cur) =>
  n == null ? '—' : `${n.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${cur || ''}`.trim();

function approvalCard(o) {
  const card = document.createElement('div');
  card.className = 'approval';
  const sideLabel = o.side.toUpperCase();
  const warnHtml = (o.warnings || [])
    .map((w) => `<div class="warn">⚠ ${w}</div>`)
    .join('');
  card.innerHTML = `
    <div class="head">
      <span class="deal">${sideLabel} ${o.qty} ${o.symbol}</span>
      <span class="est">~${money(o.estPrice, o.currency)}/sh</span>
    </div>
    <div class="est">Est. ${o.side === 'buy' ? 'cost' : 'proceeds'}: ${money(o.estValue, o.currency)} · ${o.name || ''}</div>
    ${warnHtml}
    <div class="acts">
      <button class="approve">Approve</button>
      <button class="reject">Reject</button>
    </div>`;
  card.querySelector('.approve').addEventListener('click', async () => {
    card.querySelector('.approve').disabled = true;
    try {
      const { order } = await aria.trading.approve(o.id);
      appendMsg('tool', `✓ Filled: ${order.side} ${order.qty} ${order.symbol} @ ${money(order.fillPrice, order.currency)}`);
    } catch (err) {
      appendMsg('tool', `✗ ${err.message}`);
    }
    refreshTrading();
  });
  card.querySelector('.reject').addEventListener('click', async () => {
    try { await aria.trading.reject(o.id); } catch {}
    refreshTrading();
  });
  return card;
}

function positionRow(p) {
  const row = document.createElement('div');
  row.className = 'pos-row';
  const pl = p.unrealized;
  const plClass = pl == null ? '' : pl >= 0 ? 'up' : 'down';
  const plTxt =
    pl == null ? '' : `${pl >= 0 ? '+' : ''}${pl.toFixed(2)} (${p.unrealizedPct >= 0 ? '+' : ''}${(p.unrealizedPct ?? 0).toFixed(1)}%)`;
  row.innerHTML = `
    <div>
      <div class="sym">${p.qty} ${p.symbol}</div>
      <div class="meta">avg ${p.avgCost.toFixed(2)} · now ${p.price != null ? p.price.toFixed(2) : '—'}</div>
    </div>
    <div class="pl chg ${plClass}">${plTxt}</div>`;
  return row;
}

async function refreshTrading() {
  try {
    const [pending, portfolio] = await Promise.all([
      aria.trading.pending(),
      aria.trading.portfolio(),
    ]);
    els.tradeMode.textContent = portfolio.mode;
    els.portfolioTotal.textContent = `${money(portfolio.totalValue)} · cash ${money(portfolio.cash)}`;

    els.approvals.innerHTML = '';
    pending.forEach((o) => els.approvals.appendChild(approvalCard(o)));

    els.positions.innerHTML = '';
    if (!portfolio.positions.length) {
      els.positions.innerHTML = '<p class="muted">No positions yet.</p>';
    } else {
      portfolio.positions.forEach((p) => els.positions.appendChild(positionRow(p)));
    }
  } catch (err) {
    els.portfolioTotal.textContent = '—';
  }
}

els.orderForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const side = els.orderSide.value;
  const symbol = els.orderSymbol.value.trim();
  const qty = Number(els.orderQty.value);
  if (!symbol || !qty) return;
  try {
    await aria.trading.propose({ side, symbol, qty });
    els.orderSymbol.value = '';
    els.orderQty.value = '';
    refreshTrading();
  } catch (err) {
    appendMsg('tool', `✗ ${err.message}`);
  }
});

// ---- tasks ----
const TODAY = new Date().toISOString().slice(0, 10);

function taskRow(t) {
  const row = document.createElement('div');
  row.className = 'task';
  let dueTxt = '';
  let dueCls = '';
  if (t.due) {
    dueCls = t.due < TODAY ? 'over' : t.due === TODAY ? 'today' : '';
    dueTxt = t.due < TODAY ? `overdue · ${t.due}` : t.due === TODAY ? 'today' : t.due;
  }
  row.innerHTML = `
    <button class="check" title="Mark done"></button>
    <div class="body">
      <div class="t-text">${escapeHtml(t.text)}</div>
      ${dueTxt ? `<div class="t-due ${dueCls}">${dueTxt}</div>` : ''}
    </div>
    <button class="t-del" title="Delete">✕</button>`;
  row.querySelector('.check').addEventListener('click', async () => {
    await aria.productivity.completeTask(t.id);
    loadTasks();
  });
  row.querySelector('.t-del').addEventListener('click', async () => {
    await aria.productivity.deleteTask(t.id);
    loadTasks();
  });
  return row;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

async function loadTasks() {
  try {
    const tasks = await aria.productivity.tasks('open');
    els.taskCount.textContent = tasks.length ? `${tasks.length} open` : '';
    els.tasklist.innerHTML = '';
    if (!tasks.length) {
      els.tasklist.innerHTML = '<p class="muted">Nothing open. Add a task above.</p>';
      return;
    }
    // Overdue first, then by due date, then undated.
    tasks.sort((a, b) => (a.due || '9999') < (b.due || '9999') ? -1 : 1);
    tasks.forEach((t) => els.tasklist.appendChild(taskRow(t)));
  } catch (err) {
    els.tasklist.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.taskForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = els.taskInput.value.trim();
  if (!text) return;
  const due = els.taskDue.value.trim();
  els.taskInput.value = '';
  els.taskDue.value = '';
  await aria.productivity.addTask({ text, due });
  loadTasks();
});

// ---- daily briefing ----
els.briefBtn.addEventListener('click', async () => {
  if (cfg.hasBrain) {
    // Let the brain compose and (if voice is on) speak it.
    sendToBrain('Give me my daily briefing.');
  } else {
    // Brain offline: render the raw briefing locally.
    try {
      const b = await aria.productivity.briefing();
      const lines = [`${b.greeting}. ${b.date}.`];
      if (b.tasks.overdue.length) lines.push(`Overdue: ${b.tasks.overdue.join('; ')}.`);
      if (b.tasks.dueToday.length) lines.push(`Due today: ${b.tasks.dueToday.join('; ')}.`);
      lines.push(`${b.tasks.openCount} open task(s).`);
      if (b.market.movers.length) {
        lines.push('Movers: ' + b.market.movers
          .map((m) => `${m.symbol} ${m.changePercent >= 0 ? '+' : ''}${m.changePercent.toFixed(1)}%`)
          .join(', ') + '.');
      }
      if (b.portfolio) lines.push(`Portfolio ~${money(b.portfolio.totalValue)}.`);
      appendMsg('assistant', lines.join(' '));
    } catch (err) {
      appendMsg('assistant', `Couldn't build briefing: ${err.message}`);
    }
  }
});

// ---- voice ----
function setVoiceHint(state) {
  const map = {
    listening: `Listening — say "${cfg.wakeWord}" then your question.`,
    awake: 'Yes? Go ahead…',
    heard: 'Thinking…',
    off: '',
    denied: 'Microphone permission denied. Check OS/app mic settings.',
  };
  els.voiceHint.textContent = map[state] ?? '';
  if (state === 'listening' || state === 'awake' || state === 'heard') {
    els.micBtn.classList.add('live');
    els.micBtn.textContent = '🎙 Voice: on';
  } else {
    els.micBtn.classList.remove('live');
    els.micBtn.textContent = '🎙 Voice: off';
  }
}

function initVoice() {
  voice = window.createVoice({
    wakeWord: cfg.wakeWord,
    onCommand: (cmd) => sendToBrain(cmd),
    onState: setVoiceHint,
  });
  if (!voice.supported) {
    els.micBtn.disabled = true;
    els.micBtn.textContent = '🎙 Voice: n/a';
    els.voiceHint.textContent = 'Speech recognition not available in this build.';
    return;
  }
  els.micBtn.addEventListener('click', () => voice.toggle());
}

// ---- boot ----
async function boot() {
  try {
    cfg = await aria.config();
  } catch {}
  if (cfg.hasBrain) {
    els.brainDot.classList.add('on');
    els.brainLabel.textContent = `brain online · ${cfg.model}`;
  } else {
    els.brainDot.classList.add('off');
    els.brainLabel.textContent = 'brain offline · add API key';
    appendMsg(
      'assistant',
      'Hi — I\'m ARIA. The AI brain is offline (no API key), but the Stocks panels work now: ' +
        'try adding a ticker or searching a company. Add ANTHROPIC_API_KEY to .env to unlock chat and voice.'
    );
  }
  initVoice();
  loadWatchlist();
  refreshTrading();
  loadTasks();
  // Keep pending approvals and live P/L fresh.
  setInterval(refreshTrading, 15000);
}

boot();
