'use strict';

// Loads .env (if present) and exposes resolved configuration.
const path = require('path');

try {
  require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });
} catch {
  // dotenv is optional at runtime; env vars may be set by the OS instead.
}

const config = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
  // claude-opus-4-8 is the current most-capable model. Do not downgrade silently.
  model: process.env.ARIA_MODEL || 'claude-opus-4-8',
  // Brain engine: 'local' (Ollama — no API key, runs on-device) or 'claude'
  // (Anthropic API). Default: claude when a key is present, otherwise local.
  brainEngine: (process.env.BRAIN_ENGINE || (process.env.ANTHROPIC_API_KEY ? 'claude' : 'local')).toLowerCase(),
  ollamaUrl: process.env.OLLAMA_URL || 'http://127.0.0.1:11434',
  // qwen2.5 has strong tool-calling; llama3.1:8b also works.
  ollamaModel: process.env.OLLAMA_MODEL || 'qwen2.5:7b',
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
  // Optional extra persona/behavior appended to the brain's system prompt.
  persona: process.env.ARIA_PERSONA || '',
  // Speech-to-text engine: 'local' (on-device Whisper via transformers.js;
  // default) or 'whisper-api' (cloud, opt-in). Local keeps all audio on-device.
  sttEngine: (process.env.STT_ENGINE || 'local').toLowerCase(),
  // Local Whisper model (downloaded once, then cached for offline use).
  whisperModel: process.env.WHISPER_MODEL || 'Xenova/whisper-tiny.en',
  sttModelDir: process.env.STT_MODEL_DIR || '', // optional cache dir override
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
