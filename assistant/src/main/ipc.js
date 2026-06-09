'use strict';

// Wires renderer <-> main IPC. Two kinds of channels:
//   1. Direct stock data (UI panels) — work with no API key.
//   2. The AI brain (chat / voice) — needs ANTHROPIC_API_KEY.
const { ipcMain } = require('electron');
const config = require('./config');
const brain = require('./brain');
const skills = require('./services/skills');
const broker = require('./services/broker');
const store = require('./store');

function register() {
  const stocks = skills.getSkill('stocks').api;
  const trading = skills.getSkill('trading').api;
  const productivity = skills.getSkill('productivity').api;
  const alerts = skills.getSkill('alerts').api;
  const google = skills.getSkill('google').api;

  ipcMain.handle('aria:config', () => ({
    hasBrain: config.hasBrain(),
    model: config.model,
    wakeWord: config.wakeWord,
  }));

  // Brain (natural language / voice)
  ipcMain.handle('aria:ask', async (_e, { text, history }) => brain.ask(text, history || []));

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

  // Broker (trading account). The secret never crosses back to the renderer.
  ipcMain.handle('broker:status', () => broker.status());
  ipcMain.handle('broker:connect', (_e, creds) => broker.connect(creds));
  ipcMain.handle('broker:disconnect', () => broker.disconnect());
  ipcMain.handle('broker:encryptionAvailable', () => store.encryptionAvailable());
}

module.exports = { register };
