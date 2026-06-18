'use strict';

// Loads .env (if present) and exposes resolved configuration.
const path = require('path');
const fs = require('fs');

try {
  require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });
} catch {
  // dotenv is optional at runtime; env vars may be set by the OS instead.
}

const config = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
  // claude-opus-4-8 is the current most-capable model. Do not downgrade silently.
  model: process.env.ARIA_MODEL || 'claude-opus-4-8',
  // Brain engine. 'auto' (default) is fully local with zero setup: Claude if
  // a key is set → Ollama if it's running → the built-in embedded model.
  // Force one with BRAIN_ENGINE=embedded | local | claude.
  brainEngine: (process.env.BRAIN_ENGINE || 'auto').toLowerCase(),
  ollamaUrl: process.env.OLLAMA_URL || 'http://127.0.0.1:11434',
  // qwen2.5 has strong tool-calling; llama3.1:8b also works.
  ollamaModel: process.env.OLLAMA_MODEL || 'qwen2.5:7b',
  // Built-in zero-setup brain: a small instruct model run in-process via
  // transformers.js (CPU). Weights download once, then it works offline.
  embeddedModel: process.env.EMBEDDED_MODEL || 'onnx-community/Qwen2.5-0.5B-Instruct',
  embeddedDtype: process.env.EMBEDDED_DTYPE || 'q4',
  embeddedMaxTokens: Number(process.env.EMBEDDED_MAX_TOKENS || 512),
  wakeWord: (process.env.ARIA_WAKE_WORD || 'aria').toLowerCase(),
  // iMessage bridge (macOS only). Reads ~/Library/Messages/chat.db and replies
  // via AppleScript. Only responds to allowlisted handles (safe default: none).
  imessageEnabled: process.env.IMESSAGE_ENABLED === 'true',
  imessageAllow: (process.env.IMESSAGE_ALLOW || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
  imessageTrigger: (process.env.IMESSAGE_TRIGGER || '').trim().toLowerCase(),
  imessagePollMs: Number(process.env.IMESSAGE_POLL_MS || 4000),
  imessageAlerts: process.env.IMESSAGE_ALERTS !== 'false', // text price alerts too
  // Telegram bridge (works on Windows/anywhere). Create a bot with @BotFather,
  // put its token here, and allowlist your Telegram username or chat id.
  telegramToken: process.env.TELEGRAM_BOT_TOKEN || '',
  telegramAllow: (process.env.TELEGRAM_ALLOW || '')
    .split(',')
    .map((s) => s.trim().replace(/^@/, '').toLowerCase())
    .filter(Boolean),
  telegramAlerts: process.env.TELEGRAM_ALERTS !== 'false',
  // Optional extra persona/behavior appended to the brain's system prompt.
  persona: process.env.ARIA_PERSONA || '',
  // Speech-to-text engine: 'local' (on-device Whisper via transformers.js;
  // default) or 'whisper-api' (cloud, opt-in). Local keeps all audio on-device.
  sttEngine: (process.env.STT_ENGINE || 'local').toLowerCase(),
  // Local Whisper model (downloaded once, then cached for offline use).
  whisperModel: process.env.WHISPER_MODEL || 'Xenova/whisper-tiny.en',
  sttModelDir: process.env.STT_MODEL_DIR || '', // optional cache dir override
  // Where the local AI models live. Installers bundle pre-downloaded weights
  // (resources/models), so the packaged app is fully offline from first
  // launch. Resolution: STT_MODEL_DIR override → bundled dir (if it has
  // content) → '' (transformers.js default cache + download-on-first-use,
  // the from-source path).
  modelsDir: (() => {
    if (process.env.STT_MODEL_DIR) return process.env.STT_MODEL_DIR;
    const candidates = [
      process.resourcesPath ? path.join(process.resourcesPath, 'models') : null,
      path.join(__dirname, '..', '..', 'models'),
    ].filter(Boolean);
    for (const dir of candidates) {
      try {
        if (fs.readdirSync(dir).some((f) => f !== '.gitkeep')) return dir;
      } catch {
        /* missing dir — keep looking */
      }
    }
    return '';
  })(),
  // Cloud fallback (only used when STT_ENGINE=whisper-api).
  sttApiKey: process.env.STT_API_KEY || '',
  sttBaseUrl: process.env.STT_BASE_URL || 'https://api.openai.com/v1',
  sttModel: process.env.STT_MODEL || 'whisper-1',
  hasBrain() {
    return Boolean(this.anthropicApiKey);
  },
  hasStt() {
    return Boolean(this.sttApiKey);
  },
};

module.exports = config;
