'use strict';

// Speech-to-text. Default engine is fully LOCAL: on-device Whisper via
// transformers.js (onnxruntime). The renderer captures the mic, resamples to
// 16 kHz mono float audio, and sends the samples here; transcription runs
// in-process. No audio ever leaves the machine.
//
// Only the model weights are fetched once (to a local cache) on first use;
// after that it works offline. Run `npm run model` to pre-download them.
//
// Optional cloud engine (STT_ENGINE=whisper-api) is kept for users who prefer
// it, but local is the default.

const config = require('../config');

let pipePromise = null;

function pkgInstalled() {
  try {
    require.resolve('@huggingface/transformers');
    return true;
  } catch {
    return false;
  }
}

// Lazily build the ASR pipeline once. transformers.js is ESM, so import() it
// from CommonJS.
function getPipeline() {
  if (pipePromise) return pipePromise;
  if (!pkgInstalled()) {
    return Promise.reject(
      new Error('Local speech engine (@huggingface/transformers) is not installed. Run: npm install')
    );
  }
  pipePromise = (async () => {
    const transformers = await import('@huggingface/transformers');
    const { pipeline, env } = transformers;
    if (config.sttModelDir) env.cacheDir = config.sttModelDir;
    return pipeline('automatic-speech-recognition', config.whisperModel);
  })().catch((err) => {
    pipePromise = null; // allow retry on next attempt
    throw err;
  });
  return pipePromise;
}

async function transcribeLocal({ base64 }) {
  const transcriber = await getPipeline();
  const buf = Buffer.from(base64, 'base64');
  // Copy into an aligned ArrayBuffer before viewing as Float32.
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const audio = new Float32Array(ab);
  const out = await transcriber(audio, { chunk_length_s: 30, stride_length_s: 5 });
  return { text: (out.text || '').trim(), engine: 'local-whisper' };
}

async function transcribeCloud({ base64, mime }) {
  if (!config.hasStt()) {
    throw new Error('STT_ENGINE=whisper-api but STT_API_KEY is not set.');
  }
  const blob = new Blob([Buffer.from(base64, 'base64')], { type: mime || 'audio/webm' });
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
  return { text: (data.text || '').trim(), engine: 'whisper-api' };
}

function transcribe(payload) {
  if (config.sttEngine === 'whisper-api') return transcribeCloud(payload);
  if (!payload || !payload.base64) throw new Error('No audio captured.');
  return transcribeLocal(payload);
}

// Whether the configured engine can be used. For local we only require the
// package to be present; the model downloads on first use.
function available() {
  if (config.sttEngine === 'whisper-api') return config.hasStt();
  return pkgInstalled();
}

function info() {
  const local = config.sttEngine !== 'whisper-api';
  return {
    engine: config.sttEngine,
    local,
    available: available(),
    model: local ? config.whisperModel : config.sttModel,
    pkgInstalled: pkgInstalled(),
  };
}

module.exports = { transcribe, available, info };
