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
  wakeWord: (process.env.ARIA_WAKE_WORD || 'aria').toLowerCase(),
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
