'use strict';

// Renderer controller. Talks to the main process only through `aria`, the
// preload bridge. contextBridge exposes it as a NON-CONFIGURABLE global, so we
// reference that global directly — declaring `const aria = window.aria` here is
// a redeclaration SyntaxError that aborts this entire script (dead UI). No Node
// access here.

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
  handsfreeBtn: document.getElementById('handsfree-btn'),
  handsfreeWake: document.getElementById('handsfree-wake'),
  hfStatus: document.getElementById('hf-status'),
  hfState: document.getElementById('hf-state'),
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
  imessageStatus: document.getElementById('imessage-status'),
  telegramStatus: document.getElementById('telegram-status'),
  brokerStatus: document.getElementById('broker-status'),
  brokerForm: document.getElementById('broker-form'),
  brokerMode: document.getElementById('broker-mode'),
  brokerKey: document.getElementById('broker-key'),
  brokerSecret: document.getElementById('broker-secret'),
  brokerNote: document.getElementById('broker-note'),
  brokerDisconnect: document.getElementById('broker-disconnect'),
  acctTabs: document.getElementById('acct-tabs'),
  paneSummary: document.getElementById('pane-summary'),
  paneLedger: document.getElementById('pane-ledger'),
  paneInvoices: document.getElementById('pane-invoices'),
  txnForm: document.getElementById('txn-form'),
  txnType: document.getElementById('txn-type'),
  txnAmount: document.getElementById('txn-amount'),
  txnCat: document.getElementById('txn-cat'),
  txnCats: document.getElementById('txn-cats'),
  txnDesc: document.getElementById('txn-desc'),
  txnList: document.getElementById('txn-list'),
  invForm: document.getElementById('inv-form'),
  invClient: document.getElementById('inv-client'),
  invAmount: document.getElementById('inv-amount'),
  invDue: document.getElementById('inv-due'),
  invList: document.getElementById('inv-list'),
  studyTabs: document.getElementById('study-tabs'),
  paneReview: document.getElementById('pane-review'),
  paneVocab: document.getElementById('pane-vocab'),
  paneCpa: document.getElementById('pane-cpa'),
  studyStats: document.getElementById('study-stats'),
  flashcard: document.getElementById('flashcard'),
  vocabForm: document.getElementById('vocab-form'),
  vocabWord: document.getElementById('vocab-word'),
  vocabTr: document.getElementById('vocab-tr'),
  vocabEx: document.getElementById('vocab-ex'),
  cpaList: document.getElementById('cpa-list'),
  ruStats: document.getElementById('ru-stats'),
  ruContinue: document.getElementById('ru-continue'),
  ruTabs: document.getElementById('ru-tabs'),
  ruPaneLearn: document.getElementById('ru-pane-learn'),
  ruPaneAlpha: document.getElementById('ru-pane-alpha'),
  ruPanePractice: document.getElementById('ru-pane-practice'),
  ruLevel: document.getElementById('ru-level'),
  ruRoman: document.getElementById('ru-roman'),
  ideaForm: document.getElementById('idea-form'),
  ideaSymbol: document.getElementById('idea-symbol'),
  scanIdeas: document.getElementById('scan-ideas'),
  ideas: document.getElementById('ideas'),
  planBtn: document.getElementById('plan-btn'),
  actionplan: document.getElementById('actionplan'),
  fullchartBtn: document.getElementById('fullchart-btn'),
  eventForm: document.getElementById('event-form'),
  eventTitle: document.getElementById('event-title'),
  eventStart: document.getElementById('event-start'),
  eventAllday: document.getElementById('event-allday'),
  eventNote: document.getElementById('event-note'),
  tvOverlay: document.getElementById('tv-overlay'),
  tvModal: document.querySelector('.tv-modal'),
  tvSymbol: document.getElementById('tv-symbol'),
  tvExchange: document.getElementById('tv-exchange'),
  tvClose: document.getElementById('tv-close'),
  tvIframe: document.getElementById('tv-iframe'),
  tvFallback: document.getElementById('tv-fallback'),
  tvRail: document.getElementById('tv-rail'),
};

let chatHistory = [];
let voice = null;
let cfg = { hasBrain: false, wakeWord: 'aria' };
let brainReady = false; // last-known brain state, for the auto-connect poller

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
  row.dataset.symbol = q.symbol;
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

// Streaming state for the in-flight assistant bubble. The brain streams events
// over 'brain:event'; the awaited aria.ask() promise carries history + a final
// fallback. We track the current pending turn here so the single global event
// listener (registered once in boot) can render live deltas into it.
let stream = null; // { bubble, text, gotDelta }

function setTyping(bubble) {
  bubble.classList.add('streaming');
  bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
}

function handleBrainEvent(evt) {
  if (!stream || !evt) return;
  if (evt.type === 'delta') {
    if (!stream.gotDelta) { stream.bubble.classList.remove('streaming'); stream.bubble.textContent = ''; }
    stream.gotDelta = true;
    stream.text += evt.text || '';
    stream.bubble.textContent = stream.text;
    els.transcript.scrollTop = els.transcript.scrollHeight;
  } else if (evt.type === 'tool_result') {
    // Small chip above the in-flight bubble: "↳ used: name".
    const tdiv = document.createElement('div');
    tdiv.className = 'msg tool';
    tdiv.textContent = `↳ used: ${evt.name}${evt.ok === false ? ' (failed)' : ''}`;
    els.transcript.insertBefore(tdiv, stream.bubble);
    els.transcript.scrollTop = els.transcript.scrollHeight;
  } else if (evt.type === 'done') {
    if (evt.text) { stream.text = evt.text; stream.bubble.classList.remove('streaming'); stream.bubble.textContent = evt.text; }
  } else if (evt.type === 'error') {
    stream.bubble.classList.remove('streaming');
    stream.bubble.textContent = `Error: ${evt.error}`;
  }
}

async function sendToBrain(text) {
  appendMsg('user', text);
  const pending = appendMsg('assistant', '…');
  setTyping(pending);
  stream = { bubble: pending, text: '', gotDelta: false };
  try {
    const res = await aria.ask(text, chatHistory);
    chatHistory = res.history || chatHistory;
    // If no live deltas arrived (e.g. engine offline), fall back to the resolved
    // text. If deltas did arrive, prefer the final resolved text for accuracy.
    const finalText = res.text || stream.text || '(no reply)';
    pending.classList.remove('streaming');
    pending.textContent = finalText;
    if (res.ok && finalText && ((voice && voice.isListening && voice.isListening()) || handsfreeOn)) voice.speak(finalText);
    // Refresh panels in case the brain changed the watchlist, staged a trade,
    // or added/completed a task.
    loadWatchlist();
    refreshTrading();
    loadTasks();
    loadAlerts();
    loadAgenda();
    loadAccounting();
    loadStudyStats();
    loadRussian();
  } catch (err) {
    pending.classList.remove('streaming');
    pending.textContent = `Error: ${err.message}`;
  } finally {
    stream = null;
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
      els.watchlist.appendChild(quoteRow(q, { removable: true, onSelect: onWatchlistSelect }))
    );
    subscribeWatchlist(quotes.map((q) => q.symbol).filter(Boolean));
  } catch (err) {
    els.watchlist.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

// Clicking a watchlist ticker charts it in the sidebar (fast/offline default)
// and opens the full TradingView modal (the headline feature).
function onWatchlistSelect(symbol) {
  setChart(symbol);
  openTradingView(symbol);
}

// ---- live ticks ----
// Last seen price per symbol, so a tick can flash green/red vs the prior value.
const lastTick = {};
let realtimeOn = false;
let subscribedKey = '';

async function subscribeWatchlist(symbols) {
  if (!aria.realtime || !symbols.length) return;
  // Avoid tearing down + re-creating the poller on every 60s watchlist refresh:
  // only (re)subscribe when the symbol set actually changes.
  const key = [...symbols].sort().join(',');
  if (key === subscribedKey) return;
  subscribedKey = key;
  try {
    const status = await aria.realtime.subscribe(symbols);
    realtimeOn = !!(status && status.streaming);
    // When no provider key is set, status.streaming is false — we do nothing
    // extra and the existing setInterval polling stays as the fallback.
  } catch { realtimeOn = false; }
}

// Update a single watchlist price cell live, flashing on direction of change.
function applyTick(tick) {
  if (!tick || tick.price == null) return;
  const sym = String(tick.symbol).toUpperCase();
  const row = els.watchlist.querySelector(`.row[data-symbol="${cssEscape(sym)}"]`);
  if (!row) return;
  const cell = row.querySelector('.price');
  if (!cell) return;
  const prev = lastTick[sym];
  lastTick[sym] = tick.price;
  // Preserve currency suffix if the cell already shows one.
  const curMatch = cell.textContent.match(/[A-Z]{3}$/);
  const cur = curMatch ? ' ' + curMatch[0] : '';
  cell.textContent = `${tick.price.toFixed(2)}${cur}`.trim();
  if (prev != null && tick.price !== prev) {
    const dir = tick.price > prev ? 'flash-up' : 'flash-down';
    cell.classList.remove('flash-up', 'flash-down');
    // Force reflow so the animation re-triggers on rapid ticks.
    void cell.offsetWidth;
    cell.classList.add(dir);
  }
}

// Minimal CSS.escape fallback for attribute selectors (tickers are simple, but
// be safe for symbols with dots like BRK.B).
function cssEscape(s) {
  if (window.CSS && CSS.escape) return CSS.escape(s);
  return String(s).replace(/["\\\]]/g, '\\$&');
}

// ---- TradingView full chart modal ----
// 0x1F is TradingView's study separator inside the studies query param.
const TV_STUDY_SEP = '%1F';
const TV_STUDIES = [
  'RSI%40tv-basicstudies',
  'MACD%40tv-basicstudies',
  'MASimple%40tv-basicstudies',
].join(TV_STUDY_SEP);

// Resolve a bare ticker to TradingView's EXCHANGE:SYMBOL form. We read the
// exchange via the symbol search (exchDisp) and map common venues; unknown
// exchanges fall back to the bare symbol (TradingView auto-resolves). Crypto and
// forex stay bare too.
const TV_EXCHANGE_MAP = {
  NASDAQ: 'NASDAQ', NMS: 'NASDAQ', NGM: 'NASDAQ', NCM: 'NASDAQ',
  NYSE: 'NYSE', NYQ: 'NYSE',
  NYSEARCA: 'AMEX', 'NYSE ARCA': 'AMEX', ARCA: 'AMEX', PCX: 'AMEX',
  AMEX: 'AMEX', ASE: 'AMEX', 'NYSE AMERICAN': 'AMEX', BATS: 'AMEX',
};

async function resolveTvSymbol(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  try {
    const matches = await aria.stocks.search(sym);
    const hit = (matches || []).find((m) => String(m.symbol).toUpperCase() === sym) || (matches || [])[0];
    if (hit) {
      const type = String(hit.type || '').toUpperCase();
      // Crypto / forex resolve fine bare; don't prefix an equity exchange.
      if (type === 'CRYPTOCURRENCY' || type === 'CURRENCY') return { tv: sym, exchange: hit.exchange || '' };
      const exch = String(hit.exchange || '').toUpperCase().trim();
      const mapped = TV_EXCHANGE_MAP[exch];
      if (mapped) return { tv: `${mapped}:${sym}`, exchange: hit.exchange };
      return { tv: sym, exchange: hit.exchange || '' };
    }
  } catch { /* fall through to bare symbol */ }
  return { tv: sym, exchange: '' };
}

function tvUrl(tvSymbol) {
  return (
    'https://s.tradingview.com/widgetembed/?symbol=' + encodeURIComponent(tvSymbol) +
    '&interval=D&theme=dark&style=1&hide_side_toolbar=0' +
    '&studies=' + TV_STUDIES +
    '&timezone=Etc%2FUTC'
  );
}

let tvCurrentSymbol = null;

async function openTradingView(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  if (!sym) return;
  tvCurrentSymbol = sym;
  els.tvSymbol.textContent = sym;
  els.tvExchange.textContent = '';
  els.tvFallback.classList.add('hidden');
  els.tvRail.innerHTML = '<p class="muted">Loading plan…</p>';
  els.tvOverlay.classList.remove('hidden');
  els.tvOverlay.setAttribute('aria-hidden', 'false');

  // Resolve exchange + load the iframe.
  const { tv, exchange } = await resolveTvSymbol(sym);
  if (tvCurrentSymbol !== sym) return; // user moved on while resolving
  els.tvExchange.textContent = exchange ? String(exchange) : '';
  loadTvIframe(tv);

  // Build the side rail (tranche plan + insight + catalyst + news) in parallel.
  renderTvRail(sym);
}

function loadTvIframe(tvSymbol) {
  const iframe = els.tvIframe;
  els.tvFallback.classList.add('hidden');
  // Graceful offline message if the iframe can't load (no network).
  let settled = false;
  const fail = () => {
    if (settled) return;
    settled = true;
    els.tvFallback.textContent =
      'Could not load the live TradingView chart (offline?). The lightweight chart in the sidebar still works.';
    els.tvFallback.classList.remove('hidden');
  };
  iframe.onload = () => { settled = true; els.tvFallback.classList.add('hidden'); };
  iframe.onerror = fail;
  // If nothing loads within a few seconds, show the fallback.
  setTimeout(() => { if (!settled) fail(); }, 6000);
  iframe.src = tvUrl(tvSymbol);
}

function closeTradingView() {
  els.tvOverlay.classList.add('hidden');
  els.tvOverlay.setAttribute('aria-hidden', 'true');
  els.tvIframe.src = 'about:blank'; // stop the embed when hidden
  tvCurrentSymbol = null;
}

// Build the modal side rail: analysis insight + the tranche plan + next catalyst
// + a couple of headlines. Reused (the tranche-plan portion) by the ideas panel.
async function renderTvRail(symbol) {
  const sym = String(symbol).trim().toUpperCase();
  els.tvRail.innerHTML = '<p class="muted">Building tranche plan…</p>';
  let plan = null;
  try {
    plan = await aria.strategy.tranche(sym);
  } catch (err) {
    els.tvRail.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    return;
  }
  if (tvCurrentSymbol !== sym) return;

  els.tvRail.innerHTML = '';

  // Analysis insight: a plain-language read derived from the plan.
  const insight = document.createElement('div');
  insight.className = 'tp-section';
  const dirWord = plan.direction === 'long' ? 'long' : 'short';
  insight.innerHTML = `<div class="tp-k">Insight</div>
    <div class="tp-insight">${escapeHtml(plan.symbol)} reads <strong>${escapeHtml(plan.bias)}</strong> — planning the ${escapeHtml(dirWord)} side from ${fmtNum(plan.blendedEntry)} with a ${escapeHtml(plan.stop ? plan.stop.basis : 'ATR')} stop at ${fmtNum(plan.stop && plan.stop.price)}. Targets ladder to ${fmtNum((plan.targets || [])[plan.targets.length - 1] && plan.targets[plan.targets.length - 1].price)}.${plan.biasNote ? ' ' + escapeHtml(plan.biasNote) : ''}</div>`;
  els.tvRail.appendChild(insight);

  const planEl = renderTranchePlan(plan, { propose: true });
  els.tvRail.appendChild(planEl);

  // Next catalyst + headlines, best-effort and independently defensive.
  const extra = document.createElement('div');
  extra.className = 'tp-section';
  extra.innerHTML = `<div class="tp-k">Next catalyst</div><div class="tp-event" data-cal>—</div>
    <div class="tp-k" style="margin-top:10px">Headlines</div><div class="tp-news" data-news><p class="muted">Loading…</p></div>`;
  els.tvRail.appendChild(extra);

  aria.stocks.calendar([sym]).then((rows) => {
    if (tvCurrentSymbol !== sym) return;
    const c = (rows || [])[0];
    const slot = extra.querySelector('[data-cal]');
    if (c && c.earningsDate) slot.textContent = `Earnings ${String(c.earningsDate).slice(0, 10)}`;
    else if (c && c.exDividendDate) slot.textContent = `Ex-dividend ${String(c.exDividendDate).slice(0, 10)}`;
    else slot.textContent = 'None scheduled.';
  }).catch(() => { const s = extra.querySelector('[data-cal]'); if (s) s.textContent = '—'; });

  aria.stocks.news(sym).then((items) => {
    if (tvCurrentSymbol !== sym) return;
    const slot = extra.querySelector('[data-news]');
    slot.innerHTML = '';
    const list = (items || []).slice(0, 3);
    if (!list.length) { slot.innerHTML = '<p class="muted">No recent headlines.</p>'; return; }
    list.forEach((n) => {
      const a = document.createElement('a');
      a.href = n.link; a.target = '_blank'; a.rel = 'noopener';
      a.textContent = n.title;
      slot.appendChild(a);
    });
  }).catch(() => {});
}

// Shared tranche-plan renderer (modal side rail + single-symbol idea cards).
// When opts.propose is true, each entry tranche gets a "Propose" button that
// stages an equity order through the EXISTING approval gate.
function renderTranchePlan(plan, { propose = false } = {}) {
  const el = document.createElement('div');
  el.className = 'tp';
  if (!plan) { el.innerHTML = '<p class="muted">No plan available.</p>'; return el; }
  const side = plan.direction === 'long' ? 'buy' : 'sell';

  const entriesHtml = (plan.entries || []).map((e, i) =>
    `<div class="tp-tranche">
       <div class="tp-left">
         <div class="tp-lbl">${escapeHtml(e.label)} · ${e.weightPct}%</div>
         <div class="tp-sub">@ ${fmtNum(e.price)}${e.fromMarketPct != null ? ` (${e.fromMarketPct >= 0 ? '+' : ''}${fmtNum(e.fromMarketPct)}%)` : ''} · ${e.shares} sh · $${fmtNum(e.notional)}</div>
       </div>
       ${propose ? `<button class="tp-propose" data-i="${i}">Propose</button>` : ''}
     </div>`
  ).join('');

  const targetsHtml = (plan.targets || []).map((t) =>
    `<div class="tp-tline"><span>${escapeHtml(t.label)} <span class="tp-tm">${t.rMultiple}R</span> · ${fmtNum(t.price)} (${t.gainPct >= 0 ? '+' : ''}${fmtNum(t.gainPct)}%)</span><span>scale ${t.scaleOutPct}%</span></div>`
  ).join('');

  const sz = plan.sizing || {};
  el.innerHTML = `
    <div class="tp-head">
      <span class="tp-sym">${escapeHtml(plan.symbol)} · ${fmtNum(plan.price)}</span>
      <span class="tp-bias ${plan.direction}">${escapeHtml(plan.bias)} · ${escapeHtml(plan.direction)}</span>
    </div>
    ${plan.biasNote ? `<div class="tp-note">${escapeHtml(plan.biasNote)}</div>` : ''}
    <div class="tp-section">
      <div class="tp-k">Entry ladder · blended ${fmtNum(plan.blendedEntry)}</div>
      ${entriesHtml}
    </div>
    <div class="tp-section">
      <div class="tp-k">Stop · ${escapeHtml(plan.stop ? plan.stop.basis : '')}</div>
      <div class="tp-stop">${fmtNum(plan.stop && plan.stop.price)} (${plan.stop && plan.stop.distancePct != null ? (plan.stop.distancePct >= 0 ? '+' : '') + fmtNum(plan.stop.distancePct) + '%' : '—'}) · ATR ${fmtNum(plan.atr14)} · risk/sh $${fmtNum(plan.riskPerShare)}</div>
    </div>
    <div class="tp-section tp-targets">
      <div class="tp-k">Targets</div>
      ${targetsHtml}
    </div>
    <div class="tp-section">
      <div class="tp-k">Sizing · ${sz.riskPct != null ? sz.riskPct + '% of equity' : ''}</div>
      <div class="tp-sizing">
        <div class="tp-cell"><span>Total shares</span>${sz.totalShares != null ? sz.totalShares : '—'}</div>
        <div class="tp-cell"><span>Total notional</span>$${fmtNum(sz.totalNotional)}</div>
        <div class="tp-cell"><span>Max $ risk</span>$${fmtNum(sz.maxRiskDollars)}</div>
        <div class="tp-cell"><span>Equity</span>$${fmtNum(sz.equity)}</div>
      </div>
    </div>
    <div class="tp-disc">${escapeHtml(plan.disclaimer || '')}</div>`;

  if (propose) {
    el.querySelectorAll('.tp-propose').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const e = plan.entries[Number(btn.dataset.i)];
        if (!e || !e.shares) { appendMsg('tool', `✗ Tranche has 0 shares — nothing to propose.`); return; }
        btn.disabled = true;
        try {
          await aria.trading.propose({ side, symbol: plan.symbol, qty: e.shares });
          appendMsg('tool', `↳ Staged ${side} ${e.shares} ${plan.symbol} (${e.label}) — approve in Trading.`);
          refreshTrading();
        } catch (err) {
          appendMsg('tool', `✗ ${err.message}`);
          btn.disabled = false;
        }
      });
    });
  }
  return el;
}

// Modal controls: close button, backdrop click, Escape, and the "Full chart ⤢"
// button (opens the modal for whatever the sidebar chart currently shows).
els.tvClose.addEventListener('click', closeTradingView);
els.tvOverlay.addEventListener('click', (e) => { if (e.target === els.tvOverlay) closeTradingView(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !els.tvOverlay.classList.contains('hidden')) closeTradingView();
});
els.fullchartBtn.addEventListener('click', () => {
  const sym = chartState.symbol;
  if (!sym) { appendMsg('tool', 'Click a ticker first to pick a symbol to chart.'); return; }
  openTradingView(sym);
});

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

async function loadImessageStatus() {
  try {
    const s = await aria.imessage.status();
    if (s.enabled && s.reason === 'ready') {
      els.imessageStatus.innerHTML = `<span class="ok">active · ${s.allowCount} handle(s)</span>`;
    } else if (!s.supported) {
      els.imessageStatus.textContent = 'macOS only';
    } else {
      els.imessageStatus.textContent = s.reason;
    }
  } catch {
    els.imessageStatus.textContent = 'unavailable';
  }
}

async function loadTelegramStatus() {
  try {
    const s = await aria.telegram.status();
    els.telegramStatus.innerHTML = s.enabled
      ? `<span class="ok">${escapeHtml(s.bot || 'active')} · ${s.allowCount} allowed</span>`
      : escapeHtml(s.reason || 'not configured');
  } catch {
    els.telegramStatus.textContent = 'unavailable';
  }
}

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

// ---- add-to-calendar (manual UI; the brain can also add via its tool) ----
els.eventForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const gs = await aria.google.status().catch(() => ({ connected: false }));
  if (!gs.connected) {
    els.eventNote.textContent = gs.configured === false
      ? 'Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET, then connect Google.'
      : 'Connect Google (Connections panel) to add events.';
    return;
  }
  const summary = els.eventTitle.value.trim();
  const when = els.eventStart.value; // "YYYY-MM-DDTHH:mm" (local) or "" if empty
  const allDay = els.eventAllday.checked;
  if (!summary) { els.eventNote.textContent = 'Add a title.'; return; }
  if (!when) { els.eventNote.textContent = 'Pick a date/time.'; return; }
  // datetime-local has no timezone; build an ISO start. createEvent slices the
  // date portion for all-day events and uses the host tz otherwise.
  const start = allDay ? when.slice(0, 10) : new Date(when).toISOString();
  els.eventNote.textContent = 'Adding…';
  try {
    const ev = await aria.google.addEvent({ summary, start, allDay });
    els.eventNote.innerHTML = ev.htmlLink
      ? `✓ Added — <a href="${ev.htmlLink}" target="_blank" rel="noopener">open in Google Calendar ↗</a>`
      : '✓ Added.';
    els.eventTitle.value = '';
    els.eventStart.value = '';
    els.eventAllday.checked = false;
    loadAgenda();
  } catch (err) {
    els.eventNote.textContent = `✗ ${err.message}`;
  }
});

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

// ---- hands-free (always-on) listening ----
let handsfreeOn = false;
let handsfreeBusy = false;
const HF_KEY = 'aria.handsfree';

function ariaSpeaking() {
  return !!(window.speechSynthesis && window.speechSynthesis.speaking);
}

function setHandsfreeUi(state) {
  if (!els.handsfreeBtn) return;
  const label = { off: '🎧 Hands-free: off', listening: '🎧 Listening…', thinking: '🎧 Thinking…' };
  els.handsfreeBtn.textContent = label[state] || '🎧 Hands-free';
  els.handsfreeBtn.classList.toggle('live', state === 'listening' || state === 'thinking');
}

function handsfreeText(r) {
  const t = r && (r.text != null ? r.text : (typeof r === 'string' ? r : ''));
  return String(t || '').trim();
}

// Each endpointed utterance: transcribe on-device, optionally gate on the wake
// word, then hand to the brain (sendToBrain speaks the reply in hands-free).
async function onHandsfreeUtterance(payload) {
  if (!handsfreeOn || handsfreeBusy) return;
  handsfreeBusy = true;
  setHandsfreeUi('thinking');
  try {
    let text = handsfreeText(await aria.stt.transcribe(payload));
    if (els.handsfreeWake && els.handsfreeWake.checked) {
      const w = (cfg.wakeWord || 'aria').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(w, 'i');
      if (!re.test(text)) { handsfreeBusy = false; setHandsfreeUi('listening'); return; }
      text = text.replace(re, '').replace(/^[\s,:.!-]+/, '').trim();
    }
    if (text.replace(/[^\p{L}\p{N}]/gu, '').length >= 2) await sendToBrain(text);
  } catch { /* ignore a bad utterance and keep listening */ }
  handsfreeBusy = false;
  setHandsfreeUi(handsfreeOn ? 'listening' : 'off');
}

async function setHandsfree(on) {
  if (!recorder || !recorder.continuousSupported) {
    if (els.handsfreeBtn) {
      els.handsfreeBtn.disabled = true;
      els.handsfreeBtn.title = 'Hands-free needs on-device speech recognition (local Whisper).';
    }
    return;
  }
  if (on) {
    recorder.setContinuousGate(() => handsfreeOn && !handsfreeBusy && !ariaSpeaking());
    const ok = await recorder.startContinuous(onHandsfreeUtterance);
    if (ok === false) {
      handsfreeOn = false; setHandsfreeUi('off');
      els.voiceHint.textContent = 'Microphone blocked — allow mic access for hands-free.';
    } else {
      handsfreeOn = true; setHandsfreeUi('listening');
    }
  } else {
    recorder.stopContinuous();
    handsfreeOn = false; setHandsfreeUi('off');
  }
  try { localStorage.setItem(HF_KEY, handsfreeOn ? '1' : '0'); } catch {}
}

// Wired after initTalk so `recorder` exists. Defaults ON (automatic listening);
// honors a saved preference if the user turned it off.
function initHandsfree() {
  if (!els.handsfreeBtn) return;
  els.handsfreeBtn.addEventListener('click', () => setHandsfree(!handsfreeOn));
  let pref = '1';
  try { const v = localStorage.getItem(HF_KEY); if (v != null) pref = v; } catch {}
  if (pref === '1') setHandsfree(true);
  else setHandsfreeUi('off');
}

// ---- accounting ----
const acctMoney = (n) =>
  n == null ? '—' : (n < 0 ? '-' : '') + '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

els.acctTabs.addEventListener('click', (e) => {
  const btn = e.target.closest('.t-tab');
  if (!btn) return;
  els.acctTabs.querySelectorAll('.t-tab').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  const tab = btn.dataset.tab;
  els.paneSummary.classList.toggle('hidden', tab !== 'summary');
  els.paneLedger.classList.toggle('hidden', tab !== 'ledger');
  els.paneInvoices.classList.toggle('hidden', tab !== 'invoices');
  if (tab === 'ledger') loadTxns();
  if (tab === 'invoices') loadInvoices();
});

async function loadAcctSummary() {
  try {
    const s = await aria.accounting.summary();
    const netCls = s.net >= 0 ? 'pos' : 'neg';
    const catRows = (obj) =>
      Object.entries(obj)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
        .map(([k, v]) => `<div class="crow"><span>${escapeHtml(k)}</span><span>${acctMoney(v)}</span></div>`)
        .join('') || '<div class="crow muted">none</div>';
    els.paneSummary.innerHTML = `
      <div class="sum-grid">
        <div class="sum-card"><div class="k">Income</div><div class="v pos">${acctMoney(s.income)}</div></div>
        <div class="sum-card"><div class="k">Expenses</div><div class="v neg">${acctMoney(s.expense)}</div></div>
        <div class="sum-card"><div class="k">Net</div><div class="v ${netCls}">${acctMoney(s.net)}</div></div>
        <div class="sum-card"><div class="k">Cash position</div><div class="v">${acctMoney(s.cashPosition)}</div></div>
      </div>
      <div class="sum-card" style="margin-bottom:10px">
        <div class="k">Accounts receivable</div>
        <div class="v">${acctMoney(s.accountsReceivable.outstanding)}</div>
        <div class="sum-cats">${s.accountsReceivable.openCount} open${s.accountsReceivable.overdue ? ` · ${acctMoney(s.accountsReceivable.overdue)} overdue` : ''}</div>
      </div>
      <div class="sum-cats"><div class="crow"><strong>Top expenses</strong></div>${catRows(s.byCategory.expense)}</div>`;
  } catch (err) {
    els.paneSummary.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

async function loadTxnCategories() {
  try {
    const c = await aria.accounting.categories();
    const all = [...new Set([...c.income, ...c.expense])];
    els.txnCats.innerHTML = all.map((x) => `<option value="${escapeHtml(x)}">`).join('');
  } catch {}
}

async function loadTxns() {
  try {
    const rows = await aria.accounting.txns({ limit: 30 });
    els.txnList.innerHTML = '';
    if (!rows.length) {
      els.txnList.innerHTML = '<p class="muted">No entries yet.</p>';
      return;
    }
    rows.forEach((t) => {
      const row = document.createElement('div');
      row.className = 'acct-row';
      const sign = t.type === 'income' ? '+' : '-';
      row.innerHTML = `
        <div class="left">
          <div class="a-cat">${escapeHtml(t.category)}${t.description ? ` · <span class="a-meta">${escapeHtml(t.description)}</span>` : ''}</div>
          <div class="a-meta">${t.date} · ${t.account}</div>
        </div>
        <div class="a-amt ${t.type}">${sign}${acctMoney(t.amount).replace('$', '$')}</div>
        <button class="a-del" title="Delete">✕</button>`;
      row.querySelector('.a-del').addEventListener('click', async () => {
        await aria.accounting.deleteTxn(t.id);
        loadTxns();
        loadAcctSummary();
      });
      els.txnList.appendChild(row);
    });
  } catch (err) {
    els.txnList.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.txnForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const amount = Number(els.txnAmount.value);
  if (!amount) return;
  try {
    await aria.accounting.addTxn({
      type: els.txnType.value,
      amount,
      category: els.txnCat.value.trim(),
      description: els.txnDesc.value.trim(),
    });
    els.txnAmount.value = '';
    els.txnCat.value = '';
    els.txnDesc.value = '';
    loadTxns();
    loadAcctSummary();
    loadTxnCategories();
  } catch (err) {
    appendMsg('tool', `✗ ${err.message}`);
  }
});

async function loadInvoices() {
  try {
    const list = await aria.accounting.invoices();
    els.invList.innerHTML = '';
    if (!list.length) {
      els.invList.innerHTML = '<p class="muted">No invoices yet.</p>';
      return;
    }
    const todayStr = new Date().toISOString().slice(0, 10);
    list.forEach((inv) => {
      const row = document.createElement('div');
      row.className = 'acct-row';
      const overdue = inv.status !== 'paid' && inv.due && inv.due < todayStr;
      const statusCls = inv.status === 'paid' ? 'paid' : overdue ? 'overdue' : '';
      const statusTxt = inv.status === 'paid' ? 'paid' : overdue ? 'overdue' : inv.status;
      row.innerHTML = `
        <div class="left">
          <div class="a-cat">${escapeHtml(inv.client)} <span class="a-meta">${inv.number}</span></div>
          <div class="a-meta">${acctMoney(inv.amount)}${inv.due ? ` · due ${inv.due}` : ''}</div>
        </div>
        <span class="inv-status ${statusCls}">${statusTxt}</span>
        ${inv.status !== 'paid' ? '<button class="inv-pay">Paid</button>' : ''}
        <button class="a-del" title="Delete">✕</button>`;
      const payBtn = row.querySelector('.inv-pay');
      if (payBtn) payBtn.addEventListener('click', async () => {
        await aria.accounting.markPaid(inv.id);
        loadInvoices();
        loadAcctSummary();
      });
      row.querySelector('.a-del').addEventListener('click', async () => {
        await aria.accounting.deleteInvoice(inv.id);
        loadInvoices();
        loadAcctSummary();
      });
      els.invList.appendChild(row);
    });
  } catch (err) {
    els.invList.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.invForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const client = els.invClient.value.trim();
  const amount = Number(els.invAmount.value);
  if (!client || !amount) return;
  try {
    await aria.accounting.addInvoice({ client, amount, due: els.invDue.value.trim() });
    els.invClient.value = '';
    els.invAmount.value = '';
    els.invDue.value = '';
    loadInvoices();
    loadAcctSummary();
  } catch (err) {
    appendMsg('tool', `✗ ${err.message}`);
  }
});

function loadAccounting() {
  loadAcctSummary();
  loadTxnCategories();
}

// ---- trade ideas ----
function fmtNum(n) {
  return n == null ? '—' : Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function renderIdea(idea) {
  const el = document.createElement('div');
  if (idea.recommendation === 'stand aside') {
    el.className = 'idea aside';
    el.innerHTML = `
      <div class="i-head"><span class="i-sym">${idea.symbol} · ${fmtNum(idea.price)}</span>
        <span class="i-bias neutral">stand aside</span></div>
      <div class="i-line">${escapeHtml(idea.note || '')}</div>
      <div class="i-reasons">${(idea.rationale || []).map(escapeHtml).join(' · ')}</div>
      <div class="i-disc">${escapeHtml(idea.disclaimer)}</div>`;
    return el;
  }
  const dir = idea.recommendation; // bullish | bearish
  el.className = 'idea ' + dir;
  const o = idea.option;
  const sp = idea.spread;
  const plan = idea.underlyingPlan || {};
  let contractHtml = '';
  if (o) {
    contractHtml += `<div class="i-contract">${o.type.toUpperCase()} ${idea.symbol} ${fmtNum(o.strike)} exp ${o.expiry} (${o.dte}d)
      · ~$${fmtNum(o.premium)} · BE ${fmtNum(o.breakeven)} (${o.moveToBreakevenPct >= 0 ? '+' : ''}${fmtNum(o.moveToBreakevenPct)}%)
      · max loss $${fmtNum(o.maxLossPerContract)}${o.iv != null ? ` · IV ${fmtNum(o.iv)}%` : ''}</div>`;
  } else if (idea.optionError) {
    contractHtml += `<div class="i-reasons">${escapeHtml(idea.optionError)}</div>`;
  }
  if (sp) {
    contractHtml += `<div class="i-contract">${sp.type.toUpperCase()} ${fmtNum(sp.longStrike)}/${fmtNum(sp.shortStrike)}
      · debit $${fmtNum(sp.netDebit)} · max profit $${fmtNum(sp.maxProfit)} · max loss $${fmtNum(sp.maxLoss)} · R:R ${fmtNum(sp.riskReward)}</div>`;
  }
  if (idea.futures) {
    contractHtml += `<div class="i-contract">FUTURES ${idea.futures.direction.toUpperCase()} ${idea.futures.contract} (micro ${idea.futures.microContract}) — ${escapeHtml(idea.futures.underlying)}</div>`;
  }
  el.innerHTML = `
    <div class="i-head"><span class="i-sym">${idea.symbol} · ${fmtNum(idea.price)}</span>
      <span class="i-bias ${dir}">${dir} · ${idea.setupScore}</span></div>
    <div class="i-score"><span style="width:${idea.setupScore}%"></span></div>
    <div class="i-line"><span class="i-label">UNDERLYING</span> entry ${fmtNum(plan.entry)} · stop ${fmtNum(plan.stop)} · target ${fmtNum(plan.target)}</div>
    ${contractHtml}
    <div class="i-reasons">${(idea.rationale || []).map(escapeHtml).join(' · ')}</div>
    <div class="i-disc">${escapeHtml(idea.disclaimer)}</div>`;
  // The tranche ladder + sizing + Propose buttons (reuses the side-rail renderer).
  if (idea.tranchePlan) {
    const tp = document.createElement('div');
    tp.style.marginTop = '8px';
    tp.appendChild(renderTranchePlan(idea.tranchePlan, { propose: true }));
    el.appendChild(tp);
  }
  return el;
}

async function getIdea(symbol) {
  els.ideas.innerHTML = '<p class="muted">Analyzing…</p>';
  try {
    const idea = await aria.strategy.idea(symbol);
    els.ideas.innerHTML = '';
    els.ideas.appendChild(renderIdea(idea));
  } catch (err) {
    els.ideas.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.ideaForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const s = els.ideaSymbol.value.trim();
  if (!s) return;
  getIdea(s);
});

els.scanIdeas.addEventListener('click', async () => {
  els.ideas.innerHTML = '<p class="muted">Scanning watchlist…</p>';
  try {
    const res = await aria.strategy.scan();
    els.ideas.innerHTML = '';
    if (!res.ideas.length) {
      els.ideas.innerHTML = '<p class="muted">No clean setups on the watchlist right now.</p>';
    } else {
      res.ideas.forEach((i) => {
        const row = document.createElement('div');
        row.className = 'idea-rank';
        row.innerHTML = `<span class="r-sym">${i.symbol} · ${i.bias}</span>
          <span class="r-meta">score ${i.setupScore} · ${escapeHtml((i.top || [])[0] || '')}</span>`;
        row.addEventListener('click', () => { els.ideaSymbol.value = i.symbol; getIdea(i.symbol); });
        els.ideas.appendChild(row);
      });
    }
    const note = document.createElement('p');
    note.className = 'i-disc';
    note.textContent = res.note;
    els.ideas.appendChild(note);
  } catch (err) {
    els.ideas.innerHTML = `<p class="err">${err.message}</p>`;
  }
});

// ---- action plan / briefing (synthesize news + events into a plan) ----
function actionChipClass(action) {
  return String(action || '').replace(/\s+/g, '-').toLowerCase(); // "stand aside" -> "stand-aside"
}

function renderActionPlan(plan) {
  els.actionplan.innerHTML = '';
  els.actionplan.classList.remove('hidden');

  const head = document.createElement('div');
  head.className = 'ap-head';
  head.innerHTML = `<h3>Plan of action</h3><button class="ap-close" title="Hide">✕</button>`;
  head.querySelector('.ap-close').addEventListener('click', () => els.actionplan.classList.add('hidden'));
  els.actionplan.appendChild(head);

  if (plan.marketContext) {
    const ctx = document.createElement('div');
    ctx.className = 'ap-context';
    ctx.textContent = plan.marketContext;
    els.actionplan.appendChild(ctx);
  }

  if ((plan.topActions || []).length) {
    const top = document.createElement('div');
    top.className = 'ap-top';
    plan.topActions.forEach((t) => {
      const line = document.createElement('div');
      line.className = 'ap-line';
      line.textContent = t;
      top.appendChild(line);
    });
    els.actionplan.appendChild(top);
  }

  const items = document.createElement('div');
  items.className = 'ap-items';
  (plan.items || []).forEach((it) => {
    const row = document.createElement('div');
    row.className = 'ap-item';
    if (it.error) {
      row.innerHTML = `<div class="ap-r1"><span class="ap-sym">${escapeHtml(it.symbol)}</span>
        <span class="ap-chip stand-aside">error</span></div>
        <div class="ap-meta">${escapeHtml(it.error)}</div>`;
      items.appendChild(row);
      return;
    }
    const kl = it.keyLevels || {};
    const levels = `entries ${(kl.entries || []).map(fmtNum).join(' / ') || '—'} · stop ${fmtNum(kl.stop)} · targets ${(kl.targets || []).map(fmtNum).join(' / ') || '—'}`;
    const sizing = it.sizing ? ` · ~${it.sizing.totalShares} sh (max risk $${fmtNum(it.sizing.maxRiskDollars)})` : '';
    const ev = it.nextEvent ? `<div class="ap-meta">next: ${escapeHtml(it.nextEvent.type)} ${String(it.nextEvent.date).slice(0, 10)}</div>` : '';
    const head1 = (it.catalysts || [])[0];
    row.innerHTML = `
      <div class="ap-r1">
        <span class="ap-sym">${escapeHtml(it.symbol)} · ${fmtNum(it.price)} <span class="muted">(${escapeHtml(it.bias)} · ${it.setupScore})</span></span>
        <span class="ap-chip ${actionChipClass(it.action)}">${escapeHtml(it.action)}</span>
      </div>
      <div class="ap-meta">${escapeHtml(levels)}${escapeHtml(sizing)}</div>
      ${ev}
      ${head1 ? `<div class="ap-head-line">📰 ${escapeHtml(head1)}</div>` : ''}`;
    // Clicking the symbol opens its full TradingView view.
    row.querySelector('.ap-sym').style.cursor = 'pointer';
    row.querySelector('.ap-sym').addEventListener('click', () => openTradingView(it.symbol));
    items.appendChild(row);
  });
  els.actionplan.appendChild(items);

  if (plan.disclaimer) {
    const disc = document.createElement('div');
    disc.className = 'ap-disc';
    disc.textContent = plan.disclaimer;
    els.actionplan.appendChild(disc);
  }
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

els.planBtn.addEventListener('click', async () => {
  els.actionplan.classList.remove('hidden');
  els.actionplan.innerHTML = '<p class="muted">Synthesizing news + events into a plan…</p>';
  try {
    const plan = await aria.strategy.actionPlan();
    renderActionPlan(plan);
  } catch (err) {
    els.actionplan.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
});

// ---- study ----
let dueQueue = [];

els.studyTabs.addEventListener('click', (e) => {
  const btn = e.target.closest('.t-tab');
  if (!btn) return;
  els.studyTabs.querySelectorAll('.t-tab').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  const tab = btn.dataset.tab;
  els.paneReview.classList.toggle('hidden', tab !== 'review');
  els.paneVocab.classList.toggle('hidden', tab !== 'vocab');
  els.paneCpa.classList.toggle('hidden', tab !== 'cpa');
  if (tab === 'review') loadReview();
  if (tab === 'cpa') loadCpa();
});

async function loadStudyStats() {
  try {
    const s = await aria.study.stats();
    els.studyStats.textContent =
      `${s.cards.due} card(s) due · ${s.cards.total} total · ${s.streakDays}-day streak`;
  } catch {}
}

function renderCard() {
  if (!dueQueue.length) {
    els.flashcard.innerHTML = '<p class="muted" style="text-align:center;margin:auto">No cards due. 🎉 Add vocab or ask the assistant to teach you something.</p>';
    return;
  }
  const c = dueQueue[0];
  els.flashcard.innerHTML = `
    <div class="fc-sub">${escapeHtml(c.subject)}</div>
    <div class="fc-front">${escapeHtml(c.front)}</div>
    <div class="fc-actions"><button class="fc-reveal">Show answer</button></div>`;
  els.flashcard.querySelector('.fc-reveal').addEventListener('click', () => revealCard(c));
}

function revealCard(c) {
  els.flashcard.innerHTML = `
    <div class="fc-sub">${escapeHtml(c.subject)}</div>
    <div class="fc-front">${escapeHtml(c.front)}</div>
    <div class="fc-back">${escapeHtml(c.back)}</div>
    <div class="fc-actions">
      <button class="fc-grade again" data-g="1">Again</button>
      <button class="fc-grade" data-g="3">Hard</button>
      <button class="fc-grade good" data-g="4">Good</button>
      <button class="fc-grade easy" data-g="5">Easy</button>
    </div>`;
  els.flashcard.querySelectorAll('.fc-grade').forEach((b) =>
    b.addEventListener('click', async () => {
      try { await aria.study.review(c.id, Number(b.dataset.g)); } catch {}
      dueQueue.shift();
      renderCard();
      loadStudyStats();
    })
  );
}

async function loadReview() {
  try {
    dueQueue = await aria.study.due({ limit: 50 });
    renderCard();
  } catch (err) {
    els.flashcard.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

els.vocabForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const word = els.vocabWord.value.trim();
  const translation = els.vocabTr.value.trim();
  if (!word || !translation) return;
  try {
    await aria.study.addVocab({ word, translation, example: els.vocabEx.value.trim() });
    els.vocabWord.value = '';
    els.vocabTr.value = '';
    els.vocabEx.value = '';
    loadStudyStats();
    appendMsg('tool', `✓ Added Russian card: ${word}`);
  } catch (err) {
    appendMsg('tool', `✗ ${err.message}`);
  }
});

async function loadCpa() {
  try {
    const s = await aria.study.cpa();
    els.cpaList.innerHTML = '';
    s.sections.forEach((sec) => {
      const row = document.createElement('div');
      row.className = 'cpa-row';
      row.innerHTML = `
        <span class="cpa-sec">${sec.section}</span>
        <div class="cpa-bar"><span style="width:${sec.progress}%"></span></div>
        <input class="cpa-input" type="text" inputmode="numeric" value="${sec.progress}" title="progress %" />
        <span class="cpa-pct">%</span>`;
      const input = row.querySelector('.cpa-input');
      input.addEventListener('change', async () => {
        const v = Number(input.value);
        if (Number.isFinite(v)) {
          await aria.study.setCpa({ section: sec.section, progress: v });
          loadCpa();
        }
      });
      els.cpaList.appendChild(row);
    });
    const overall = document.createElement('div');
    overall.className = 'study-stats muted';
    overall.textContent = `Overall ${s.overallProgress}% · Becker (progress tracked here; study in Becker)`;
    els.cpaList.appendChild(overall);
  } catch (err) {
    els.cpaList.innerHTML = `<p class="err">${err.message}</p>`;
  }
}

function loadStudy() {
  loadStudyStats();
  loadReview();
}

// ---- Russian language program (A1→C2) ----
// State for the Learn pane: the curriculum tree, the romanization toggle, and
// the lesson currently open in the detail area. Kept local to this section.
let ruCurriculum = [];
let ruShowRoman = true;
let ruOpenLessonId = null;

// Speak an arbitrary Russian string. Prefers the standalone window helper that
// voice.js exposes (picks a ru-RU voice); falls back to the shared voice object.
function ruSpeak(text) {
  if (!text) return;
  if (typeof window.ariaSpeak === 'function') { window.ariaSpeak(text); return; }
  if (voice && voice.speak) voice.speak(text);
}

// Header stats: level badge, streak, words learned, daily-goal progress.
function renderRuStats(p) {
  const goal = p.dailyGoalMins || 15;
  const done = p.minutesToday || 0;
  const pct = goal ? Math.min(100, Math.round((done / goal) * 100)) : 0;
  els.ruStats.innerHTML = `
    <span class="ru-badge">${escapeHtml(p.level || 'A1')}</span>
    <span class="ru-stat" title="Day streak">🔥 ${p.streak || 0}</span>
    <span class="ru-stat" title="Words learned">${p.wordsLearned || 0} words</span>
    <span class="ru-stat" title="Lessons done">${p.completedCount || 0}/${p.totalLessons || 0} lessons</span>
    <span class="ru-goal" title="Daily goal">
      <span class="ru-goal-bar"><span style="width:${pct}%"></span></span>
      <span class="ru-goal-txt">${done}/${goal} min</span>
    </span>`;
}

// Continue card: the lesson to resume (current, else next) + a launch button.
function renderRuContinue(p) {
  const lesson = p.currentLesson || p.nextLesson || null;
  if (!lesson) {
    els.ruContinue.innerHTML = '<p class="muted">All lessons complete — practice or set a higher level. 🎉</p>';
    return;
  }
  els.ruContinue.innerHTML = `
    <div class="ru-cont-info">
      <div class="ru-cont-k">${p.currentLesson ? 'Continue' : 'Start'}</div>
      <div class="ru-cont-title">${escapeHtml(lesson.title)}</div>
      <div class="ru-cont-meta">${escapeHtml(lesson.unitTitle || '')}${lesson.level ? ' · ' + escapeHtml(lesson.level) : ''}</div>
    </div>
    <button class="ru-cont-go">Learn with ARIA ▶</button>`;
  els.ruContinue.querySelector('.ru-cont-go').addEventListener('click', () =>
    ruStartLesson(lesson.id, lesson.title)
  );
}

// Fetch progress and render the header + continue card + level/roman controls.
async function loadRussian() {
  try {
    const p = await aria.russian.progress();
    ruShowRoman = !(p.settings && p.settings.showRomanization === false);
    if (els.ruLevel && p.level) els.ruLevel.value = p.level;
    if (els.ruRoman) els.ruRoman.checked = ruShowRoman;
    renderRuStats(p);
    renderRuContinue(p);
    // Refresh whichever pane is active so done-flags etc. stay in sync.
    const active = els.ruTabs.querySelector('.t-tab.active');
    const tab = active ? active.dataset.tab : 'learn';
    if (tab === 'learn') loadRuCurriculum();
    else if (tab === 'alpha') renderAlphabet();
    else if (tab === 'practice') renderRuPractice();
  } catch (err) {
    if (els.ruStats) els.ruStats.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
}

// Tab bar: Learn | Alphabet | Practice.
els.ruTabs.addEventListener('click', (e) => {
  const btn = e.target.closest('.t-tab');
  if (!btn) return;
  els.ruTabs.querySelectorAll('.t-tab').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  const tab = btn.dataset.tab;
  els.ruPaneLearn.classList.toggle('hidden', tab !== 'learn');
  els.ruPaneAlpha.classList.toggle('hidden', tab !== 'alpha');
  els.ruPanePractice.classList.toggle('hidden', tab !== 'practice');
  if (tab === 'learn') loadRuCurriculum();
  if (tab === 'alpha') renderAlphabet();
  if (tab === 'practice') renderRuPractice();
});

// Learn pane: levels → units → lessons, with a ✓ on done lessons. Clicking a
// lesson opens its full content in the detail area below the list.
async function loadRuCurriculum() {
  els.ruPaneLearn.innerHTML = '<p class="muted">Loading curriculum…</p>';
  try {
    ruCurriculum = await aria.russian.curriculum();
    renderRuCurriculum();
  } catch (err) {
    els.ruPaneLearn.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
}

function renderRuCurriculum() {
  els.ruPaneLearn.innerHTML = '';
  const tree = document.createElement('div');
  tree.className = 'ru-tree';
  (ruCurriculum || []).forEach((lvl) => {
    const total = (lvl.units || []).reduce((n, u) => n + (u.lessons || []).length, 0);
    const done = (lvl.units || []).reduce((n, u) => n + (u.lessons || []).filter((l) => l.done).length, 0);
    const levelEl = document.createElement('details');
    levelEl.className = 'ru-level-group';
    // Open the level that still has unfinished lessons (first incomplete).
    if (done < total && !tree.querySelector('details[open]')) levelEl.open = true;
    const sum = document.createElement('summary');
    sum.className = 'ru-level-sum';
    sum.innerHTML = `<span class="ru-level-name">${escapeHtml(lvl.level)}</span>
      <span class="ru-level-prog">${done}/${total}</span>`;
    levelEl.appendChild(sum);

    if (lvl.summary) {
      const s = document.createElement('div');
      s.className = 'ru-level-blurb muted';
      s.textContent = lvl.summary;
      levelEl.appendChild(s);
    }

    (lvl.units || []).forEach((unit) => {
      const ue = document.createElement('div');
      ue.className = 'ru-unit';
      ue.innerHTML = `<div class="ru-unit-head">${escapeHtml(unit.title)}</div>
        ${unit.goal ? `<div class="ru-unit-goal muted">${escapeHtml(unit.goal)}</div>` : ''}`;
      (unit.lessons || []).forEach((l) => {
        const row = document.createElement('button');
        row.className = 'ru-lesson' + (l.done ? ' done' : '') + (l.id === ruOpenLessonId ? ' active' : '');
        row.type = 'button';
        row.innerHTML = `<span class="ru-check">${l.done ? '✓' : ''}</span>
          <span class="ru-lesson-title">${escapeHtml(l.title)}</span>
          <span class="ru-lesson-cefr">${escapeHtml(l.cefr || '')}</span>`;
        row.addEventListener('click', () => openRuLesson(l.id));
        ue.appendChild(row);
      });
      levelEl.appendChild(ue);
    });
    tree.appendChild(levelEl);
  });
  els.ruPaneLearn.appendChild(tree);

  const detail = document.createElement('div');
  detail.className = 'ru-detail';
  detail.id = 'ru-detail';
  if (!ruOpenLessonId) detail.innerHTML = '<p class="muted">Pick a lesson to see its content.</p>';
  els.ruPaneLearn.appendChild(detail);

  // Re-open whatever lesson was showing (after a refresh).
  if (ruOpenLessonId) openRuLesson(ruOpenLessonId);
}

// Load a full lesson into the detail area. Every field is rendered defensively
// — outline lessons (B1+) may omit explanation/vocab/examples/dialogue.
async function openRuLesson(id) {
  ruOpenLessonId = id;
  // Highlight the active row without re-fetching the whole tree.
  els.ruPaneLearn.querySelectorAll('.ru-lesson').forEach((b) => b.classList.remove('active'));
  const detail = document.getElementById('ru-detail');
  if (!detail) return;
  detail.innerHTML = '<p class="muted">Loading lesson…</p>';
  let l;
  try {
    l = await aria.russian.lesson(id);
  } catch (err) {
    detail.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    return;
  }
  if (ruOpenLessonId !== id) return; // user moved on

  const parts = [];
  parts.push(`<div class="ru-d-head">
    <div class="ru-d-title">${escapeHtml(l.title || '')}</div>
    <div class="ru-d-meta">${escapeHtml(l.unitTitle || '')}${l.level ? ' · ' + escapeHtml(l.level) : ''}${l.cefr ? ' · ' + escapeHtml(l.cefr) : ''}</div>
  </div>`);

  if (l.grammarFocus) parts.push(`<div class="ru-d-block"><div class="ru-d-k">Grammar focus</div><div>${escapeHtml(l.grammarFocus)}</div></div>`);

  if (Array.isArray(l.canDo) && l.canDo.length) {
    parts.push(`<div class="ru-d-block"><div class="ru-d-k">Can-do</div><ul class="ru-d-cando">${
      l.canDo.map((c) => `<li>${escapeHtml(c)}</li>`).join('')
    }</ul></div>`);
  }

  if (l.explanation) parts.push(`<div class="ru-d-block"><div class="ru-d-k">Explanation</div><p class="ru-d-expl">${escapeHtml(l.explanation)}</p></div>`);

  if (Array.isArray(l.vocab) && l.vocab.length) {
    const rows = l.vocab.map((v) => `<tr>
        <td class="ru-cyr">${escapeHtml(v.ru || '')}</td>
        ${ruShowRoman ? `<td class="ru-translit">${escapeHtml(v.translit || '')}</td>` : ''}
        <td>${escapeHtml(v.en || '')}</td>
      </tr>${v.ex ? `<tr class="ru-ex-row"><td colspan="${ruShowRoman ? 3 : 2}" class="ru-ex">${escapeHtml(v.ex)}</td></tr>` : ''}`).join('');
    parts.push(`<div class="ru-d-block"><div class="ru-d-k">Vocabulary</div>
      <table class="ru-vocab"><tbody>${rows}</tbody></table></div>`);
  }

  if (Array.isArray(l.examples) && l.examples.length) {
    const rows = l.examples.map((ex) => `<div class="ru-ex-line">
        <span class="ru-cyr">${escapeHtml(ex.ru || '')}</span>
        ${ruShowRoman && ex.translit ? `<span class="ru-translit"> · ${escapeHtml(ex.translit)}</span>` : ''}
        <span class="muted"> — ${escapeHtml(ex.en || '')}</span>
      </div>`).join('');
    parts.push(`<div class="ru-d-block"><div class="ru-d-k">Examples</div>${rows}</div>`);
  }

  if (Array.isArray(l.dialogue) && l.dialogue.length) {
    const rows = l.dialogue.map((d) => `<div class="ru-dlg-line">
        <span class="ru-cyr">${escapeHtml(d.ru || '')}</span>
        <span class="muted"> — ${escapeHtml(d.en || '')}</span>
      </div>`).join('');
    parts.push(`<div class="ru-d-block"><div class="ru-d-k">Dialogue</div>${rows}</div>`);
  } else if (typeof l.dialogue === 'string' && l.dialogue.trim()) {
    parts.push(`<div class="ru-d-block"><div class="ru-d-k">Dialogue</div><p class="ru-cyr">${escapeHtml(l.dialogue)}</p></div>`);
  }

  if (l.notes) parts.push(`<div class="ru-d-block"><div class="ru-d-k">Notes</div><p class="muted">${escapeHtml(l.notes)}</p></div>`);

  parts.push(`<div class="ru-d-acts">
    <button class="ru-start">Start with ARIA</button>
    <button class="ru-complete ghost">Mark complete</button>
  </div>`);

  detail.innerHTML = parts.join('');
  // Highlight the matching row in the tree (matched by title text).
  els.ruPaneLearn.querySelectorAll('.ru-lesson').forEach((b) => {
    const t = b.querySelector('.ru-lesson-title');
    if (t && t.textContent === (l.title || '')) b.classList.add('active');
  });
  detail.querySelector('.ru-start').addEventListener('click', () => ruStartLesson(l.id, l.title));
  detail.querySelector('.ru-complete').addEventListener('click', () => ruCompleteLesson(l.id));
}

// Start a lesson: mark it current in the program, then hand the brain a precise
// tutor prompt so ARIA teaches it step by step.
async function ruStartLesson(id, title) {
  try { await aria.russian.start(id); } catch {}
  sendToBrain(`Let's do my Russian lesson: "${title}" (id ${id}). Teach it to me step by step in tutor mode — explain, give examples, then quiz me.`);
}

async function ruCompleteLesson(id) {
  try {
    await aria.russian.complete({ id });
    appendMsg('tool', '✓ Marked Russian lesson complete.');
  } catch (err) {
    appendMsg('tool', `✗ ${err.message}`);
  }
  loadRussian();
}

// Alphabet pane: the full Cyrillic grid. Clicking a letter speaks its example
// Russian word (or the letter name) using the Russian voice.
async function renderAlphabet() {
  els.ruPaneAlpha.innerHTML = '<p class="muted">Loading alphabet…</p>';
  let letters;
  try {
    letters = await aria.russian.alphabet();
  } catch (err) {
    els.ruPaneAlpha.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    return;
  }
  els.ruPaneAlpha.innerHTML = '';
  const hint = document.createElement('p');
  hint.className = 'muted ru-alpha-hint';
  hint.textContent = 'Tap a letter to hear it spoken in Russian.';
  els.ruPaneAlpha.appendChild(hint);

  const grid = document.createElement('div');
  grid.className = 'ru-alpha-grid';
  (letters || []).forEach((a) => {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.className = 'ru-alpha-cell';
    const ex = a.example || {};
    cell.innerHTML = `
      <span class="ru-alpha-char">${escapeHtml(a.char || '')}</span>
      <span class="ru-alpha-translit">${escapeHtml(a.translit || '')}</span>
      <span class="ru-alpha-sound">${escapeHtml(a.sound || '')}</span>
      ${ex.ru ? `<span class="ru-alpha-ex"><span class="ru-cyr">${escapeHtml(ex.ru)}</span> — ${escapeHtml(ex.en || '')}</span>` : ''}`;
    cell.addEventListener('click', () => ruSpeak(ex.ru || a.char || a.name || ''));
    grid.appendChild(cell);
  });
  els.ruPaneAlpha.appendChild(grid);
}

// Practice pane: tutor-driving buttons + SRS seeding. Each logs a practice
// session so the streak / daily-goal progress reflects real activity.
function renderRuPractice() {
  els.ruPanePractice.innerHTML = `
    <p class="muted">Drills that hand ARIA a focused prompt — answer back in chat or by voice.</p>
    <div class="ru-prac-grid">
      <button class="ru-prac" data-act="conversation">💬 Conversation (Russian)</button>
      <button class="ru-prac" data-act="review">📖 Review vocabulary</button>
      <button class="ru-prac" data-act="grammar">✍️ Grammar drill</button>
      <button class="ru-prac" data-act="reading">📚 Reading</button>
      <button class="ru-prac ru-prac-seed" data-act="seed">➕ Add starter vocabulary</button>
    </div>`;
  els.ruPanePractice.querySelectorAll('.ru-prac').forEach((btn) =>
    btn.addEventListener('click', () => ruPractice(btn.dataset.act))
  );
}

async function ruPractice(act) {
  if (act === 'seed') {
    try {
      const res = await aria.russian.seedVocab();
      appendMsg('tool', `✓ Added ${res && res.added != null ? res.added : ''} starter word(s) to your review queue.`);
    } catch (err) {
      appendMsg('tool', `✗ ${err.message}`);
    }
    loadRussian();
    loadStudyStats();
    return;
  }
  const prompts = {
    conversation: { kind: 'conversation', text: "Let's have a short conversation in Russian at my level. Start, correct my mistakes, keep it simple." },
    review: { kind: 'review', text: 'Quiz me on my due Russian flashcards now, one at a time.' },
    grammar: { kind: 'grammar', text: 'Give me a short Russian grammar drill on my current topic, then check my answers.' },
    reading: { kind: 'reading', text: 'Give me a short Russian reading passage at my level with a glossary, then ask me about it.' },
  };
  const p = prompts[act];
  if (!p) return;
  // Log a few minutes so the daily goal/streak move; best-effort.
  try { aria.russian.logPractice({ minutes: 5, kind: p.kind }); } catch {}
  // Conversation practice is most natural with voice on, if available.
  if (act === 'conversation' && voice && voice.isListening && !voice.isListening()) {
    try { voice.start(); } catch {}
  }
  sendToBrain(p.text);
}

// Level select → set the program level. Romanization checkbox → persist the
// setting. Both reload progress + the active pane.
els.ruLevel.addEventListener('change', async () => {
  try { await aria.russian.setLevel(els.ruLevel.value); } catch (err) { appendMsg('tool', `✗ ${err.message}`); }
  loadRussian();
});

els.ruRoman.addEventListener('change', async () => {
  try { await aria.russian.settings({ showRomanization: els.ruRoman.checked }); } catch (err) { appendMsg('tool', `✗ ${err.message}`); }
  loadRussian();
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
// Reflect brain connection state in the header. The poller calls this so ARIA
// links up on her own the moment Ollama is running — no app restart.
function applyBrainStatus(b, announce = false) {
  const wasReady = brainReady;
  brainReady = !!(b && b.ready);
  els.brainDot.classList.toggle('on', brainReady);
  els.brainDot.classList.toggle('off', !brainReady);
  els.brainLabel.textContent = brainReady
    ? `brain online · ${b.local ? 'local' : 'claude'} · ${b.model}`
    : `brain offline · ${b && b.local === false ? 'add API key' : 'start Ollama'}`;
  if (announce && brainReady && !wasReady) {
    appendMsg('assistant', `Brain connected — ${b.model} is live. Ready when you are, Vinny.`);
    if (handsfreeOn && voice && voice.speak) voice.speak('Brain connected. Ready when you are.');
  }
}

async function pollBrainStatus() {
  try {
    const c = await aria.config();
    if (c && c.brain) applyBrainStatus(c.brain, true);
  } catch { /* keep last-known state */ }
}

async function boot() {
  try {
    cfg = await aria.config();
  } catch {}
  const b = cfg.brain || { engine: '?', model: cfg.model, ready: cfg.hasBrain };
  applyBrainStatus(b);
  if (!b.ready) {
    appendMsg(
      'assistant',
      `Hi Vinny — I'm ARIA. The brain is offline: ${b.reason || 'not configured'} ` +
        'Start Ollama (or add a key) and I\'ll connect automatically — no restart. ' +
        'The data panels all still work meanwhile.'
    );
  }
  // Streaming brain events (delta / tool_result / done / error) — register ONCE.
  if (aria.onBrainEvent) aria.onBrainEvent(handleBrainEvent);
  // Live price ticks — register ONCE; subscription happens after watchlist load.
  if (aria.realtime && aria.realtime.onTick) aria.realtime.onTick(applyTick);

  initVoice();
  initTalk().then(initHandsfree);
  loadWatchlist();
  refreshTrading();
  loadTasks();
  loadAlerts();
  loadGoogleStatus();
  loadImessageStatus();
  loadTelegramStatus();
  loadBrokerStatus();
  loadAgenda();
  loadAccounting();
  loadStudy();
  loadRussian();

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

  // Always-live brain: re-check the connection so ARIA links up on her own the
  // moment Ollama starts (and reflects a dropped connection).
  setInterval(pollBrainStatus, 4000);

  // Live refresh: trades/P/L fast, watchlist + chart on a slower intraday cadence.
  setInterval(refreshTrading, 15000);
  setInterval(loadWatchlist, 60000);
  setInterval(() => chartState.symbol && loadChart(), 45000);
}

boot();
