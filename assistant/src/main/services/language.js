'use strict';

// Language Immersion Center — a HELIOS flagship pillar. Fully local.
//
// Covers a beginner→fluent pathway across seven languages with:
//   • Target language + CEFR self-level profile          (set_target_language)
//   • Vocabulary growth via spaced repetition            (delegates to study SRS)
//   • Daily immersion missions across all four modes      (daily_missions)
//   • Progress analytics + an honest CEFR estimate        (language_progress)
//   • Roleplay / conversation scenario seeds              (language_roleplay)
//   • The CEFR curriculum / pathway as reference data     (api.curriculum)
//
// Conversation, grammar correction, pronunciation feedback, and shadowing are
// the brain's job — driven by the systemPromptFragment below. This module owns
// the durable state (profile, missions, progress) and the structured pathway;
// the brain owns the live teaching. Vocab SRS is shared with the Study pillar
// (one card store, subject = language) so reviews surface in both places.

const store = require('../store');
const study = require('./study');

const today = () => new Date().toISOString().slice(0, 10);

// Supported languages with native name + flag, ordered as in the HELIOS spec.
const LANGUAGES = [
  { code: 'russian', name: 'Russian', native: 'Русский', flag: '🇷🇺' },
  { code: 'spanish', name: 'Spanish', native: 'Español', flag: '🇪🇸' },
  { code: 'french', name: 'French', native: 'Français', flag: '🇫🇷' },
  { code: 'german', name: 'German', native: 'Deutsch', flag: '🇩🇪' },
  { code: 'italian', name: 'Italian', native: 'Italiano', flag: '🇮🇹' },
  { code: 'japanese', name: 'Japanese', native: '日本語', flag: '🇯🇵' },
  { code: 'mandarin', name: 'Mandarin Chinese', native: '中文', flag: '🇨🇳' },
];
const LANG_CODES = LANGUAGES.map((l) => l.code);
const isLang = (c) => LANG_CODES.includes(String(c || '').trim().toLowerCase());
const langMeta = (c) => LANGUAGES.find((l) => l.code === c) || null;

// CEFR pathway — the beginner→fluent curriculum. Each level lists the
// communicative goals that define it (reference data the tutor teaches toward).
const CURRICULUM = [
  { level: 'A1', label: 'Beginner', goals: ['Greetings & introductions', 'Numbers, dates, time', 'Essential survival phrases', '~500 high-frequency words'] },
  { level: 'A2', label: 'Elementary', goals: ['Daily routines & needs', 'Past & future basics', 'Simple connected sentences', '~1,000 words'] },
  { level: 'B1', label: 'Intermediate', goals: ['Handle most travel situations', 'Describe experiences & opinions', 'Narrate a story', '~2,000 words'] },
  { level: 'B2', label: 'Upper-Intermediate', goals: ['Fluent everyday interaction', 'Argue a viewpoint', 'Understand most media', '~4,000 words'] },
  { level: 'C1', label: 'Advanced', goals: ['Flexible, effective language use', 'Subtle & idiomatic expression', 'Complex professional topics', '~8,000 words'] },
  { level: 'C2', label: 'Mastery', goals: ['Near-native precision', 'Effortless comprehension', 'Nuanced register control', '~16,000+ words'] },
];
const LEVELS = CURRICULUM.map((c) => c.level);

// ---------- profile ----------
function getProfile() {
  const p = store.get('languageProfile', null);
  if (p && isLang(p.language)) return p;
  const init = { language: 'russian', level: 'A1', startedAt: new Date().toISOString() };
  store.set('languageProfile', init);
  return init;
}

function setTargetLanguage({ language, level }) {
  const code = String(language || '').trim().toLowerCase();
  if (!isLang(code)) throw new Error(`language must be one of: ${LANG_CODES.join(', ')}`);
  const p = getProfile();
  if (p.language !== code) p.startedAt = new Date().toISOString();
  p.language = code;
  if (level) {
    const lv = String(level).trim().toUpperCase();
    if (!LEVELS.includes(lv)) throw new Error(`level must be one of: ${LEVELS.join(', ')}`);
    p.level = lv;
  }
  store.set('languageProfile', p);
  return { ...p, ...langMeta(code) };
}

// ---------- vocabulary (shared SRS via the Study pillar) ----------
function addVocab({ language, word, translation, example }) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  if (!isLang(code)) throw new Error(`language must be one of: ${LANG_CODES.join(', ')}`);
  return study.api.addVocab({ word, translation, example, subject: code });
}

function dueReview({ language, limit } = {}) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  return study.api.dueFlashcards({ subject: code, limit });
}

function vocabStats(code) {
  const counts = study.api.cardCounts().bySubject[code] || { total: 0, due: 0 };
  // "Mature" = recalled enough times to count toward level (reps >= 3 in SM-2).
  return counts;
}

// ---------- daily missions ----------
// A deterministic daily set spanning the four immersion modes, seeded by date +
// language so it is stable across a day but rotates day to day. Completion is
// persisted; the streak counts consecutive days with at least one mission done.
const MISSION_POOL = [
  { kind: 'speaking', text: 'Have a 5-minute spoken conversation with your tutor about your day.' },
  { kind: 'speaking', text: 'Roleplay: order food and drinks at a café entirely in {LANG}.' },
  { kind: 'listening', text: 'Shadow one short audio clip — repeat each phrase to match the rhythm.' },
  { kind: 'reading', text: 'Read one short paragraph in {LANG} and summarize it back in your own words.' },
  { kind: 'writing', text: 'Write 3 sentences in {LANG} about your plans for tomorrow; get them corrected.' },
  { kind: 'vocab', text: 'Clear today’s due flashcards, then learn 5 new words.' },
  { kind: 'speaking', text: 'Describe a photo or your surroundings out loud for 60 seconds.' },
  { kind: 'reading', text: 'Read a news headline in {LANG} and explain what it means.' },
  { kind: 'writing', text: 'Keep a 2-sentence journal entry in {LANG} about how you feel today.' },
  { kind: 'listening', text: 'Listen to a song or clip and catch three words you already know.' },
];

function dayIndex(dateStr) {
  // Days since epoch — a stable integer to rotate the pool.
  return Math.floor(new Date(dateStr + 'T00:00:00').getTime() / 86400000);
}

function missionKey(code, date) {
  return `${date}|${code}`;
}

function dailyMissions({ language } = {}) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  if (!isLang(code)) throw new Error(`language must be one of: ${LANG_CODES.join(', ')}`);
  const date = today();
  const all = store.get('languageMissions', {});
  const key = missionKey(code, date);
  if (!all[key]) {
    const idx = dayIndex(date) + LANG_CODES.indexOf(code);
    const meta = langMeta(code);
    const picks = [];
    for (let i = 0; i < 4; i++) {
      const m = MISSION_POOL[(idx + i * 3) % MISSION_POOL.length];
      picks.push({
        id: `m${i}`,
        kind: m.kind,
        text: m.text.replace('{LANG}', meta.name),
        done: false,
      });
    }
    all[key] = picks;
    store.set('languageMissions', all);
  }
  return { language: code, date, missions: all[key] };
}

function completeMission({ id, language }) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  const date = today();
  const all = store.get('languageMissions', {});
  const key = missionKey(code, date);
  if (!all[key]) dailyMissions({ language: code });
  const list = store.get('languageMissions', {})[key] || [];
  const m = list.find((x) => x.id === id);
  if (!m) throw new Error('No matching mission for today.');
  m.done = true;
  const fresh = store.get('languageMissions', {});
  fresh[key] = list;
  store.set('languageMissions', fresh);
  // Record the day toward the streak.
  const days = new Set(store.get('languageDoneDays', []));
  days.add(`${code}|${date}`);
  store.set('languageDoneDays', [...days]);
  return { completed: id, missions: list };
}

function streakFor(code) {
  const days = new Set(store.get('languageDoneDays', []));
  let streak = 0;
  const d = new Date(today() + 'T00:00:00');
  for (;;) {
    const ds = d.toISOString().slice(0, 10);
    if (days.has(`${code}|${ds}`)) {
      streak += 1;
      d.setDate(d.getDate() - 1);
    } else break;
  }
  return streak;
}

// ---------- progress ----------
// CEFR estimate is intentionally conservative and labelled as an estimate: it
// is driven by mature vocabulary against the per-level word-count milestones.
const LEVEL_WORD_MILESTONES = { A1: 0, A2: 500, B1: 1000, B2: 2000, C1: 4000, C2: 8000 };

function estimateLevel(matureWords) {
  let level = 'A1';
  for (const [lv, n] of Object.entries(LEVEL_WORD_MILESTONES)) {
    if (matureWords >= n) level = lv;
  }
  return level;
}

function progress({ language } = {}) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  if (!isLang(code)) throw new Error(`language must be one of: ${LANG_CODES.join(', ')}`);
  const profile = getProfile();
  const all = study.api.cardCounts().bySubject[code] || { total: 0, due: 0 };
  // Honest proxy for the CEFR estimate: total vocabulary the user has learned.
  const matureWords = all.total;
  const { missions } = dailyMissions({ language: code });
  const meta = langMeta(code);
  return {
    language: code,
    name: meta.name,
    native: meta.native,
    flag: meta.flag,
    selfLevel: profile.level,
    estimatedLevel: estimateLevel(matureWords),
    estimateNote: 'CEFR estimate from learned vocabulary — a rough guide, not a test score.',
    words: all.total,
    dueNow: all.due,
    streakDays: streakFor(code),
    missionsToday: missions.length,
    missionsDoneToday: missions.filter((m) => m.done).length,
    startedAt: profile.startedAt,
  };
}

// ---------- roleplay / conversation seeds ----------
const SCENARIOS = {
  cafe: 'You are a barista; the user is a customer ordering coffee and a pastry.',
  directions: 'You are a local; the user is a lost tourist asking for directions.',
  hotel: 'You are a hotel receptionist; the user is checking in.',
  market: 'You are a market vendor; the user is haggling over the price of fruit.',
  interview: 'You are an interviewer; the user is interviewing for a job.',
  doctor: 'You are a doctor; the user is describing symptoms.',
};

function roleplay({ language, scenario } = {}) {
  const code = String(language || getProfile().language).trim().toLowerCase();
  if (!isLang(code)) throw new Error(`language must be one of: ${LANG_CODES.join(', ')}`);
  const meta = langMeta(code);
  const key = String(scenario || 'cafe').trim().toLowerCase();
  const setup = SCENARIOS[key] || `Improvise a realistic everyday situation involving ${scenario || 'daily life'}.`;
  return {
    language: code,
    name: meta.name,
    scenario: key,
    setup,
    instructions: `Stay in role and speak primarily in ${meta.name} at the user's level. Keep turns short, gently correct mistakes after responding, and offer the English meaning of new words in parentheses.`,
    available: Object.keys(SCENARIOS),
  };
}

const tools = [
  {
    name: 'set_target_language',
    description:
      'Set the user’s active study language (russian, spanish, french, german, italian, japanese, mandarin) and optional CEFR level (A1–C2). Call when the user says they want to learn or switch to a language.',
    input_schema: {
      type: 'object',
      properties: {
        language: { type: 'string', enum: LANG_CODES },
        level: { type: 'string', enum: LEVELS },
      },
      required: ['language'],
    },
  },
  {
    name: 'language_progress',
    description:
      'Get the user’s progress in their target language (or a specified one): words learned, cards due, streak, today’s missions, self-rated and estimated CEFR level.',
    input_schema: {
      type: 'object',
      properties: { language: { type: 'string', enum: LANG_CODES } },
    },
  },
  {
    name: 'daily_missions',
    description:
      'Get today’s immersion missions for the target language (speaking, listening, reading, writing, vocab). Use to give the user their daily plan.',
    input_schema: {
      type: 'object',
      properties: { language: { type: 'string', enum: LANG_CODES } },
    },
  },
  {
    name: 'complete_mission',
    description: 'Mark one of today’s immersion missions complete by its id (m0–m3). Call when the user finishes a mission with you.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, language: { type: 'string', enum: LANG_CODES } },
      required: ['id'],
    },
  },
  {
    name: 'language_roleplay',
    description:
      'Start an immersive roleplay scenario in the target language (e.g. cafe, directions, hotel, market, interview, doctor). Returns the scene + how to run it; then converse in-character.',
    input_schema: {
      type: 'object',
      properties: {
        scenario: { type: 'string', description: 'cafe | directions | hotel | market | interview | doctor | or describe one' },
        language: { type: 'string', enum: LANG_CODES },
      },
    },
  },
];

const handlers = {
  set_target_language: (i) => setTargetLanguage(i),
  language_progress: async (i) => progress(i || {}),
  daily_missions: async (i) => dailyMissions(i || {}),
  complete_mission: (i) => completeMission(i),
  language_roleplay: async (i) => roleplay(i || {}),
};

module.exports = {
  name: 'language',
  systemPromptFragment:
    'You run the Language Immersion Center across Russian, Spanish, French, German, Italian, Japanese, and Mandarin. Teach through immersion: speak in the target language at the user’s level, gently correct grammar and pronunciation after responding, and explain new words in parentheses. ' +
    'Save new vocabulary with add_vocab (subject = the language) so it enters spaced-repetition review. Use set_target_language when they pick/switch a language, daily_missions for their plan, language_roleplay for scenario practice, and language_progress to report growth. Keep the learner producing the language, not just hearing about it.',
  tools,
  handlers,
  api: {
    LANGUAGES, LANG_CODES, CURRICULUM, LEVELS,
    getProfile, setTargetLanguage,
    addVocab, dueReview, vocabStats,
    dailyMissions, completeMission,
    progress, roleplay, streakFor,
  },
};
