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

    function speak(text) {
      if (!text || !window.speechSynthesis) return;
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.02;
      u.pitch = 1.0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }

    return { supported: true, start, stop, toggle, speak, isListening: () => listening };
  }

  window.createVoice = createVoice;
})();
