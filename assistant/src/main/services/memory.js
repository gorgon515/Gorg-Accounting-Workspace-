'use strict';

// Cross-session memory — the upgrade that makes ARIA smarter in every area.
// Facts the user shares (or asks ARIA to remember) persist locally and are
// injected into the system prompt of every future conversation, so context
// carries across restarts: trading preferences, study goals, names, routines.
//
// Fully local (persisted JSON via store). Capped to keep the prompt lean.

const store = require('../store');

const MAX_MEMORIES = 60;

const memories = () => store.get('memories', []);
const save = (m) => store.set('memories', m);
const newId = () => 'mem_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);

function remember({ fact, category }) {
  if (!fact || !String(fact).trim()) throw new Error('fact is required');
  const m = {
    id: newId(),
    fact: String(fact).trim(),
    category: (category && String(category).trim().toLowerCase()) || 'general',
    createdAt: new Date().toISOString(),
  };
  const list = memories();
  // de-dupe near-identical facts
  if (list.some((x) => x.fact.toLowerCase() === m.fact.toLowerCase())) {
    return { saved: false, note: 'Already remembered.' };
  }
  list.push(m);
  while (list.length > MAX_MEMORIES) list.shift(); // oldest out
  save(list);
  return { saved: true, memory: m };
}

function recall({ query } = {}) {
  let list = memories();
  if (query) {
    const q = String(query).toLowerCase();
    list = list.filter((m) => m.fact.toLowerCase().includes(q) || m.category.includes(q));
  }
  return list;
}

function forget({ id, query }) {
  const list = memories();
  let target = id ? list.find((m) => m.id === id) : null;
  if (!target && query) {
    const q = String(query).toLowerCase();
    target = list.find((m) => m.fact.toLowerCase().includes(q));
  }
  if (!target) throw new Error('No matching memory found.');
  save(list.filter((m) => m.id !== target.id));
  return { forgot: target.fact };
}

// Injected into the system prompt by the skill registry on every brain call.
function promptBlock() {
  const list = memories();
  if (!list.length) return '';
  return (
    '\nKnown facts about the user (from earlier sessions — use them naturally, do not recite them):\n' +
    list.map((m) => `- ${m.fact}`).join('\n')
  );
}

const tools = [
  {
    name: 'remember',
    description:
      'Save a lasting fact about the user or their preferences (e.g. "prefers defined-risk spreads", "studying for FAR exam in August", "company is Verum Advisory"). Call whenever the user shares something worth carrying into future sessions, or asks you to remember something.',
    input_schema: {
      type: 'object',
      properties: {
        fact: { type: 'string', description: 'One concise sentence' },
        category: { type: 'string', description: 'e.g. trading, study, personal, accounting' },
      },
      required: ['fact'],
    },
  },
  {
    name: 'recall_memories',
    description: 'List saved memories, optionally filtered by a search term. Use when asked "what do you know about me" or to check stored preferences.',
    input_schema: {
      type: 'object',
      properties: { query: { type: 'string' } },
    },
  },
  {
    name: 'forget',
    description: 'Delete a saved memory by id or matching text. Call when the user asks you to forget something.',
    input_schema: {
      type: 'object',
      properties: { id: { type: 'string' }, query: { type: 'string' } },
    },
  },
];

const handlers = {
  remember: (i) => remember(i),
  recall_memories: async (i) => recall(i),
  forget: (i) => forget(i),
};

module.exports = {
  name: 'memory',
  systemPromptFragment:
    'You have persistent memory: save lasting user facts/preferences with remember, retrieve with recall_memories, delete with forget. Proactively remember important things the user tells you (preferences, goals, recurring context) without being asked, and mention that you will remember them.',
  tools,
  handlers,
  api: { remember, recall, forget, promptBlock },
};
