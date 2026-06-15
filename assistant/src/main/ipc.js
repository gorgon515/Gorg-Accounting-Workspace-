'use strict';

// Wires renderer <-> main IPC. Two kinds of channels:
//   1. Direct stock data (UI panels) — work with no API key.
//   2. The AI brain (chat / voice) — needs ANTHROPIC_API_KEY.
const { ipcMain } = require('electron');
const config = require('./config');
const brain = require('./brain');
const skills = require('./services/skills');
const broker = require('./services/broker');
const stt = require('./services/stt');
const imessage = require('./services/imessage');
const telegram = require('./services/telegram');
const realtime = require('./services/realtime');
const store = require('./store');

function register() {
  const stocks = skills.getSkill('stocks').api;
  const trading = skills.getSkill('trading').api;
  const productivity = skills.getSkill('productivity').api;
  const alerts = skills.getSkill('alerts').api;
  const google = skills.getSkill('google').api;
  const accounting = skills.getSkill('accounting').api;
  const study = skills.getSkill('study').api;
  const strategy = skills.getSkill('strategy').api;
  const russian = skills.getSkill('russian').api;

  ipcMain.handle('aria:config', async () => {
    const b = await brain.status();
    return {
      hasBrain: b.ready,
      brain: b, // { engine, model, ready, local, reason }
      model: b.model,
      wakeWord: config.wakeWord,
      stt: stt.info(),
    };
  });

  // Speech-to-text
  ipcMain.handle('stt:available', () => stt.available());
  ipcMain.handle('stt:info', () => stt.info());
  ipcMain.handle('stt:transcribe', (_e, payload) => stt.transcribe(payload));

  // Brain (natural language / voice). onEvent forwards streaming deltas, tool
  // chips, and the final message to the renderer over the 'brain:event' channel;
  // the resolved promise still carries the final text + history as a fallback.
  ipcMain.handle('aria:ask', async (e, { text, history }) =>
    brain.ask(text, history || [], { onEvent: (evt) => e.sender.send('brain:event', evt) })
  );

  // Direct stock data for panels
  ipcMain.handle('stocks:quote', (_e, symbol) => stocks.getQuote(symbol));
  ipcMain.handle('stocks:quotes', (_e, symbols) => stocks.getQuotes(symbols));
  ipcMain.handle('stocks:search', (_e, query) => stocks.searchSymbol(query));
  ipcMain.handle('stocks:news', (_e, query) => stocks.getNews(query));
  ipcMain.handle('stocks:history', (_e, { symbol, range }) => stocks.getHistory(symbol, range));
  ipcMain.handle('stocks:watchlist', () => stocks.getWatchlist());
  ipcMain.handle('stocks:watchlist:quotes', () => stocks.getQuotes(stocks.getWatchlist()));
  ipcMain.handle('stocks:watchlist:add', (_e, symbol) => stocks.addToWatchlist(symbol));
  ipcMain.handle('stocks:watchlist:remove', (_e, symbol) => stocks.removeFromWatchlist(symbol));
  ipcMain.handle('stocks:candles', (_e, { symbol, range }) => stocks.getCandles(symbol, range));
  ipcMain.handle('stocks:marketNews', () => stocks.getMarketNews());
  ipcMain.handle('stocks:calendar', (_e, symbols) => stocks.getCalendar(symbols));

  // Real-time price ticks (REST-poll provider). Streams to the renderer over
  // 'quote:tick'; returns status so the UI can decide whether to keep polling.
  ipcMain.handle('realtime:subscribe', (e, symbols) =>
    realtime.subscribe(symbols, (tick) => e.sender.send('quote:tick', tick))
  );
  ipcMain.handle('realtime:unsubscribe', () => { realtime.unsubscribe(); return realtime.status(); });
  ipcMain.handle('realtime:status', () => realtime.status());

  // Trading (paper). propose stages an order; only approve fills it.
  ipcMain.handle('trading:portfolio', () => trading.getPortfolio());
  ipcMain.handle('trading:pending', () => trading.listPending());
  ipcMain.handle('trading:propose', (_e, order) => trading.proposeTrade(order));
  ipcMain.handle('trading:approve', (_e, id) => trading.approve(id));
  ipcMain.handle('trading:reject', (_e, id) => trading.reject(id));
  ipcMain.handle('trading:orders', () => trading.getOrders());
  ipcMain.handle('trading:reset', () => trading.resetAccount());

  // Productivity
  ipcMain.handle('prod:tasks', (_e, filter) => productivity.listTasks({ filter }));
  ipcMain.handle('prod:task:add', (_e, t) => productivity.addTask(t));
  ipcMain.handle('prod:task:complete', (_e, id) => productivity.completeTask({ id }));
  ipcMain.handle('prod:task:delete', (_e, id) => productivity.deleteTask({ id }));
  ipcMain.handle('prod:briefing', () => productivity.briefing());

  // Alerts
  ipcMain.handle('alerts:list', () => alerts.listAlerts());
  ipcMain.handle('alerts:add', (_e, a) => alerts.addAlert(a));
  ipcMain.handle('alerts:remove', (_e, id) => alerts.removeAlert({ id }));

  // Google (Gmail + Calendar)
  ipcMain.handle('google:status', () => google.status());
  ipcMain.handle('google:connect', () => google.startAuth());
  ipcMain.handle('google:disconnect', () => google.disconnect());
  ipcMain.handle('google:agenda', () => google.listEvents());
  ipcMain.handle('google:inbox', () => google.listUnread());
  ipcMain.handle('google:event:add', (_e, payload) => google.createEvent(payload));

  // Broker (trading account). The secret never crosses back to the renderer.
  ipcMain.handle('broker:status', () => broker.status());
  ipcMain.handle('broker:connect', (_e, creds) => broker.connect(creds));
  ipcMain.handle('broker:disconnect', () => broker.disconnect());
  ipcMain.handle('broker:encryptionAvailable', () => store.encryptionAvailable());

  // Accounting
  ipcMain.handle('acct:summary', (_e, range) => accounting.summary(range || {}));
  ipcMain.handle('acct:txns', (_e, filter) => accounting.listTransactions(filter || {}));
  ipcMain.handle('acct:txn:add', (_e, t) => accounting.addTransaction(t));
  ipcMain.handle('acct:txn:delete', (_e, id) => accounting.deleteTransaction({ id }));
  ipcMain.handle('acct:categories', () => accounting.categories());
  ipcMain.handle('acct:invoices', (_e, filter) => accounting.listInvoices(filter || {}));
  ipcMain.handle('acct:invoice:add', (_e, inv) => accounting.addInvoice(inv));
  ipcMain.handle('acct:invoice:paid', (_e, id) => accounting.markInvoicePaid({ id }));
  ipcMain.handle('acct:invoice:delete', (_e, id) => accounting.deleteInvoice({ id }));

  // Study
  ipcMain.handle('study:stats', () => study.studyStats());
  ipcMain.handle('study:due', (_e, filter) => study.dueFlashcards(filter || {}));
  ipcMain.handle('study:review', (_e, p) => study.reviewFlashcard(p));
  ipcMain.handle('study:card:add', (_e, c) => study.addFlashcard(c));
  ipcMain.handle('study:vocab:add', (_e, v) => study.addVocab(v));
  ipcMain.handle('study:card:delete', (_e, id) => study.deleteFlashcard({ id }));
  ipcMain.handle('study:notes', (_e, filter) => study.listNotes(filter || {}));
  ipcMain.handle('study:note:add', (_e, n) => study.addNote(n));
  ipcMain.handle('study:note:delete', (_e, id) => study.deleteNote({ id }));
  ipcMain.handle('study:log', (_e, s) => study.logStudy(s));
  ipcMain.handle('study:cpa', () => study.cpaStatus());
  ipcMain.handle('study:cpa:set', (_e, p) => study.setCpaProgress(p));

  // Russian language program (in-depth A1→C2). Direct API for the UI panel;
  // the brain drives the conversational tutoring via its own russian tools.
  ipcMain.handle('russian:progress', () => russian.getProgress());
  ipcMain.handle('russian:curriculum', () => russian.getCurriculum());
  ipcMain.handle('russian:lesson', (_e, id) => russian.getLesson(id));
  ipcMain.handle('russian:alphabet', () => russian.getAlphabet());
  ipcMain.handle('russian:start', (_e, id) => russian.startLesson(id));
  ipcMain.handle('russian:complete', (_e, p) => russian.completeLesson(p));
  ipcMain.handle('russian:setLevel', (_e, level) => russian.setLevel(level));
  ipcMain.handle('russian:seedVocab', (_e, p) => russian.seedVocab(p || {}));
  ipcMain.handle('russian:logPractice', (_e, p) => russian.logPractice(p));
  ipcMain.handle('russian:settings', (_e, s) => russian.setSettings(s));
  ipcMain.handle('russian:review', () => russian.reviewQueue());

  // Trade ideas
  ipcMain.handle('strategy:idea', (_e, symbol) => strategy.tradeIdea(symbol));
  ipcMain.handle('strategy:scan', () => strategy.scanIdeas());
  ipcMain.handle('strategy:tranche', (_e, { symbol, riskPct, equity } = {}) =>
    strategy.buildTranchePlan(symbol, { riskPct, equity })
  );
  ipcMain.handle('strategy:actionPlan', (_e, { symbols } = {}) => strategy.buildActionPlan({ symbols }));

  // iMessage bridge status (macOS)
  ipcMain.handle('imessage:status', () => imessage.available());

  // Telegram bridge status (cross-platform)
  ipcMain.handle('telegram:status', () => telegram.status());
}

module.exports = { register };
