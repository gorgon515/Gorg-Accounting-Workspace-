'use strict';

// Study pillar — fully local. Covers:
//   • Notes      — study material by subject (e.g. "russian", "cpa-far")
//   • Flashcards — spaced repetition (SM-2), incl. language vocab
//   • Study log  — minutes/topic per session, with stats + streak
//   • CPA tracker— Becker exam-prep progress per section (manual; no Becker API)
//   • Russian    — built-in curriculum: themed vocab corpus + grammar lessons
//
// "Synopsis" is the brain's job: it reads saved notes via list_notes and writes
// a summary. Russian tutoring is the brain conversing + saving vocab as cards.

const store = require('../store');
const russianData = require('./russian-data');

const ledgerKeys = { notes: 'studyNotes', cards: 'flashcards', log: 'studyLog', cpa: 'cpaProgress' };
const get = (k, d) => store.get(ledgerKeys[k], d);
const set = (k, v) => store.set(ledgerKeys[k], v);
const newId = (p) => p + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const today = () => new Date().toISOString().slice(0, 10);
const addDays = (d, n) => {
  const dt = new Date(d + 'T00:00:00');
  dt.setDate(dt.getDate() + n);
  return dt.toISOString().slice(0, 10);
};

// CPA Evolution sections: 3 core + 3 discipline.
const CPA_SECTIONS = ['AUD', 'FAR', 'REG', 'BAR', 'ISC', 'TCP'];

// ---------- notes ----------
function addNote({ subject, title, text }) {
  if (!text || !String(text).trim()) throw new Error('note text is required');
  const n = {
    id: newId('note'),
    subject: (subject && String(subject).trim().toLowerCase()) || 'general',
    title: (title && String(title).trim()) || '',
    text: String(text).trim(),
    createdAt: new Date().toISOString(),
  };
  const list = get('notes', []);
  list.unshift(n);
  if (list.length > 500) list.length = 500;
  set('notes', list);
  return n;
}

function listNotes({ subject, limit } = {}) {
  let list = get('notes', []);
  if (subject) list = list.filter((n) => n.subject === String(subject).trim().toLowerCase());
  return limit ? list.slice(0, limit) : list;
}

function deleteNote({ id }) {
  set('notes', get('notes', []).filter((n) => n.id !== id));
  return { deleted: id };
}

// ---------- flashcards (SM-2) ----------
function addFlashcard({ front, back, subject }) {
  if (!front || !back) throw new Error('front and back are required');
  const c = {
    id: newId('card'),
    subject: (subject && String(subject).trim().toLowerCase()) || 'general',
    front: String(front).trim(),
    back: String(back).trim(),
    ease: 2.5,
    interval: 0,
    reps: 0,
    due: today(),
    lastReview: null,
    createdAt: new Date().toISOString(),
  };
  const list = get('cards', []);
  list.push(c);
  set('cards', list);
  return c;
}

// Convenience for language learning (e.g. Russian).
function addVocab({ word, translation, example, subject }) {
  if (!word || !translation) throw new Error('word and translation are required');
  const back = example ? `${translation}\n\ne.g. ${example}` : translation;
  return addFlashcard({ front: word, back, subject: subject || 'russian' });
}

function dueFlashcards({ subject, limit } = {}) {
  const t = today();
  let list = get('cards', []).filter((c) => c.due <= t);
  if (subject) list = list.filter((c) => c.subject === String(subject).trim().toLowerCase());
  list.sort((a, b) => (a.due < b.due ? -1 : 1));
  return limit ? list.slice(0, limit) : list;
}

// grade: 0–5 (SM-2). <3 = lapse (reset). >=3 = recalled.
function reviewFlashcard({ id, grade }) {
  grade = Math.max(0, Math.min(5, Number(grade)));
  const list = get('cards', []);
  const c = list.find((x) => x.id === id);
  if (!c) throw new Error('No matching flashcard.');
  if (grade < 3) {
    c.reps = 0;
    c.interval = 1;
  } else {
    c.ease = Math.max(1.3, c.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)));
    c.reps += 1;
    c.interval = c.reps === 1 ? 1 : c.reps === 2 ? 6 : Math.round(c.interval * c.ease);
  }
  c.due = addDays(today(), c.interval);
  c.lastReview = today();
  set('cards', list);
  return c;
}

function deleteFlashcard({ id }) {
  set('cards', get('cards', []).filter((c) => c.id !== id));
  return { deleted: id };
}

function cardCounts() {
  const list = get('cards', []);
  const t = today();
  const bySubject = {};
  list.forEach((c) => {
    bySubject[c.subject] = bySubject[c.subject] || { total: 0, due: 0 };
    bySubject[c.subject].total += 1;
    if (c.due <= t) bySubject[c.subject].due += 1;
  });
  return { total: list.length, due: list.filter((c) => c.due <= t).length, bySubject };
}

// ---------- study log ----------
function logStudy({ subject, minutes, topic }) {
  minutes = Math.round(Number(minutes));
  if (!Number.isFinite(minutes) || minutes <= 0) throw new Error('minutes must be a positive number');
  const e = {
    id: newId('ses'),
    subject: (subject && String(subject).trim().toLowerCase()) || 'general',
    minutes,
    topic: (topic && String(topic).trim()) || '',
    date: today(),
    at: new Date().toISOString(),
  };
  const list = get('log', []);
  list.unshift(e);
  set('log', list);
  return e;
}

function studyStats() {
  const list = get('log', []);
  const bySubject = {};
  list.forEach((e) => { bySubject[e.subject] = (bySubject[e.subject] || 0) + e.minutes; });
  // streak: consecutive days up to today with any session
  const days = new Set(list.map((e) => e.date));
  let streak = 0;
  let d = today();
  while (days.has(d)) {
    streak += 1;
    d = addDays(d, -1);
  }
  const totalMinutes = list.reduce((s, e) => s + e.minutes, 0);
  return { totalMinutes, bySubject: bySubject, streakDays: streak, cards: cardCounts() };
}

// ---------- CPA tracker (Becker — manual) ----------
function cpaState() {
  const s = get('cpa', null);
  if (s) return s;
  const sections = {};
  CPA_SECTIONS.forEach((k) => (sections[k] = { progress: 0, status: 'not started', examDate: null }));
  const init = { provider: 'Becker', sections };
  set('cpa', init);
  return init;
}

function setCpaProgress({ section, progress, status, examDate }) {
  section = String(section || '').trim().toUpperCase();
  if (!CPA_SECTIONS.includes(section)) throw new Error(`section must be one of ${CPA_SECTIONS.join(', ')}`);
  const s = cpaState();
  const sec = s.sections[section];
  if (progress != null) sec.progress = Math.max(0, Math.min(100, Math.round(Number(progress))));
  if (status) sec.status = String(status).trim();
  if (examDate !== undefined) sec.examDate = examDate ? String(examDate).slice(0, 10) : null;
  set('cpa', s);
  return s;
}

function cpaStatus() {
  const s = cpaState();
  const sections = Object.entries(s.sections).map(([k, v]) => ({ section: k, ...v }));
  const overall = Math.round(sections.reduce((a, v) => a + v.progress, 0) / sections.length);
  return { provider: s.provider, sections, overallProgress: overall, link: 'https://www.becker.com/cpa-review' };
}

// ---------- Russian curriculum ----------

/** List all themes present in the corpus with entry counts. */
function russianThemes() {
  return russianData.vocabThemes();
}

/** Return vocab entries, optionally filtered by theme and/or capped at limit. */
function russianVocab({ theme, limit } = {}) {
  return russianData.filterVocab({ theme, limit });
}

/** Return grammar lessons, optionally filtered by level ('beginner'|'intermediate'). */
function russianLessons({ level } = {}) {
  return russianData.filterGrammar({ level });
}

/** Return a single grammar lesson by its id string. Throws if not found. */
function russianLesson({ id }) {
  if (!id) throw new Error('id is required');
  return russianData.findLesson({ id });
}

/**
 * Bulk-load corpus vocab into the SM-2 flashcard system as Russian cards.
 * Idempotent: skips words already present as russian cards (matched by front/ru).
 * Optionally scoped to one theme. Returns { added, skipped, total }.
 */
function seedRussianVocab({ theme } = {}) {
  const seededKey = 'russianSeeded';
  const alreadySeeded = store.get(seededKey, {});

  const entries = russianData.filterVocab({ theme });
  const existing = get('cards', [])
    .filter((c) => c.subject === 'russian')
    .map((c) => c.front);
  const existingSet = new Set(existing);

  let added = 0;
  let skipped = 0;

  entries.forEach((entry) => {
    const front = entry.ru;
    if (existingSet.has(front)) {
      skipped += 1;
      return;
    }
    const back = `${entry.translit} — ${entry.en}`;
    addFlashcard({ front, back, subject: 'russian' });
    existingSet.add(front);
    added += 1;
  });

  // Record which themes have been seeded to speed up future idempotency checks.
  const themeKey = theme ? String(theme).trim().toLowerCase() : '__all__';
  alreadySeeded[themeKey] = true;
  store.set(seededKey, alreadySeeded);

  return { added, skipped, total: added + skipped };
}

const tools = [
  {
    name: 'add_note',
    description: 'Save study material/notes under a subject (e.g. "russian", "cpa-far"). Use when the user shares material to remember or wants to capture a lesson. To produce a synopsis, call list_notes for the subject and summarize.',
    input_schema: {
      type: 'object',
      properties: { subject: { type: 'string' }, title: { type: 'string' }, text: { type: 'string' } },
      required: ['text'],
    },
  },
  {
    name: 'list_notes',
    description: 'Retrieve saved study notes, optionally for one subject. Use this to gather material before writing a synopsis or summary of what the user is learning.',
    input_schema: {
      type: 'object',
      properties: { subject: { type: 'string' }, limit: { type: 'number' } },
    },
  },
  {
    name: 'add_flashcard',
    description: 'Create a flashcard (front/back) for spaced-repetition review under a subject.',
    input_schema: {
      type: 'object',
      properties: { front: { type: 'string' }, back: { type: 'string' }, subject: { type: 'string' } },
      required: ['front', 'back'],
    },
  },
  {
    name: 'add_vocab',
    description: 'Add a language vocabulary card (defaults to subject "russian"): a word/phrase, its translation, and an optional example sentence. Use when teaching the user Russian or other-language vocabulary.',
    input_schema: {
      type: 'object',
      properties: {
        word: { type: 'string', description: 'The foreign word/phrase (e.g. Russian)' },
        translation: { type: 'string' },
        example: { type: 'string' },
        subject: { type: 'string' },
      },
      required: ['word', 'translation'],
    },
  },
  {
    name: 'due_flashcards',
    description: 'Get flashcards due for review now (optionally by subject). Use to quiz the user.',
    input_schema: {
      type: 'object',
      properties: { subject: { type: 'string' }, limit: { type: 'number' } },
    },
  },
  {
    name: 'review_flashcard',
    description: 'Grade a flashcard review (0–5; below 3 means forgotten) to reschedule it. Call after the user answers a card you quizzed them on.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, grade: { type: 'number' } },
      required: ['id', 'grade'],
    },
  },
  {
    name: 'log_study',
    description: 'Log a study session (minutes + topic) for a subject. Use when the user finishes studying or asks to track time.',
    input_schema: {
      type: 'object',
      properties: { subject: { type: 'string' }, minutes: { type: 'number' }, topic: { type: 'string' } },
      required: ['minutes'],
    },
  },
  {
    name: 'study_stats',
    description: 'Get study stats: minutes by subject, day streak, and flashcard counts (total/due).',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'cpa_status',
    description: 'Get Becker CPA exam-prep progress: per-section progress, status, exam dates, and overall percent.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'set_cpa_progress',
    description: 'Update Becker CPA progress for a section (AUD, FAR, REG, BAR, ISC, TCP): progress percent, status, and/or exam date.',
    input_schema: {
      type: 'object',
      properties: {
        section: { type: 'string', enum: CPA_SECTIONS },
        progress: { type: 'number', description: '0–100' },
        status: { type: 'string' },
        examDate: { type: 'string', description: 'YYYY-MM-DD' },
      },
      required: ['section'],
    },
  },
  {
    name: 'russian_vocab',
    description: 'Retrieve Russian vocabulary entries from the built-in corpus. Call this when the user asks for Russian vocabulary, wants to study a specific theme (e.g. "greetings", "verbs", "food"), or when you need words to teach from. Pass theme to filter by category; pass limit to cap the result.',
    input_schema: {
      type: 'object',
      properties: {
        theme: { type: 'string', description: 'Vocab theme, e.g. "greetings", "verbs", "food", "numbers", "travel". Omit for all.' },
        limit: { type: 'number', description: 'Max number of entries to return.' },
      },
    },
  },
  {
    name: 'russian_lessons',
    description: 'List Russian grammar lessons from the built-in curriculum, optionally filtered by level. Call this when the user asks about Russian grammar, wants a lesson on a topic (cases, verbs, adjectives, etc.), or needs an overview of available grammar content.',
    input_schema: {
      type: 'object',
      properties: {
        level: { type: 'string', enum: ['beginner', 'intermediate'], description: 'Filter by difficulty. Omit for all.' },
      },
    },
  },
  {
    name: 'russian_grammar',
    description: 'Get the full text of a single Russian grammar lesson by its id. Call this when the user asks to learn or review a specific grammar topic (e.g. "accusative case", "verb aspect", "past tense"). Use russian_lessons first to find the right id if you are unsure.',
    input_schema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'Lesson id, e.g. "accusative", "aspect", "past_tense", "gender". See russian_lessons for the full list.' },
      },
      required: ['id'],
    },
  },
  {
    name: 'seed_russian',
    description: 'Bulk-add Russian corpus vocabulary into the SM-2 flashcard deck (subject "russian"). Idempotent — will not create duplicates. Call this when the user asks to load, seed, or import Russian vocabulary into their flashcard deck. Optionally scoped to one theme.',
    input_schema: {
      type: 'object',
      properties: {
        theme: { type: 'string', description: 'Only seed vocab from this theme. Omit to seed everything.' },
      },
    },
  },
];

const handlers = {
  add_note: (i) => addNote(i),
  list_notes: async (i) => listNotes(i),
  add_flashcard: (i) => addFlashcard(i),
  add_vocab: (i) => addVocab(i),
  due_flashcards: async (i) => dueFlashcards(i),
  review_flashcard: (i) => reviewFlashcard(i),
  log_study: (i) => logStudy(i),
  study_stats: async () => studyStats(),
  cpa_status: async () => cpaStatus(),
  set_cpa_progress: (i) => setCpaProgress(i),
  russian_vocab: (i) => russianVocab(i),
  russian_lessons: (i) => russianLessons(i),
  russian_grammar: (i) => russianLesson(i),
  seed_russian: (i) => seedRussianVocab(i),
};

module.exports = {
  name: 'study',
  systemPromptFragment:
    'You are also a study tutor. You actively help the user continue their RUSSIAN language education — teach and quiz vocabulary and grammar, converse in simple Russian when useful, and save new words with add_vocab so they enter spaced-repetition review. ' +
    'ARIA ships with a complete built-in Russian curriculum: use russian_vocab (themed vocabulary corpus, 300+ entries) and russian_grammar / russian_lessons (17 grammar lessons from the Cyrillic alphabet through verb aspect and case system) to teach real content without waiting for the user to supply material. ' +
    'When teaching Russian: pull vocab with russian_vocab (filter by theme), explain grammar with russian_grammar (use the lesson id), and use seed_russian to bulk-load cards into spaced repetition when the user wants to drill a topic. ' +
    'You track BECKER CPA exam prep (sections AUD, FAR, REG, BAR, ISC, TCP) via cpa_status/set_cpa_progress — note that Becker has no public API, so progress is tracked manually here; point the user to becker.com to study the actual lessons. ' +
    'When the user shares material or asks for a SYNOPSIS of what they\'re learning, call list_notes (and/or use what they pasted) and write a concise, well-structured summary with the key points, then offer to turn it into flashcards. Use spaced repetition: quiz due_flashcards and grade with review_flashcard.',
  tools,
  handlers,
  api: {
    addNote, listNotes, deleteNote,
    addFlashcard, addVocab, dueFlashcards, reviewFlashcard, deleteFlashcard, cardCounts,
    logStudy, studyStats,
    cpaStatus, setCpaProgress, cpaSections: CPA_SECTIONS,
    russianThemes, russianVocab, russianLessons, russianLesson, seedRussianVocab,
  },
};
