'use strict';

// Voice layer — speech via the browser-native Web Speech API, which ships in
// Electron's Chromium with no native dependencies.
//
//   • Wake word: continuous recognition listens for the wake word (default
//     "aria"). On hearing it, it captures the following phrase as a command.
//   • Push-to-talk: the mic button toggles an always-listening mode where any
//     final transcript is treated as a command (no wake word needed).
//   • TTS: speechSynthesis reads replies aloud in a FEMALE voice.
//
// Female-voice guarantee: OS voice lists vary and many default to a male voice
// (e.g. "Microsoft David"). We actively prefer female voices, never auto-pick a
// known male one, and as a last resort raise the pitch so a neutral/male
// fallback still reads female. The user can also pick any installed voice
// explicitly (persisted), which always wins.

(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const SYNTH = window.speechSynthesis || null;
  const SAVED_KEY = 'aria.voiceURI';

  // Heuristics over "name + lang". Female list is broad (Win/macOS/Chrome/Edge
  // voices); male list is a deny-list so we never auto-select a male voice.
  const FEMALE_HINTS = [
    'female', 'woman', 'google uk english female', 'google us english female',
    'hazel', 'susan', 'libby', 'sonia', 'aria', 'zira', 'jenny', 'michelle',
    'eva', 'catherine', 'fiona', 'samantha', 'victoria', 'tessa', 'moira',
    'karen', 'amelie', 'joana', 'serena', 'kate', 'stephanie', 'martha',
    'linda', 'heather', 'hortense', 'paulina', 'helena', 'sara', 'nora',
  ];
  const MALE_HINTS = [
    'male', 'google uk english male', 'google us english male',
    'david', 'mark', 'george', 'james', 'daniel', 'alex', 'fred', 'rishi',
    'ravi', 'oliver', 'thomas', 'guy', 'william', 'liam', 'arthur', 'aaron',
    'eddy', 'reed', 'rocko', 'jorge', 'diego', 'paul',
  ];

  const blob = (v) => (((v && v.name) || '') + ' ' + ((v && v.lang) || '')).toLowerCase();
  const isFemale = (v) => FEMALE_HINTS.some((h) => blob(v).includes(h));
  const isMale = (v) => MALE_HINTS.some((h) => blob(v).includes(h));
  const isEnGB = (v) => !!v && /en[-_]gb/i.test(v.lang || '');
  const isEn = (v) => !!v && /^en/i.test(v.lang || '');

  function getVoices() {
    if (!SYNTH) return [];
    try { return SYNTH.getVoices() || []; } catch { return []; }
  }
  function savedURI() {
    try { return localStorage.getItem(SAVED_KEY) || ''; } catch { return ''; }
  }

  // Pure selection (exposed for tests). A user-saved voice always wins; then
  // en-GB female → en female → any female → en-GB non-male → en non-male →
  // any non-male → first. Result is feminized via pitch if not clearly female.
  function chooseVoice(voices, saved) {
    if (!voices || !voices.length) return null;
    if (saved) {
      const s = voices.find((v) => v.voiceURI === saved || v.name === saved);
      if (s) return s;
    }
    return (
      voices.find((v) => isEnGB(v) && isFemale(v)) ||
      voices.find((v) => isEn(v) && isFemale(v)) ||
      voices.find((v) => isFemale(v)) ||
      voices.find((v) => isEnGB(v) && !isMale(v)) ||
      voices.find((v) => isEn(v) && !isMale(v)) ||
      voices.find((v) => !isMale(v)) ||
      voices[0]
    );
  }

  let chosenVoice = null;
  const voicesListeners = [];

  function resolve() {
    const v = chooseVoice(getVoices(), savedURI());
    if (v) chosenVoice = v;
    voicesListeners.forEach((cb) => { try { cb(); } catch {} });
    return chosenVoice;
  }

  if (SYNTH) {
    resolve();
    if (typeof SYNTH.addEventListener === 'function') SYNTH.addEventListener('voiceschanged', resolve);
    else SYNTH.onvoiceschanged = resolve;
    // Electron populates voices asynchronously and sometimes without firing
    // voiceschanged — poll briefly until they appear.
    let tries = 0;
    const t = setInterval(() => { if (getVoices().length || ++tries > 10) { resolve(); if (getVoices().length || tries > 10) clearInterval(t); } }, 300);
  }

  function speak(text) {
    if (!text || !SYNTH) return;
    const v = chosenVoice || resolve();
    const u = new SpeechSynthesisUtterance(String(text));
    if (v) { u.voice = v; u.lang = v.lang || 'en-GB'; }
    else u.lang = 'en-GB';
    u.rate = 1.0;
    // Female voice → natural; neutral/male fallback → raise pitch to feminize.
    u.pitch = v && isFemale(v) ? 1.06 : 1.18;
    try { SYNTH.cancel(); } catch {}
    SYNTH.speak(u);
  }

  // Renderer-facing voice controls (used by the voice picker UI).
  function listVoices() {
    return getVoices().map((v) => ({
      name: v.name, lang: v.lang, voiceURI: v.voiceURI,
      female: isFemale(v), male: isMale(v),
      current: chosenVoice && v.voiceURI === chosenVoice.voiceURI,
    }));
  }
  function setVoice(uri) {
    try { uri ? localStorage.setItem(SAVED_KEY, uri) : localStorage.removeItem(SAVED_KEY); } catch {}
    chosenVoice = null;
    return resolve();
  }
  function getVoiceURI() { return chosenVoice ? chosenVoice.voiceURI : ''; }
  function onVoices(cb) { if (typeof cb === 'function') voicesListeners.push(cb); }

  // Debug hook so the pure picker can be exercised under automation.
  window.__ariaChooseVoice = (voices, saved) => { const r = chooseVoice(voices, saved); return r ? r.name : null; };

  function createVoice({ wakeWord = 'aria', onCommand, onState } = {}) {
    const base = { listVoices, setVoice, getVoiceURI, onVoices, speak };
    if (!SR) {
      return { supported: false, start() {}, stop() {}, toggle() { return false; }, isListening: () => false, ...base };
    }

    let recognition = null;
    let listening = false;
    let awaitingCommand = false;

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
        if (awaitingCommand) { awaitingCommand = false; dispatch(text); return; }
        if (idx !== -1) {
          const after = text.slice(idx + wakeWord.length).trim().replace(/^[,.!?]+/, '').trim();
          if (after) dispatch(after);
          else { awaitingCommand = true; emitState('awake'); }
        }
      };
      r.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { listening = false; emitState('denied'); }
      };
      r.onend = () => { if (listening) { try { r.start(); } catch {} } };
      return r;
    }

    function dispatch(command) { emitState('heard'); if (onCommand) onCommand(command); }
    function start() {
      if (listening) return;
      recognition = recognition || build();
      listening = true;
      try { recognition.start(); emitState('listening'); } catch {}
    }
    function stop() {
      listening = false; awaitingCommand = false;
      if (recognition) { try { recognition.stop(); } catch {} }
      emitState('off');
    }
    function toggle() { listening ? stop() : start(); return listening; }

    return { supported: true, start, stop, toggle, isListening: () => listening, ...base };
  }

  window.createVoice = createVoice;
})();
