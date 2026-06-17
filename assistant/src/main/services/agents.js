'use strict';

// HELIOS multi-agent orchestration layer.
//
// The brain is a single tool-use loop, but HELIOS presents — and reasons — as a
// coordinated team of specialist agents (a "Chief of Staff" coordinating
// domain experts). This module is the orchestration seam:
//
//   • roster()      — the agent team, each mapped to the skills/tools it owns.
//   • route(text)   — a fast, fully-local heuristic classifier that picks the
//                     agent(s) most likely to own a request (no model needed).
//                     Used by the Agent Activity panel and for logging which
//                     specialist handled a turn.
//   • promptBlock() — injected into the system prompt so the single brain
//                     operates *as* the team: it knows its specialists, defers
//                     to the right one, and routes through the Chief of Staff.
//
// It is also a normal skill module ({ name, systemPromptFragment, tools,
// handlers, api }) so the brain can introspect its own team via `which_agent`.
//
// Design note: agents are defined declaratively by the *names* of the skills
// they own (string keys), so this module has no static dependency on the skill
// registry — avoiding a require cycle (skills.js requires agents.js). Live tool
// counts are computed by passing the registered skills into roster().

// The HELIOS agent team. `skills` lists the skill-module names each agent owns;
// `keywords` drives the local router. `planned` marks capabilities whose
// backing skill is on the roadmap (e.g. N8N automation, a dedicated tax engine).
const AGENTS = [
  {
    key: 'chief_of_staff',
    name: 'Chief of Staff',
    role: 'Coordinates the team, runs the daily briefing and end-of-day review, and decides which specialist owns a request.',
    skills: ['productivity', 'memory'],
    keywords: ['brief', 'briefing', 'agenda', 'plan', 'plan my', 'today', 'priorit', 'summary of my day', 'overview', 'review', 'organize', 'remind'],
  },
  {
    key: 'accounting',
    name: 'Accounting Agent',
    role: 'Bookkeeping, the ledger, invoices, and P&L. Accounting guidance grounded in the local books.',
    skills: ['accounting'],
    keywords: ['ledger', 'invoice', 'expense', 'income', 'p&l', 'profit', 'bookkeep', 'accounts', 'receivable', 'payable', 'journal', 'debit', 'credit', 'reconcile', 'balance sheet'],
  },
  {
    key: 'tax',
    name: 'Tax Agent',
    role: 'Tax research, planning, and CPA exam prep. (Dedicated tax-research engine is on the roadmap; today it leans on study + accounting context.)',
    skills: ['study', 'accounting'],
    keywords: ['tax', 'irs', 'deduction', 'cpa', 'far', 'reg', 'aud', 'tcp', 'bar', 'isc', 'filing', 'return', 'depreciation', 'asc', 'fasb'],
    planned: 'Dedicated ASC/IRS research + memo engine',
  },
  {
    key: 'research',
    name: 'Research Agent',
    role: 'General information gathering and news synthesis.',
    skills: ['stocks'],
    keywords: ['research', 'news', 'headline', 'what is', 'who is', 'explain', 'look up', 'find out', 'summarize'],
  },
  {
    key: 'quant',
    name: 'Quant Agent',
    role: 'Quantitative market analysis: technicals, indicators, and setup scoring.',
    skills: ['analysis', 'strategy'],
    keywords: ['analyze', 'technical', 'rsi', 'macd', 'indicator', 'chart', 'trend', 'momentum', 'backtest', 'factor', 'screen', 'setup', 'signal'],
  },
  {
    key: 'trading',
    name: 'Trading Agent',
    role: 'Position management and approval-gated trade proposals. Never executes without your approval.',
    skills: ['trading', 'strategy'],
    keywords: ['buy', 'sell', 'trade', 'position', 'portfolio', 'order', 'stop', 'target', 'option', 'call', 'put', 'futures', 'idea', 'entry'],
  },
  {
    key: 'language_coach',
    name: 'Language Coach',
    role: 'Immersion teaching across Russian, Spanish, French, German, Italian, Japanese, and Mandarin — vocab, missions, conversation, and the CEFR pathway.',
    skills: ['language', 'study'],
    keywords: ['russian', 'spanish', 'french', 'german', 'italian', 'japanese', 'mandarin', 'chinese', 'vocab', 'word', 'translate', 'pronounce', 'conjugat', 'grammar', 'flashcard', 'lesson', 'immersion', 'roleplay', 'language'],
  },
  {
    key: 'email',
    name: 'Email Agent',
    role: 'Reads, summarizes, prioritizes, and drafts email (Gmail today; Outlook on the roadmap).',
    skills: ['google'],
    keywords: ['email', 'inbox', 'gmail', 'message', 'reply', 'draft', 'unread'],
  },
  {
    key: 'calendar',
    name: 'Calendar Agent',
    role: 'Scheduling, daily agendas, conflict detection, and meeting prep (Google Calendar today).',
    skills: ['google'],
    keywords: ['calendar', 'schedule', 'meeting', 'event', 'appointment', 'book', 'free time', 'availability'],
  },
  {
    key: 'automation',
    name: 'Automation Agent',
    role: 'Builds and runs N8N workflows from natural language. (Embedded N8N is on the roadmap.)',
    skills: [],
    keywords: ['build a workflow', 'create a workflow', 'set up a workflow', 'workflow', 'automation', 'automate', 'n8n', 'webhook', 'pipeline', 'trigger when'],
    planned: 'Embedded N8N workflow engine',
  },
  {
    key: 'knowledge',
    name: 'Knowledge Agent',
    role: 'Persistent memory and retrieval — what HELIOS knows about you, your projects, and people.',
    skills: ['memory'],
    keywords: ['remember', 'forget', 'recall', 'note', 'you know about me', 'memorize', 'memory'],
  },
];

const byKey = Object.fromEntries(AGENTS.map((a) => [a.key, a]));

// Local heuristic router: score each agent by keyword hits in the request and
// return the best match (plus runners-up). Deterministic, no network/model.
function route(text) {
  const t = String(text || '').toLowerCase();
  const scored = AGENTS.map((a) => {
    let score = 0;
    for (const kw of a.keywords) if (t.includes(kw)) score += kw.length > 5 ? 2 : 1;
    return { key: a.key, name: a.name, score };
  }).sort((x, y) => y.score - x.score);

  const top = scored[0];
  // No clear signal → the Chief of Staff fields it and delegates.
  if (!top || top.score === 0) {
    return { agent: 'chief_of_staff', name: byKey.chief_of_staff.name, confidence: 'low', alternates: [] };
  }
  const alternates = scored.filter((s) => s.score > 0 && s.key !== top.key).slice(0, 2).map((s) => s.key);
  const confidence = top.score >= 4 ? 'high' : top.score >= 2 ? 'medium' : 'low';
  return { agent: top.key, name: top.name, confidence, alternates };
}

// Roster with live tool counts. `registeredSkills` is the array from skills.js
// (passed in to avoid a require cycle). Each agent reports how many tools it
// currently owns and whether it is fully wired or still planned.
function roster(registeredSkills = []) {
  const toolCount = (skillName) => {
    const s = registeredSkills.find((x) => x.name === skillName);
    return s && s.tools ? s.tools.length : 0;
  };
  return AGENTS.map((a) => {
    const tools = a.skills.reduce((n, name) => n + toolCount(name), 0);
    return {
      key: a.key,
      name: a.name,
      role: a.role,
      skills: a.skills,
      tools,
      status: a.planned ? 'planned' : tools > 0 ? 'online' : 'idle',
      planned: a.planned || null,
    };
  });
}

// System-prompt block: tells the single brain to behave as the coordinated team.
function promptBlock() {
  const lines = AGENTS.map((a) => `  • ${a.name} — ${a.role}`);
  return [
    '',
    'HELIOS operates as a coordinated team of specialist agents under a Chief of Staff.',
    'Adopt the mindset of whichever specialist owns the request; if it spans several,',
    'coordinate them and synthesize one clear answer. The team:',
    ...lines,
    'You share one memory and one set of tools across the team — route silently; do not',
    'narrate handoffs. For anything involving money (trades, ledger postings) the relevant',
    'agent may only *propose*; the user approves before anything executes.',
  ].join('\n');
}

const tools = [
  {
    name: 'which_agent',
    description:
      'Identify which HELIOS specialist agent owns a described task, with confidence and alternates. Use when the user asks "who handles X", "what can your team do", or to explain how you would approach a multi-part request.',
    input_schema: {
      type: 'object',
      properties: { task: { type: 'string', description: 'A short description of the task to route.' } },
      required: ['task'],
    },
  },
];

const handlers = {
  which_agent: async ({ task }) => {
    const r = route(task);
    const a = byKey[r.agent];
    return { ...r, role: a.role, owns: a.skills };
  },
};

module.exports = {
  name: 'agents',
  systemPromptFragment:
    'You are the orchestration layer: you can introspect your own agent team with which_agent and explain how HELIOS would divide a request among specialists.',
  tools,
  handlers,
  api: { roster, route, promptBlock, AGENTS },
};
