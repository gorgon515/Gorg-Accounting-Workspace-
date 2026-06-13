'use strict';

// Voice layer — day-one speech using the browser-native Web Speech API, which
// ships in Electron's Chromium with no native dependencies.
//
//   • Wake word: continuous recognition listens for the wake word (default
//     "aria"). On hearing it, it captures the following phrase as a command.
//   • Push-to-talk: the mic button toggles an always-listening mode where any
//     final transcript is treated as a command (no wake word needed).
//   • TTS: speechSynthesis reads replies aloud.
//
// This is the pragmatic MVP. For a robust always-on wake word later, swap in a
// dedicated wake-word engine (e.g. Porcupine) behind this same interface.

(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  // ---- TTS voice selection: prefer an en-GB female voice ("British woman") ----
  // Voices load asynchronously in Chromium; we resolve once and cache the pick,
  // re-resolving whenever the voice list changes.
  const SYNTH = window.speechSynthesis || null;
  // Preferred named voices, best first. These are the common en-GB female voices
  // across Chrome/Edge/macOS; the first one that exists wins.
  const PREFERRED_VOICE_NAMES = [
    'Google UK English Female',
    'Microsoft Hazel',
    'Microsoft Susan',
    'Microsoft Libby',
    'Serena',
    'Kate',
    'Stephanie',
    'Martha',
  ];
  let chosenVoice = null;

  function isEnGB(v) {
    return v && typeof v.lang === 'string' && v.lang.toLowerCase().replace('_', '-').startsWith('en-gb');
  }

  // Pick the best available voice given the preference order in the spec.
  function pickVoice() {
    if (!SYNTH) return null;
    let voices = [];
    try { voices = SYNTH.getVoices() || []; } catch { voices = []; }
    if (!voices.length) return chosenVoice; // not loaded yet; keep prior pick

    // 1) Preferred named voices (case-insensitive, allow partial match on name).
    for (const name of PREFERRED_VOICE_NAMES) {
      const want = name.toLowerCase();
      const hit = voices.find((v) => (v.name || '').toLowerCase().includes(want));
      if (hit) { chosenVoice = hit; return chosenVoice; }
    }
    // 2) First voice whose lang is en-GB.
    const gb = voices.find(isEnGB);
    if (gb) { chosenVoice = gb; return chosenVoice; }
    // 3) Any English voice.
    const en = voices.find((v) => typeof v.lang === 'string' && v.lang.toLowerCase().startsWith('en'));
    if (en) { chosenVoice = en; return chosenVoice; }
    // 4) Fall back to whatever default the engine has.
    chosenVoice = chosenVoice || voices[0] || null;
    return chosenVoice;
  }

  if (SYNTH) {
    // Resolve now (may be empty on first call) and again when the list loads.
    pickVoice();
    if (typeof SYNTH.addEventListener === 'function') {
      SYNTH.addEventListener('voiceschanged', pickVoice);
    } else {
      // Older API surface.
      SYNTH.onvoiceschanged = pickVoice;
    }
  }

  function createVoice({ wakeWord = 'aria', onCommand, onState } = {}) {
    if (!SR) {
      return { supported: false, start() {}, stop() {}, speak() {}, toggle() { return false; } };
    }

    let recognition = null;
    let listening = false;
    let awaitingCommand = false; // true right after wake word heard

    function emitState(s) { if (onState) onState(s); }

    function build() {
      const r = new SR();
      r.continuous = true;
      r.interimResults = false;
      r.lang = 'en-GB';

      r.onresult = (event) => {
        const result = event.results[event.results.length - 1];
        if (!result.isFinal) return;
        const text = result[0].transcript.trim();
        if (!text) return;

        const lower = text.toLowerCase();
        const idx = lower.indexOf(wakeWord);

        if (awaitingCommand) {
          awaitingCommand = false;
          dispatch(text);
          return;
        }
        if (idx !== -1) {
          // Wake word present — take whatever follows it as the command.
          const after = text.slice(idx + wakeWord.length).trim().replace(/^[,.!?]+/, '').trim();
          if (after) {
            dispatch(after);
          } else {
            awaitingCommand = true;
            emitState('awake');
          }
        }
      };

      r.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          listening = false;
          emitState('denied');
        }
      };

      // Auto-restart so listening stays continuous across browser timeouts.
      r.onend = () => {
        if (listening) {
          try { r.start(); } catch { /* already starting */ }
        }
      };

      return r;
    }

    function dispatch(command) {
      emitState('heard');
      if (onCommand) onCommand(command);
    }

    function start() {
      if (listening) return;
      recognition = recognition || build();
      listening = true;
      try { recognition.start(); emitState('listening'); }
      catch { /* may already be running */ }
    }

    function stop() {
      listening = false;
      awaitingCommand = false;
      if (recognition) { try { recognition.stop(); } catch {} }
      emitState('off');
    }

    function toggle() { listening ? stop() : start(); return listening; }

    function speak(text) {
      if (!text || !window.speechSynthesis) return;
      const u = new SpeechSynthesisUtterance(text);
      // British woman: gentle, natural cadence.
      u.lang = 'en-GB';
      u.rate = 0.98;
      u.pitch = 1.05;
      // Ensure we have a pick even if voiceschanged hasn't fired yet.
      const v = chosenVoice || pickVoice();
      if (v) u.voice = v;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }

    return { supported: true, start, stop, toggle, speak, isListening: () => listening };
  }

  window.createVoice = createVoice;
})();
