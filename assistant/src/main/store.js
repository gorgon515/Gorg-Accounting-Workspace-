'use strict';

// Tiny JSON-file persistence in Electron's userData directory.
// Keeps the vertical slice dependency-free; swap for SQLite when modules grow.
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

let filePath = null;
let cache = null;

function init() {
  filePath = path.join(app.getPath('userData'), 'aria-store.json');
  try {
    cache = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    cache = { watchlist: ['AAPL', 'MSFT', 'NVDA'], portfolio: [] };
    flush();
  }
}

function flush() {
  if (!filePath) return;
  try {
    fs.writeFileSync(filePath, JSON.stringify(cache, null, 2));
  } catch (err) {
    console.error('[store] write failed:', err.message);
  }
}

function get(key, fallback) {
  if (!cache) init();
  return key in cache ? cache[key] : fallback;
}

function set(key, value) {
  if (!cache) init();
  cache[key] = value;
  flush();
  return value;
}

module.exports = { init, get, set };
