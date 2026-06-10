'use strict';

// Push-to-talk recorder. Captures mic audio with MediaRecorder, then either:
//   • 'pcm16' (local/Vosk): decodes + resamples to 16 kHz mono PCM entirely in
//     the renderer and sends raw samples to the local engine — no audio leaves
//     the machine; or
//   • 'audio' (cloud/whisper-api): sends the recorded audio file.
//
// Mic capture is always local (getUserMedia). The default mode is 'pcm16'.

(function () {
  function arrayBufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(bin);
  }

  // Decode a recorded blob and resample to 16 kHz mono float audio, all local.
  // Returns an ArrayBuffer of Float32 samples (what Whisper expects).
  async function blobToFloat32_16k(blob) {
    const AC = window.AudioContext || window.webkitAudioContext;
    const decodeCtx = new AC();
    let decoded;
    try {
      decoded = await decodeCtx.decodeAudioData(await blob.arrayBuffer());
    } finally {
      decodeCtx.close();
    }
    const targetRate = 16000;
    const frames = Math.ceil(decoded.duration * targetRate);
    const offline = new OfflineAudioContext(1, frames, targetRate);
    const src = offline.createBufferSource();
    src.buffer = decoded;
    src.connect(offline.destination);
    src.start(0);
    const rendered = await offline.startRendering();
    return rendered.getChannelData(0).slice().buffer; // own ArrayBuffer
  }

  function createRecorder({ mode = 'pcm16', onText, onState } = {}) {
    const supported =
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof window.MediaRecorder !== 'undefined';

    let recorder = null;
    let stream = null;
    let chunks = [];
    let recording = false;

    const emit = (s) => onState && onState(s);

    async function start() {
      if (recording || !supported) return;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        emit('denied');
        return;
      }
      chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
      recorder.onstop = async () => {
        recording = false;
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        if (!blob.size) { emit('idle'); return; }
        emit('transcribing');
        try {
          let payload;
          if (mode === 'audio') {
            payload = { base64: arrayBufferToBase64(await blob.arrayBuffer()), mime: blob.type };
          } else {
            const f32 = await blobToFloat32_16k(blob);
            payload = { base64: arrayBufferToBase64(f32), sampleRate: 16000 };
          }
          const res = await window.aria.stt.transcribe(payload);
          emit('idle');
          if (res && res.text) onText && onText(res.text);
          else emit('empty');
        } catch (err) {
          emit('error');
          if (onText) onText(null, err);
        }
      };
      recorder.start();
      recording = true;
      emit('recording');
    }

    function stop() {
      if (recording && recorder) recorder.stop();
    }

    function toggle() {
      recording ? stop() : start();
      return recording;
    }

    return { supported, start, stop, toggle, isRecording: () => recording };
  }

  window.createRecorder = createRecorder;
})();
