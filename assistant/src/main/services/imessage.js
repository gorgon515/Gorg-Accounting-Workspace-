'use strict';

// iMessage bridge — macOS only. There is no Apple API for iMessage; this reads
// the local Messages SQLite DB and sends replies by scripting Messages.app.
// Because the iPhone's iMessages sync to a Mac on the same Apple ID, this lets
// the user text ARIA from their phone and get replies on their phone.
//
// Requirements (macOS): Full Disk Access (to read chat.db) and Automation
// permission for Messages (to send). Uses the system `sqlite3` CLI and
// `osascript` — no native modules.
//
// SAFETY: only responds to handles in IMESSAGE_ALLOW. With an empty allowlist
// it never responds (so a stranger texting the Mac can't drive the assistant).
// Trade execution still requires in-app approval; this channel can't bypass it.

const os = require('os');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const config = require('../config');
const store = require('../store');

const isMac = process.platform === 'darwin';
const CHAT_DB = path.join(os.homedir(), 'Library', 'Messages', 'chat.db');
const SEND_SCRIPT = path.join(os.tmpdir(), 'aria-send-imessage.applescript');

const SEND_APPLESCRIPT = `on run {targetHandle, msgText}
  tell application "Messages"
    set svc to 1st service whose service type = iMessage
    set theBuddy to buddy targetHandle of svc
    send msgText to theBuddy
  end tell
end run`;

let timer = null;

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 4 * 1024 * 1024, ...opts }, (err, stdout, stderr) => {
      if (err) return reject(new Error((stderr || err.message || '').toString().trim()));
      resolve(stdout);
    });
  });
}

function allowed(handle) {
  if (!config.imessageAllow.length) return false;
  const h = String(handle).replace(/[\s()-]/g, '');
  return config.imessageAllow.some((a) => {
    const x = a.replace(/[\s()-]/g, '');
    return h === x || h.endsWith(x) || x.endsWith(h);
  });
}

function available() {
  return {
    platform: process.platform,
    supported: isMac,
    enabled: isMac && config.imessageEnabled,
    dbReadable: isMac ? canRead() : false,
    allowCount: config.imessageAllow.length,
    reason: !isMac
      ? 'iMessage bridge is macOS-only (Apple has no cross-platform API).'
      : !config.imessageEnabled
        ? 'Set IMESSAGE_ENABLED=true in .env.'
        : !config.imessageAllow.length
          ? 'Set IMESSAGE_ALLOW to the phone/email handle(s) ARIA may answer.'
          : !canRead()
            ? 'Grant the app Full Disk Access so it can read Messages.'
            : 'ready',
  };
}

function canRead() {
  try {
    fs.accessSync(CHAT_DB, fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

// Pull new inbound text messages since the last seen ROWID.
async function poll() {
  const last = store.get('imessageLastRow', 0);
  const sql =
    'SELECT m.ROWID as rowid, m.text as text, h.id as handle ' +
    'FROM message m JOIN handle h ON m.handle_id = h.ROWID ' +
    `WHERE m.ROWID > ${Number(last) || 0} AND m.is_from_me = 0 AND m.text IS NOT NULL ` +
    'ORDER BY m.ROWID ASC LIMIT 20;';
  let out;
  try {
    out = await run('sqlite3', ['-json', '-readonly', CHAT_DB, sql]);
  } catch (err) {
    // Likely missing Full Disk Access; surface once and back off.
    console.warn('[imessage] read failed:', err.message);
    return [];
  }
  let rows = [];
  try {
    rows = out.trim() ? JSON.parse(out) : [];
  } catch {
    rows = [];
  }
  if (rows.length) store.set('imessageLastRow', rows[rows.length - 1].rowid);
  return rows;
}

async function send(handle, text) {
  if (!isMac) throw new Error('iMessage send is macOS-only.');
  try {
    if (!fs.existsSync(SEND_SCRIPT)) fs.writeFileSync(SEND_SCRIPT, SEND_APPLESCRIPT);
  } catch { /* tmp write may fail; osascript -e fallback below */ }
  try {
    await run('osascript', [SEND_SCRIPT, String(handle), String(text)]);
  } catch (err) {
    throw new Error(`Messages send failed (${err.message}). Check Automation permission for Messages.`);
  }
}

// Start polling. handler(handle, text) handles an inbound message; it should
// return the reply string (or falsy to stay silent).
function start(handler) {
  if (!isMac || !config.imessageEnabled) return () => {};
  // Initialize lastRow to the current max so we don't replay history on boot.
  primeLastRow().finally(() => {
    timer = setInterval(async () => {
      const rows = await poll();
      for (const r of rows) {
        let text = (r.text || '').trim();
        if (!text || !allowed(r.handle)) continue;
        if (config.imessageTrigger) {
          if (!text.toLowerCase().startsWith(config.imessageTrigger)) continue;
          text = text.slice(config.imessageTrigger.length).replace(/^[\s,:]+/, '').trim();
          if (!text) continue;
        }
        try {
          const reply = await handler(r.handle, text);
          if (reply) await send(r.handle, reply);
        } catch (err) {
          console.warn('[imessage] handler error:', err.message);
        }
      }
    }, Math.max(2000, config.imessagePollMs));
  });
  return stop;
}

async function primeLastRow() {
  if (store.get('imessageLastRow', null) != null) return;
  try {
    const out = await run('sqlite3', ['-readonly', CHAT_DB, 'SELECT IFNULL(MAX(ROWID),0) FROM message;']);
    store.set('imessageLastRow', Number(out.trim()) || 0);
  } catch {
    store.set('imessageLastRow', 0);
  }
}

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}

module.exports = { available, start, stop, send, allowed, isMac };
