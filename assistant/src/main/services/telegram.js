'use strict';

// Telegram bridge — the cross-platform phone channel (Windows/Linux/macOS).
// Lets the user text ARIA from their phone via a Telegram bot and receive
// replies + price alerts back. This is the practical alternative to iMessage
// on non-Mac systems (Apple provides no iMessage access off macOS).
//
// Uses long polling (getUpdates) — outbound HTTPS only, no inbound port, no
// dependencies. SAFETY: only allowlisted usernames/chat-ids are answered; an
// empty allowlist answers no one. Trade execution still requires in-app
// approval — this channel cannot bypass it.

const config = require('../config');
const store = require('../store');

const api = () => `https://api.telegram.org/bot${config.telegramToken}`;

let polling = false;
let abort = null;

function allowed(msg) {
  if (!config.telegramAllow.length) return false;
  const user = (msg.from?.username || '').toLowerCase();
  const chatId = String(msg.chat?.id || '');
  return config.telegramAllow.some((a) => a === user || a === chatId.toLowerCase());
}

async function tg(method, payload) {
  const res = await fetch(`${api()}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
    signal: abort?.signal,
  });
  const data = await res.json().catch(() => ({}));
  if (!data.ok) throw new Error(data.description || `Telegram ${method} failed (${res.status})`);
  return data.result;
}

async function send(chatId, text) {
  // Telegram caps messages at 4096 chars; split politely.
  const chunks = String(text).match(/[\s\S]{1,3900}/g) || [];
  for (const c of chunks) {
    await tg('sendMessage', { chat_id: chatId, text: c });
  }
}

// Broadcast (e.g. price alerts) to every allowlisted numeric chat id, plus any
// chats we've seen from allowlisted usernames (persisted as telegramChats).
async function broadcast(text) {
  const known = store.get('telegramChats', {});
  const ids = new Set([
    ...config.telegramAllow.filter((a) => /^-?\d+$/.test(a)),
    ...Object.values(known).map(String),
  ]);
  for (const id of ids) {
    try { await send(id, text); } catch { /* per-chat failure is non-fatal */ }
  }
}

function rememberChat(msg) {
  const user = (msg.from?.username || '').toLowerCase();
  if (!user) return;
  const known = store.get('telegramChats', {});
  if (known[user] !== msg.chat.id) {
    known[user] = msg.chat.id;
    store.set('telegramChats', known);
  }
}

// Start long polling. handler(chatId, text) -> reply string (or falsy).
function start(handler) {
  if (!config.telegramToken) return () => {};
  polling = true;
  abort = new AbortController();

  (async () => {
    let offset = store.get('telegramOffset', 0);
    while (polling) {
      try {
        const updates = await tg('getUpdates', { offset, timeout: 25, allowed_updates: ['message'] });
        for (const u of updates) {
          offset = u.update_id + 1;
          store.set('telegramOffset', offset);
          const msg = u.message;
          const text = (msg?.text || '').trim();
          if (!msg || !text) continue;
          if (!allowed(msg)) continue; // silently ignore strangers
          rememberChat(msg);
          if (text === '/start') {
            await send(msg.chat.id, 'ARIA connected. Ask me anything — stocks, trades, tasks, books, study.');
            continue;
          }
          try {
            const reply = await handler(msg.chat.id, text);
            if (reply) await send(msg.chat.id, reply);
          } catch (err) {
            await send(msg.chat.id, `Error: ${err.message}`).catch(() => {});
          }
        }
      } catch (err) {
        if (!polling) break;
        // Network blip or Telegram hiccup — back off and retry.
        await new Promise((r) => setTimeout(r, 5000));
      }
    }
  })();

  return stop;
}

function stop() {
  polling = false;
  try { abort?.abort(); } catch {}
}

async function status() {
  if (!config.telegramToken) {
    return { enabled: false, reason: 'Set TELEGRAM_BOT_TOKEN in .env (create a bot with @BotFather).' };
  }
  if (!config.telegramAllow.length) {
    return { enabled: false, reason: 'Set TELEGRAM_ALLOW to your Telegram @username or chat id.' };
  }
  try {
    const me = await tg('getMe');
    return { enabled: true, bot: me.username ? `@${me.username}` : 'connected', allowCount: config.telegramAllow.length, reason: 'ready' };
  } catch (err) {
    return { enabled: false, reason: `Token check failed: ${err.message}` };
  }
}

module.exports = { start, stop, send, broadcast, allowed, status };
