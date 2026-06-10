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
  talkBtn: document.getElementById('talk-btn'),
  taskForm: document.getElementById('task-form'),
  taskInput: document.getElementById('task-input'),
  taskDue: document.getElementById('task-due'),
  tasklist: document.getElementById('tasklist'),
  taskCount: document.getElementById('task-count'),
  chartCanvas: document.getElementById('chart-canvas'),
  chartSymbol: document.getElementById('chart-symbol'),
  chartMeta: document.getElementById('chart-meta'),
  chartRanges: document.getElementById('chart-ranges'),
  newsSymbol: document.getElementById('news-symbol'),
  newslist: document.getElementById('newslist'),
  alertForm: document.getElementById('alert-form'),
  alertSymbol: document.getElementById('alert-symbol'),
  alertDir: document.getElementById('alert-dir'),
  alertPrice: document.getElementById('alert-price'),
  alertlist: document.getElementById('alertlist'),
  agenda: document.getElementById('agenda'),
  inboxCount: document.getElementById('inbox-count'),
  googleStatus: document.getElementById('google-status'),
  googleBtn: document.getElementById('google-btn'),
  brokerStatus: document.getElementById('broker-status'),
  brokerForm: document.getElementById('broker-form'),
  brokerMode: document.getElementById('broker-mode'),
  brokerKey: document.getElementById('broker-key'),
  brokerSecret: document.getElementById('broker-secret'),
  brokerNote: document.getElementById('broker-note'),
  brokerDisconnect: document.getElementById('broker-disconnect'),
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

function quoteRow(q, { removable = false, clickable = false, onSelect = null } = {}) {
  const row = document.createElement('div');
  row.className = 'row' + (clickable || onSelect ? ' clickable' : '');
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
  if (onSelect) {
    row.addEventListener('click', () => onSelect(q.symbol));
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
    loadAlerts();
    loadAgenda();
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
    quotes.forEach((q) =>
      els.watchlist.appendChild(quoteRow(q, { removable: true, onSelect: setChart }))
    );
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
  card.className = 'approval' + (o.live ? ' live' : '');
  const sideLabel = o.side.toUpperCase();
  const warnHtml = (o.warnings || [])
    .map((w) => `<div class="warn">⚠ ${w}</div>`)
    .join('');
  const liveTag = o.live ? ' <span class="live-tag">live · real money</span>' : '';
  card.innerHTML = `
    <div class="head">
      <span class="deal">${sideLabel} ${o.qty} ${o.symbol}${liveTag}</span>
      <span class="est">~${money(o.estPrice, o.currency)}/sh</span>
    </div>
    <div class="est">Est. ${o.side === 'buy' ? 'cost' : 'proceeds'}: ${money(o.estValue, o.currency)} · ${o.name || ''}</div>
    ${warnHtml}
    <div class="acts">
      <button class="approve">Approve</button>
      <button class="reject">Reject</button>
    </div>`;
  card.querySelector('.approve').addEventListener('click', async () => {
    // Real-money orders get a second, explicit confirmation at approval time.
    if (o.live) {
      const ok = confirm(
        `Execute LIVE real-money order:\n\n${o.side.toUpperCase()} ${o.qty} ${o.symbol} (~${money(o.estValue, o.currency)})\n\n` +
        'This sends a real order to your broker and cannot be undone here. Continue?'
      );
      if (!ok) return;
    }
    card.querySelector('.approve').disabled = true;
    try {
      const { order } = await aria.trading.approve(o.id);
      const verb = order.status === 'submitted' ? 'Submitted' : 'Filled';
      const at = order.fillPrice != null ? ` @ ${money(order.fillPrice, order.currency)}` : '';
      appendMsg('tool', `✓ ${verb}: ${order.side} ${order.qty} ${order.symbol}${at}`);
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

// ---- chart ----
const chartState = { symbol: null, range: '1mo' };

function drawChart(points) {
  const cv = els.chartCanvas;
  const ctx = cv.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || 320;
  const h = cv.clientHeight || 150;
  cv.width = w * dpr;
  cv.height = h * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (!points || points.length < 2) return;

  const vals = points.map((p) => p.close);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const pad = 6;
  const x = (i) => pad + (i / (points.length - 1)) * (w - 2 * pad);
  const y = (v) => (max === min ? h / 2 : pad + (1 - (v - min) / (max - min)) * (h - 2 * pad));
  const up = vals[vals.length - 1] >= vals[0];
  const color = up ? '#6FA98C' : '#C97A6A';

  // line
  ctx.beginPath();
  points.forEach((p, i) => {
    const X = x(i);
    const Y = y(p.close);
    i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // soft fill under the line
  ctx.lineTo(x(points.length - 1), h - pad);
  ctx.lineTo(x(0), h - pad);
  ctx.closePath();
  ctx.fillStyle = up ? 'rgba(111,169,140,0.08)' : 'rgba(201,122,106,0.08)';
  ctx.fill();
}

async function loadChart() {
  if (!chartState.symbol) return;
  els.chartSymbol.textContent = chartState.symbol;
  els.chartMeta.textContent = 'Loading…';
  try {
    const hist = await aria.stocks.history(chartState.symbol, chartState.range);
    if (!hist.points || !hist.points.length) {
      els.chartMeta.textContent = 'No data.';
      drawChart([]);
      return;
    }
    drawChart(hist.points);
    const first = hist.points[0].close;
    const last = hist.points[hist.points.length - 1].close;
    const chg = last - first;
    const pct = first ? (chg / first) * 100 : 0;
    els.chartMeta.textContent =
      `${chartState.range} · ${last.toFixed(2)} (${chg >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
  } catch (err) {
    els.chartMeta.textContent = err.message;
  }
}

function setChart(symbol) {
  chartState.symbol = symbol;
  loadChart();
  loadNews(symbol);
}

function relTime(iso) {
  if (!iso) return '';
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

async function loadNews(symbol) {
  els.newsSymbol.textContent = symbol || '';
  els.newslist.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const items = await aria.stocks.news(symbol);
    els.newslist.innerHTML = '';
    if (!items.length) {
      els.newslist.innerHTML = '<p class="muted">No recent headlines.</p>';
      return;
    }
    items.forEach((n) => {
      const el = document.createElement('div');
      el.className = 'news-item';
      // target=_blank routes through the main process to the system browser.
      el.innerHTML = `
        <a href="${n.link}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a>
        <div class="meta">${escapeHtml(n.publisher || '')}${n.time ? ' · ' + relTime(n.time) : ''}</div>`;
      els.newslist.appendChild(el);
    });
  } catch (err) {
    els.newslist.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.chartRanges.addEventListener('click', (e) => {
  const btn = e.target.closest('.r-btn');
  if (!btn) return;
  els.chartRanges.querySelectorAll('.r-btn').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  chartState.range = btn.dataset.range;
  loadChart();
});
// Redraw on resize so the canvas stays crisp.
window.addEventListener('resize', () => chartState.symbol && loadChart());

// ---- price alerts ----
function alertRow(a) {
  const row = document.createElement('div');
  row.className = 'alert-row' + (a.active ? '' : ' fired');
  const state = a.active
    ? '<span class="a-state live">watching</span>'
    : `<span class="a-state fired">fired${a.triggeredPrice != null ? ' ' + a.triggeredPrice.toFixed(2) : ''}</span>`;
  row.innerHTML = `
    <span class="a-desc">${a.symbol} ${a.direction} ${a.price}</span>
    <div class="right">${state}<button class="a-del" title="Remove">✕</button></div>`;
  row.querySelector('.a-del').addEventListener('click', async () => {
    await aria.alerts.remove(a.id);
    loadAlerts();
  });
  return row;
}

// Short two-tone chime via Web Audio (no asset file needed).
function playAlertSound() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    [880, 1175].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.type = 'sine';
      const t = ctx.currentTime + i * 0.16;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.16);
    });
    setTimeout(() => ctx.close(), 600);
  } catch { /* audio unavailable */ }
}

async function loadAlerts() {
  try {
    const list = await aria.alerts.list();
    els.alertlist.innerHTML = '';
    if (!list.length) {
      els.alertlist.innerHTML = '<p class="muted">No alerts set.</p>';
      return;
    }
    list.sort((a, b) => (a.active === b.active ? 0 : a.active ? -1 : 1));
    list.forEach((a) => els.alertlist.appendChild(alertRow(a)));
  } catch (err) {
    els.alertlist.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.alertForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const symbol = els.alertSymbol.value.trim();
  const direction = els.alertDir.value;
  const price = Number(els.alertPrice.value);
  if (!symbol || !price) return;
  try {
    await aria.alerts.add({ symbol, direction, price });
    els.alertSymbol.value = '';
    els.alertPrice.value = '';
    loadAlerts();
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

// ---- connections: Google ----
async function loadGoogleStatus() {
  try {
    const s = await aria.google.status();
    if (!s.configured) {
      els.googleStatus.innerHTML = 'not configured';
      els.googleBtn.disabled = true;
      els.googleBtn.title = 'Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env';
    } else if (s.connected) {
      els.googleStatus.innerHTML = `<span class="ok">${escapeHtml(s.email || 'connected')}</span>`;
      els.googleBtn.textContent = 'Disconnect';
      els.googleBtn.dataset.connected = '1';
    } else {
      els.googleStatus.textContent = 'not connected';
      els.googleBtn.textContent = 'Connect';
      els.googleBtn.dataset.connected = '';
    }
  } catch {
    els.googleStatus.textContent = 'unavailable';
  }
}

els.googleBtn.addEventListener('click', async () => {
  if (els.googleBtn.dataset.connected) {
    await aria.google.disconnect();
    loadGoogleStatus();
    loadAgenda();
    return;
  }
  els.googleStatus.textContent = 'opening browser…';
  try {
    await aria.google.connect();
    await loadGoogleStatus();
    loadAgenda();
  } catch (err) {
    els.googleStatus.textContent = 'failed';
    appendMsg('tool', `✗ Google: ${err.message}`);
  }
});

// ---- connections: broker (trading account) ----
async function loadBrokerStatus() {
  try {
    const s = await aria.broker.status();
    if (s.connected) {
      const liveCls = s.mode === 'live' ? 'live' : 'ok';
      els.brokerStatus.innerHTML = `<span class="${liveCls}">${s.mode}</span> · ${escapeHtml(s.keyMasked || '')}`;
      els.brokerForm.style.display = 'none';
      els.brokerDisconnect.style.display = '';
      els.brokerNote.textContent = s.account
        ? `Value ${money(s.account.portfolioValue)} · cash ${money(s.account.cash)}`
        : s.error || '';
    } else {
      els.brokerStatus.textContent = 'paper simulator';
      els.brokerForm.style.display = '';
      els.brokerDisconnect.style.display = 'none';
      const enc = await aria.broker.encryptionAvailable();
      els.brokerNote.textContent = enc
        ? 'Alpaca key/secret, stored encrypted on this device.'
        : 'Note: OS secure storage unavailable — secret stored obfuscated, not encrypted.';
    }
  } catch {
    els.brokerStatus.textContent = 'unavailable';
  }
}

els.brokerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const mode = els.brokerMode.value;
  const keyId = els.brokerKey.value.trim();
  const secret = els.brokerSecret.value.trim();
  if (!keyId || !secret) return;
  if (mode === 'live' && !confirm('Connect a LIVE real-money account? Approved orders will execute for real.')) return;
  els.brokerNote.textContent = 'Connecting…';
  try {
    await aria.broker.connect({ keyId, secret, mode });
    els.brokerKey.value = '';
    els.brokerSecret.value = '';
    await loadBrokerStatus();
    refreshTrading();
    appendMsg('tool', `✓ Connected ${mode} trading account.`);
  } catch (err) {
    els.brokerNote.textContent = err.message;
  }
});

els.brokerDisconnect.addEventListener('click', async () => {
  await aria.broker.disconnect();
  await loadBrokerStatus();
  refreshTrading();
});

// ---- agenda (Google Calendar + unread count) ----
function evTime(iso) {
  if (!iso) return 'all day';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function loadAgenda() {
  const gs = await aria.google.status().catch(() => ({ connected: false }));
  if (!gs.connected) {
    els.agenda.innerHTML = '<p class="muted">Connect Google to see your day.</p>';
    els.inboxCount.textContent = '';
    return;
  }
  els.agenda.innerHTML = '<p class="muted">Loading…</p>';
  try {
    const [events, inbox] = await Promise.all([
      aria.google.agenda(),
      aria.google.inbox().catch(() => ({ unread: 0 })),
    ]);
    els.inboxCount.textContent = inbox.unread ? `${inbox.unread} unread` : 'inbox clear';
    els.agenda.innerHTML = '';
    if (!events.length) {
      els.agenda.innerHTML = '<p class="muted">No events today.</p>';
      return;
    }
    events.forEach((ev) => {
      const el = document.createElement('div');
      el.className = 'ev';
      el.innerHTML = `<span class="ev-time">${evTime(ev.start)}</span><span class="ev-title">${escapeHtml(ev.summary)}</span>`;
      els.agenda.appendChild(el);
    });
  } catch (err) {
    els.agenda.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

// ---- push-to-talk (Whisper STT) ----
let recorder = null;

function setTalkState(state) {
  const map = {
    recording: '● Recording — click to stop',
    transcribing: '… Transcribing',
    denied: '🎤 Mic blocked',
    error: '🎤 STT error',
    empty: '🎤 Talk',
    idle: '🎤 Talk',
  };
  els.talkBtn.textContent = map[state] || '🎤 Talk';
  els.talkBtn.classList.toggle('live', state === 'recording' || state === 'transcribing');
  if (state === 'denied') els.voiceHint.textContent = 'Microphone blocked — allow mic access for ARIA.';
  if (state === 'error') els.voiceHint.textContent = 'Transcription failed — check STT_API_KEY in .env.';
}

async function initTalk() {
  const sttInfo = await aria.stt.info().catch(() => ({ available: false, engine: 'vosk', local: true }));
  recorder = window.createRecorder({
    mode: sttInfo.engine === 'whisper-api' ? 'audio' : 'pcm16',
    onText: (text, err) => {
      if (err) { appendMsg('tool', `✗ STT: ${err.message}`); return; }
      if (text) sendToBrain(text);
    },
    onState: setTalkState,
  });
  els.talkBtn.title = sttInfo.local
    ? 'Push to talk — fully local speech recognition'
    : 'Push to talk — cloud (Whisper API)';
  if (!recorder.supported || !sttInfo.available) {
    els.talkBtn.disabled = true;
    els.talkBtn.style.opacity = '0.5';
    els.talkBtn.title = !recorder.supported
      ? 'Audio recording not available in this build'
      : sttInfo.local
        ? `Local speech model not found at ${sttInfo.modelPath || 'models/vosk'} — see README`
        : 'Set STT_API_KEY in .env to enable push-to-talk';
    return;
  }
  els.talkBtn.addEventListener('click', () => recorder.toggle());
}

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
  initTalk();
  loadWatchlist();
  refreshTrading();
  loadTasks();
  loadAlerts();
  loadGoogleStatus();
  loadBrokerStatus();
  loadAgenda();

  // Chart the first watchlist symbol on load.
  try {
    const symbols = await aria.stocks.watchlist();
    if (symbols && symbols.length) setChart(symbols[0]);
  } catch {}

  // Push notifications when a price alert fires (main -> renderer).
  if (aria.alerts.onTriggered) {
    aria.alerts.onTriggered((a) => {
      const now = a.triggeredPrice != null ? ` (now ${a.triggeredPrice.toFixed(2)})` : '';
      appendMsg('assistant', `🔔 Alert: ${a.symbol} is ${a.direction} ${a.price}${now}.`);
      playAlertSound();
      if (voice && voice.isListening && voice.isListening()) {
        voice.speak(`Alert: ${a.symbol} is ${a.direction} ${a.price}`);
      }
      loadAlerts();
    });
  }

  // Live refresh: trades/P/L fast, watchlist + chart on a slower intraday cadence.
  setInterval(refreshTrading, 15000);
  setInterval(loadWatchlist, 60000);
  setInterval(() => chartState.symbol && loadChart(), 45000);
}

boot();
