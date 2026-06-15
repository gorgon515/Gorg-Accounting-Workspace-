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

  // True if the text contains any Cyrillic character — then we speak Russian.
  const CYRILLIC = /[Ѐ-ӿ]/;

  // Pick an installed ru-RU voice if one exists; null means "use the default".
  // speechSynthesis.getVoices() can be empty until voices load asynchronously,
  // so we look it up lazily on each call rather than caching at startup.
  function pickRussianVoice() {
    if (!window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    return (
      voices.find((v) => v.lang === 'ru-RU') ||
      voices.find((v) => /^ru(-|_|$)/i.test(v.lang || '')) ||
      voices.find((v) => /russ/i.test(v.name || '')) ||
      null
    );
  }

  // Speak `text`, auto-switching to Russian (ru-RU + a Russian voice if any) for
  // Cyrillic input and leaving English behavior untouched otherwise. If no
  // Russian voice is installed it still requests ru-RU and never throws.
  function speakText(text) {
    if (!text || !window.speechSynthesis) return;
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    u.pitch = 1.0;
    if (CYRILLIC.test(text)) {
      u.lang = 'ru-RU';
      const rv = pickRussianVoice();
      if (rv) u.voice = rv;
    }
    try { window.speechSynthesis.cancel(); } catch {}
    window.speechSynthesis.speak(u);
  }

  // Standalone helper the renderer can call to speak an arbitrary string (e.g.
  // an alphabet letter) without holding a voice instance. CSP-safe (no inline
  // handlers): the renderer wires this via addEventListener.
  window.ariaSpeak = speakText;

  // True while TTS is actively speaking — the hands-free feedback guard polls
  // this to pause mic capture so ARIA never transcribes her own voice.
  window.ariaIsSpeaking = function () {
    return !!(window.speechSynthesis &&
      (window.speechSynthesis.speaking || window.speechSynthesis.pending));
  };

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
      r.lang = 'en-US';

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

    // Reads replies aloud. Russian (Cyrillic) text auto-uses a ru-RU voice;
    // English is unchanged. See speakText for the detection.
    function speak(text) { speakText(text); }

    return { supported: true, start, stop, toggle, speak, isListening: () => listening };
  }

  window.createVoice = createVoice;
})();
