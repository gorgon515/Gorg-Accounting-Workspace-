'use strict';

// Push-to-talk recorder: captures mic audio with MediaRecorder, then hands the
// bytes to the main process for Whisper transcription. This is the reliable
// voice-input path in Electron (the Web Speech API in voice.js needs a Google
// key that Electron doesn't ship).

(function () {
  function arrayBufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = '';
    const chunk = 0x8000; // avoid call-stack limits on large buffers
    for (let i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(bin);
  }

  function createRecorder({ onText, onState } = {}) {
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
      } catch (err) {
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
          const base64 = arrayBufferToBase64(await blob.arrayBuffer());
          const res = await window.aria.stt.transcribe(base64, blob.type);
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
