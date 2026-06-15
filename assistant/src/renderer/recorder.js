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

  // Float32 16 kHz mono samples (an Array of frames) -> the same payload the
  // push-to-talk path produces: { base64, sampleRate: 16000 } of Float32 bytes.
  function framesToPayload(frames, total) {
    const merged = new Float32Array(total);
    let off = 0;
    for (let i = 0; i < frames.length; i++) {
      merged.set(frames[i], off);
      off += frames[i].length;
    }
    return { base64: arrayBufferToBase64(merged.buffer), sampleRate: 16000 };
  }

  function createRecorder({ mode = 'pcm16', onText, onState } = {}) {
    const supported =
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof window.MediaRecorder !== 'undefined';

    const continuousSupported =
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof (window.AudioContext || window.webkitAudioContext) !== 'undefined';

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

    // ---- continuous / hands-free mode (energy-based VAD) ----
    // Keeps the mic open and runs a ScriptProcessor that resamples to 16 kHz and
    // measures per-frame RMS. Speech starts after a few loud frames and ends
    // after ~800ms of silence (hangover); each captured utterance is handed to
    // `onUtterance` as the SAME { base64, sampleRate: 16000 } PCM payload the
    // push-to-talk path produces. Capturing is gated by `gate()` so callers can
    // pause processing while TTS is speaking (avoids transcribing ARIA herself).
    let contCtx = null;          // AudioContext for the live mic graph
    let contStream = null;       // the open MediaStream
    let contNode = null;         // ScriptProcessorNode
    let contSource = null;       // MediaStreamAudioSourceNode
    let contActive = false;
    let contGate = null;         // () => boolean : true means "may capture now"

    const VAD_TARGET_RATE = 16000;
    const VAD_START_RMS = 0.018;   // speech-onset energy threshold
    const VAD_END_RMS = 0.012;     // below this counts toward silence
    const VAD_START_FRAMES = 3;    // consecutive loud frames to start
    const VAD_HANG_MS = 800;       // trailing silence before endpoint
    const VAD_MAX_MS = 15000;      // hard cap per utterance
    const VAD_MIN_MS = 280;        // ignore sub-word blips

    function startContinuous(onUtterance) {
      if (contActive || !continuousSupported) return Promise.resolve(false);
      const AC = window.AudioContext || window.webkitAudioContext;
      return navigator.mediaDevices.getUserMedia({ audio: true }).then((s) => {
        contStream = s;
        contCtx = new AC();
        contSource = contCtx.createMediaStreamSource(contStream);
        const inRate = contCtx.sampleRate || 48000;
        const ratio = inRate / VAD_TARGET_RATE;
        contNode = contCtx.createScriptProcessor(4096, 1, 1);

        let speaking = false;
        let loudRun = 0;
        let silenceMs = 0;
        let spokenMs = 0;
        let frames = [];
        let total = 0;

        const finish = () => {
          const captured = frames;
          const captTotal = total;
          frames = [];
          total = 0;
          speaking = false;
          loudRun = 0;
          silenceMs = 0;
          const ms = (captTotal / VAD_TARGET_RATE) * 1000;
          spokenMs = 0;
          if (captTotal && ms >= VAD_MIN_MS && onUtterance) {
            try { onUtterance(framesToPayload(captured, captTotal)); } catch {}
          }
        };

        // Linear-resample one input block to 16 kHz mono Float32.
        const resample = (input) => {
          const outLen = Math.round(input.length / ratio);
          const out = new Float32Array(outLen);
          for (let i = 0; i < outLen; i++) {
            const src = i * ratio;
            const i0 = Math.floor(src);
            const i1 = Math.min(i0 + 1, input.length - 1);
            const f = src - i0;
            out[i] = input[i0] * (1 - f) + input[i1] * f;
          }
          return out;
        };

        contNode.onaudioprocess = (e) => {
          if (!contActive) return;
          // Feedback guard: while TTS is speaking, drop audio and reset state so
          // ARIA never transcribes her own voice.
          if (contGate && !contGate()) {
            if (speaking) { frames = []; total = 0; speaking = false; loudRun = 0; silenceMs = 0; spokenMs = 0; }
            return;
          }
          const input = e.inputBuffer.getChannelData(0);
          const block = resample(input);
          const blockMs = (block.length / VAD_TARGET_RATE) * 1000;

          let sum = 0;
          for (let i = 0; i < block.length; i++) sum += block[i] * block[i];
          const rms = Math.sqrt(sum / (block.length || 1));

          if (!speaking) {
            if (rms >= VAD_START_RMS) {
              loudRun += 1;
              if (loudRun >= VAD_START_FRAMES) {
                speaking = true;
                silenceMs = 0;
                spokenMs = 0;
                frames = [block];
                total = block.length;
              }
            } else {
              loudRun = 0;
            }
            return;
          }

          // Speaking: keep buffering until enough trailing silence.
          frames.push(block);
          total += block.length;
          spokenMs += blockMs;
          if (rms < VAD_END_RMS) {
            silenceMs += blockMs;
            if (silenceMs >= VAD_HANG_MS) finish();
          } else {
            silenceMs = 0;
          }
          if (spokenMs >= VAD_MAX_MS) finish();
        };

        contSource.connect(contNode);
        // ScriptProcessor only fires when connected to a destination; route to a
        // muted gain so nothing is actually played back.
        const sink = contCtx.createGain();
        sink.gain.value = 0;
        contNode.connect(sink);
        sink.connect(contCtx.destination);
        contActive = true;
        emit('listening');
        return true;
      }).catch(() => {
        stopContinuous();
        emit('denied');
        return false;
      });
    }

    function stopContinuous() {
      contActive = false;
      if (contNode) { try { contNode.disconnect(); contNode.onaudioprocess = null; } catch {} }
      if (contSource) { try { contSource.disconnect(); } catch {} }
      if (contStream) { try { contStream.getTracks().forEach((t) => t.stop()); } catch {} }
      if (contCtx) { try { contCtx.close(); } catch {} }
      contNode = null; contSource = null; contStream = null; contCtx = null;
    }

    // Caller supplies a predicate: returns true when capture is allowed (e.g.
    // false while TTS speaks). Lets renderer pause/resume without restarting.
    function setContinuousGate(fn) { contGate = fn; }

    return {
      supported,
      continuousSupported,
      start,
      stop,
      toggle,
      isRecording: () => recording,
      startContinuous,
      stopContinuous,
      setContinuousGate,
      isContinuous: () => contActive,
    };
  }

  window.createRecorder = createRecorder;
})();
