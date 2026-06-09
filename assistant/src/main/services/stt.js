'use strict';

// Speech-to-text via a Whisper-compatible HTTP API (OpenAI or Groq).
//
// Why this and not the browser SpeechRecognition API: Electron's Chromium does
// not ship Google's speech key, so Web Speech recognition silently fails. Here
// the renderer records mic audio with MediaRecorder and hands the bytes to this
// service, which runs the transcription request from the Node side (no CSP
// limits, no native build). Configure with STT_API_KEY in .env; point
// STT_BASE_URL/STT_MODEL at Groq for a fast, low-cost option.

const config = require('../config');

async function transcribe({ base64, mime }) {
  if (!config.hasStt()) {
    throw new Error('Speech-to-text not configured. Set STT_API_KEY in .env (OpenAI or Groq).');
  }
  if (!base64) throw new Error('No audio captured.');

  const bytes = Buffer.from(base64, 'base64');
  // Blob + FormData are global in Node 18+; fetch sets the multipart boundary.
  const blob = new Blob([bytes], { type: mime || 'audio/webm' });
  const fd = new FormData();
  fd.append('file', blob, 'audio.webm');
  fd.append('model', config.sttModel);
  fd.append('response_format', 'json');

  const res = await fetch(`${config.sttBaseUrl.replace(/\/$/, '')}/audio/transcriptions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${config.sttApiKey}` },
    body: fd,
  });
  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw new Error(`Transcription failed (${res.status}): ${t.slice(0, 200)}`);
  }
  const data = await res.json();
  return { text: (data.text || '').trim() };
}

module.exports = { transcribe, available: () => config.hasStt() };
