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
    // Refresh watchlist in case the brain modified it.
    loadWatchlist();
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
}

boot();
