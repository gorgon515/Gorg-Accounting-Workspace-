'use strict';

// Productivity skill — tasks, quick notes, and a daily briefing that pulls
// together tasks + market + portfolio into one spoken-friendly summary.
//
// The briefing is the "feels like an assistant" centerpiece: it reuses the
// stocks and trading skills' data APIs rather than duplicating logic.
//
// Email triage (Gmail) is intentionally NOT here yet: doing it inside the
// desktop app requires its own OAuth flow + stored credentials, which is a
// separate setup. `briefing` exposes an `inbox` section that stays empty until
// an email provider is wired in — the seam is ready, the integration isn't.

const store = require('../store');
const stocks = require('./stocks');
const trading = require('./trading');

function tasks() {
  return store.get('tasks', []);
}
function saveTasks(t) {
  return store.set('tasks', t);
}
function notes() {
  return store.get('notes', []);
}
function saveNotes(n) {
  return store.set('notes', n);
}

function newId(prefix) {
  return prefix + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

// Lenient date parse: accepts ISO (YYYY-MM-DD), "today", "tomorrow", or blank.
function parseDue(due) {
  if (!due) return null;
  const s = String(due).trim().toLowerCase();
  const d = new Date();
  if (s === 'today') return d.toISOString().slice(0, 10);
  if (s === 'tomorrow') {
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  }
  const parsed = new Date(s);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
}

function addTask({ text, due }) {
  if (!text || !String(text).trim()) throw new Error('Task text is required.');
  const list = tasks();
  const task = {
    id: newId('task'),
    text: String(text).trim(),
    due: parseDue(due),
    done: false,
    createdAt: new Date().toISOString(),
  };
  list.push(task);
  saveTasks(list);
  return task;
}

// Match by id, or fall back to a case-insensitive substring of the text.
function findTask(list, idOrText) {
  const key = String(idOrText || '').trim().toLowerCase();
  return (
    list.find((t) => t.id === idOrText) ||
    list.find((t) => !t.done && t.text.toLowerCase().includes(key)) ||
    null
  );
}

function completeTask({ id, text }) {
  const list = tasks();
  const t = findTask(list, id || text);
  if (!t) throw new Error('No matching task found.');
  t.done = true;
  t.completedAt = new Date().toISOString();
  saveTasks(list);
  return t;
}

function deleteTask({ id, text }) {
  const list = tasks();
  const t = findTask(list, id || text);
  if (!t) throw new Error('No matching task found.');
  saveTasks(list.filter((x) => x.id !== t.id));
  return { deleted: t.id };
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function listTasks({ filter } = {}) {
  const all = tasks();
  const today = todayStr();
  if (filter === 'all') return all;
  if (filter === 'today') return all.filter((t) => !t.done && t.due === today);
  if (filter === 'overdue') return all.filter((t) => !t.done && t.due && t.due < today);
  return all.filter((t) => !t.done); // default: open
}

function addNote({ text }) {
  if (!text || !String(text).trim()) throw new Error('Note text is required.');
  const list = notes();
  const note = { id: newId('note'), text: String(text).trim(), createdAt: new Date().toISOString() };
  list.unshift(note);
  if (list.length > 200) list.length = 200;
  saveNotes(list);
  return note;
}
function listNotes() {
  return notes();
}
function deleteNote({ id }) {
  saveNotes(notes().filter((n) => n.id !== id));
  return { deleted: id };
}

// The daily briefing: tasks + market movers + portfolio, in one object.
async function briefing() {
  const today = todayStr();
  const all = tasks();
  const open = all.filter((t) => !t.done);
  const overdue = open.filter((t) => t.due && t.due < today);
  const dueToday = open.filter((t) => t.due === today);

  // Market: biggest movers among the watchlist.
  let movers = [];
  try {
    const quotes = await stocks.api.getQuotes(stocks.api.getWatchlist());
    movers = quotes
      .filter((q) => !q.error && q.changePercent != null)
      .sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent))
      .slice(0, 3)
      .map((q) => ({ symbol: q.symbol, price: q.price, changePercent: q.changePercent }));
  } catch {
    /* market feed may be unreachable; briefing still works without it */
  }

  let portfolio = null;
  try {
    const p = await trading.api.getPortfolio();
    portfolio = { totalValue: p.totalValue, cash: p.cash, positionCount: p.positions.length };
  } catch {
    /* non-fatal */
  }

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  return {
    date: today,
    greeting,
    tasks: {
      openCount: open.length,
      overdue: overdue.map((t) => t.text),
      dueToday: dueToday.map((t) => t.text),
    },
    market: { movers },
    portfolio,
    inbox: { unread: 0, items: [], note: 'Email triage not yet connected.' },
  };
}

const tools = [
  {
    name: 'add_task',
    description: 'Add a to-do item. Optionally include a due date ("today", "tomorrow", or YYYY-MM-DD). Call when the user wants to remember or schedule something.',
    input_schema: {
      type: 'object',
      properties: {
        text: { type: 'string', description: 'What needs to be done' },
        due: { type: 'string', description: 'Optional due date: today | tomorrow | YYYY-MM-DD' },
      },
      required: ['text'],
    },
  },
  {
    name: 'list_tasks',
    description: 'List the user\'s tasks. filter: "open" (default), "today", "overdue", or "all".',
    input_schema: {
      type: 'object',
      properties: { filter: { type: 'string', enum: ['open', 'today', 'overdue', 'all'] } },
    },
  },
  {
    name: 'complete_task',
    description: 'Mark a task done. Identify it by id or by a snippet of its text.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, text: { type: 'string' } },
    },
  },
  {
    name: 'delete_task',
    description: 'Delete a task by id or text snippet.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, text: { type: 'string' } },
    },
  },
  {
    name: 'add_note',
    description: 'Save a quick note or thought for later.',
    input_schema: {
      type: 'object',
      properties: { text: { type: 'string' } },
      required: ['text'],
    },
  },
  {
    name: 'list_notes',
    description: 'List saved notes, newest first.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'daily_briefing',
    description: 'Get a consolidated daily briefing: open/overdue/today tasks, top watchlist movers, and portfolio snapshot. Call when the user asks for their briefing, their day, "what\'s up", or a morning summary. Read the result back as a short spoken-style summary.',
    input_schema: { type: 'object', properties: {} },
  },
];

const handlers = {
  add_task: (i) => addTask(i),
  list_tasks: async (i) => listTasks(i),
  complete_task: (i) => completeTask(i),
  delete_task: (i) => deleteTask(i),
  add_note: (i) => addNote(i),
  list_notes: async () => listNotes(),
  daily_briefing: () => briefing(),
};

module.exports = {
  name: 'productivity',
  systemPromptFragment:
    'You manage the user\'s tasks and quick notes, and can produce a daily briefing that combines their tasks, watchlist movers, and portfolio. ' +
    'When giving the briefing aloud, lead with the greeting and date, then the most urgent tasks (overdue first), then a one-line market note, then portfolio value. Keep it under ~60 words unless asked for detail. ' +
    'Email/inbox triage is not connected yet — if asked about email, say it\'s coming and offer to note a reminder instead.',
  tools,
  handlers,
  api: {
    addTask, listTasks, completeTask, deleteTask,
    addNote, listNotes, deleteNote, briefing,
  },
};
