'use strict';

// Wires renderer <-> main IPC. Two kinds of channels:
//   1. Direct stock data (UI panels) — work with no API key.
//   2. The AI brain (chat / voice) — needs ANTHROPIC_API_KEY.
const { ipcMain } = require('electron');
const config = require('./config');
const brain = require('./brain');
const skills = require('./services/skills');

function register() {
  const stocks = skills.getSkill('stocks').api;

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
  ipcMain.handle('stocks:history', (_e, { symbol, range }) => stocks.getHistory(symbol, range));
  ipcMain.handle('stocks:watchlist', () => stocks.getWatchlist());
  ipcMain.handle('stocks:watchlist:quotes', () => stocks.getQuotes(stocks.getWatchlist()));
  ipcMain.handle('stocks:watchlist:add', (_e, symbol) => stocks.addToWatchlist(symbol));
  ipcMain.handle('stocks:watchlist:remove', (_e, symbol) => stocks.removeFromWatchlist(symbol));
}

module.exports = { register };
