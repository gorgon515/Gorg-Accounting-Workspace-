'use strict';

// Tiny JSON-file persistence in Electron's userData directory.
// Keeps the vertical slice dependency-free; swap for SQLite when modules grow.
const fs = require('fs');
const path = require('path');
const { app, safeStorage } = require('electron');

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

// Secret helpers: encrypt at rest with the OS keychain via safeStorage when
// available; fall back to base64 (obfuscation only) with a flag so callers can
// warn. Secrets are stored under their own keys, never returned to the renderer.
function setSecret(key, plaintext) {
  if (plaintext == null) return set(key, null);
  let entry;
  try {
    if (safeStorage && safeStorage.isEncryptionAvailable()) {
      entry = { enc: true, data: safeStorage.encryptString(String(plaintext)).toString('base64') };
    } else {
      entry = { enc: false, data: Buffer.from(String(plaintext), 'utf8').toString('base64') };
    }
  } catch {
    entry = { enc: false, data: Buffer.from(String(plaintext), 'utf8').toString('base64') };
  }
  return set(key, entry);
}

function getSecret(key) {
  const v = get(key, null);
  if (!v || !v.data) return null;
  try {
    if (v.enc && safeStorage && safeStorage.isEncryptionAvailable()) {
      return safeStorage.decryptString(Buffer.from(v.data, 'base64'));
    }
    return Buffer.from(v.data, 'base64').toString('utf8');
  } catch {
    return null;
  }
}

function encryptionAvailable() {
  try {
    return Boolean(safeStorage && safeStorage.isEncryptionAvailable());
  } catch {
    return false;
  }
}

module.exports = { init, get, set, setSecret, getSecret, encryptionAvailable };
