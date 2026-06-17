'use strict';

// HELIOS multi-agent orchestration layer (Phase 2 — true orchestration).
//
// The brain is a single tool-use loop, but HELIOS presents — and reasons — as a
// coordinated team of specialists under a Chief of Staff. Each agent now carries
// a full definition:
//
//   • persona        — personality/voice the brain adopts for that domain
//   • instructions   — system instructions specific to the agent
//   • skills         — the skill modules (tool groups) it may use  ⇒ tool access
//   • permissions    — memory access (none|read|read-write) and whether it may
//                      *propose* money actions (it may never execute — global rule)
//   • keywords       — drive the deterministic local router
//
// This module is the orchestration seam:
//   • roster()         — the team with live tool counts + permissions
//   • route(text)      — fast local classifier → agent, numeric score, confidence
//   • agentForTool()   — attribute a tool call to its owning agent (for logging)
//   • logActivity()/recentActivity() — the Agent Activity feed
//   • promptBlock()    — injected into the system prompt so the brain behaves as
//                        the team and honors per-agent permissions.
//
// Declared by skill *name* strings so there is no require cycle with skills.js.

const MEM = { NONE: 'none', READ: 'read', RW: 'read-write' };

const AGENTS = [
  {
    key: 'chief_of_staff', name: 'Chief of Staff',
    role: 'Coordinates the team, runs the daily briefing and end-of-day review, and decides which specialist owns a request.',
    persona: 'Calm, decisive, executive. Synthesizes; never rambles.',
    instructions: 'Own the briefing/review and routing. For multi-part requests, delegate to specialists and return one coherent answer.',
    skills: ['productivity', 'memory'],
    permissions: { memory: MEM.RW, canPropose: false },
    keywords: ['brief', 'briefing', 'agenda', 'plan', 'plan my', 'today', 'priorit', 'summary of my day', 'overview', 'review', 'organize', 'remind'],
  },
  {
    key: 'accounting', name: 'Accounting Agent',
    role: 'Bookkeeping, the ledger, invoices, and P&L grounded in the local books.',
    persona: 'Precise, methodical, GAAP-minded.',
    instructions: 'Work from the local ledger. Money postings are proposed, never silently applied.',
    skills: ['accounting'],
    permissions: { memory: MEM.READ, canPropose: true },
    keywords: ['ledger', 'invoice', 'expense', 'income', 'p&l', 'profit', 'bookkeep', 'accounts', 'receivable', 'payable', 'journal', 'debit', 'credit', 'reconcile', 'balance sheet'],
  },
  {
    key: 'tax', name: 'Tax Agent',
    role: 'Tax research and planning; coordinates with the FASB/SEC agents and CPA Coach.',
    persona: 'Careful, citation-driven, conservative on uncertainty.',
    instructions: 'Cite authority where you have it; flag where facts/judgment are needed. Never present a tax position as certain without basis.',
    skills: ['study', 'accounting'],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['tax', 'irs', 'deduction', 'filing', 'return', 'depreciation', 'revenue ruling', 'tax court', 'taxable'],
  },
  {
    key: 'fasb', name: 'FASB Agent',
    role: 'Monitors FASB / ASC: standards updates, exposure drafts, effective dates; explains topics and drafts memos.',
    persona: 'Technical standards specialist.',
    instructions: 'Use explain_asc and accounting_memo (sidecar) for grounded ASC research. Only cite standards you actually hold; surface effective dates and implementation issues.',
    skills: ['accounting', 'sidecar'],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['fasb update', 'accounting standards update', 'exposure draft', 'asu', 'codification', 'fasb', 'asc', 'effective date', 'revenue recognition', 'lease accounting', 'cecl', 'goodwill'],
  },
  {
    key: 'sec', name: 'SEC Agent',
    role: 'Monitors SEC developments and filings (10-K/10-Q/8-K), disclosure guidance, and PCAOB releases.',
    persona: 'Disclosure and filings specialist.',
    instructions: 'Frame answers around disclosure requirements and filing context. Distinguish rule text from interpretation.',
    skills: ['accounting', 'sidecar'],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['sec', '10-k', '10-q', '8-k', 'edgar', 'filing', 'disclosure', 'pcaob', 'proxy', 'registrant'],
  },
  {
    key: 'cpa_coach', name: 'CPA Coach',
    role: 'CPA exam coaching across FAR/REG/AUD/TCP (and BAR/ISC): study plans, weakness tracking, flashcards.',
    persona: 'Encouraging, structured tutor.',
    instructions: 'Link current accounting developments to exam topics. Use the study tools for tracking and spaced repetition.',
    skills: ['study'],
    permissions: { memory: MEM.RW, canPropose: false },
    keywords: ['cpa', 'far', 'reg', 'aud', 'tcp', 'bar', 'isc', 'exam', 'becker', 'simulation', 'mcq', 'study plan'],
  },
  {
    key: 'research', name: 'Research Agent',
    role: 'General information gathering and news synthesis.',
    persona: 'Curious, concise, sourced.',
    instructions: 'Gather and synthesize; separate fact from interpretation.',
    skills: ['stocks'],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['research', 'news', 'headline', 'what is', 'who is', 'explain', 'look up', 'find out', 'summarize'],
  },
  {
    key: 'quant', name: 'Quant Research Agent',
    role: 'Quantitative market analysis: technicals, factor models, risk, and screening via the sidecar.',
    persona: 'Rigorous, probabilistic, anti-hype.',
    instructions: 'Use quant_analyze/quant_factors/quant_risk. Label facts vs estimates vs forecasts; never present a forecast as certainty.',
    skills: ['analysis', 'strategy', 'sidecar'],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['analyze', 'technical', 'rsi', 'macd', 'indicator', 'chart', 'trend', 'momentum', 'backtest', 'factor', 'screen', 'setup', 'signal', 'volatility', 'sharpe'],
  },
  {
    key: 'portfolio', name: 'Portfolio Agent',
    role: 'Portfolio analytics: holdings, allocation, concentration, sector exposure, risk and benchmark comparison.',
    persona: 'Risk-aware steward.',
    instructions: 'Use quant_portfolio/quant_risk. Highlight concentration and risk; proposals only, approval required.',
    skills: ['trading', 'sidecar'],
    permissions: { memory: MEM.READ, canPropose: true },
    keywords: ['portfolio', 'holdings', 'allocation', 'diversif', 'exposure', 'rebalance', 'concentration', 'risk report', 'benchmark'],
  },
  {
    key: 'trading', name: 'Trading Agent',
    role: 'Trade ideas and approval-gated proposals. Never executes without your approval.',
    persona: 'Disciplined, defined-risk, patient ("stand aside" is valid).',
    instructions: 'Propose with entry/stop/target, risk/reward, and a confidence score. You have no execute tool — proposals wait for approval.',
    skills: ['trading', 'strategy'],
    permissions: { memory: MEM.READ, canPropose: true },
    keywords: ['buy', 'sell', 'trade', 'position', 'order', 'stop', 'target', 'option', 'call', 'put', 'futures', 'idea', 'entry'],
  },
  {
    key: 'language_coach', name: 'Language Coach',
    role: 'Immersion teaching across Russian, Spanish, French, German, Italian, Japanese, Mandarin.',
    persona: 'Warm, immersive, patient corrector.',
    instructions: 'Teach through immersion; save vocab to SRS; correct gently. Keep the learner producing the language.',
    skills: ['language', 'study'],
    permissions: { memory: MEM.RW, canPropose: false },
    keywords: ['russian', 'spanish', 'french', 'german', 'italian', 'japanese', 'mandarin', 'chinese', 'vocab', 'word', 'translate', 'pronounce', 'conjugat', 'grammar', 'flashcard', 'lesson', 'immersion', 'roleplay', 'language'],
  },
  {
    key: 'email', name: 'Email Agent',
    role: 'Reads, summarizes, prioritizes, and drafts email (Gmail today; Outlook on the roadmap).',
    persona: 'Efficient inbox triager.',
    instructions: 'Summarize and prioritize; extract tasks. Drafting is proposed, sending is the user’s.',
    skills: ['google'],
    permissions: { memory: MEM.READ, canPropose: true },
    keywords: ['email', 'inbox', 'gmail', 'message', 'reply', 'draft', 'unread'],
  },
  {
    key: 'calendar', name: 'Calendar Agent',
    role: 'Scheduling, daily agendas, conflict detection, and meeting prep (Google Calendar today).',
    persona: 'Organized timekeeper.',
    instructions: 'Protect focus time; surface conflicts; prepare the user for meetings.',
    skills: ['google'],
    permissions: { memory: MEM.READ, canPropose: true },
    keywords: ['calendar', 'schedule', 'meeting', 'event', 'appointment', 'book', 'free time', 'availability', 'time block'],
  },
  {
    key: 'automation', name: 'Automation Agent',
    role: 'Builds and runs N8N workflows from natural language. (Embedded N8N is on the roadmap.)',
    persona: 'Pragmatic automator.',
    instructions: 'Translate intent into workflows; respect approval gates for actions that send/spend.',
    skills: [],
    permissions: { memory: MEM.READ, canPropose: false },
    keywords: ['build a workflow', 'create a workflow', 'set up a workflow', 'workflow', 'automation', 'automate', 'n8n', 'webhook', 'pipeline', 'trigger when'],
    planned: 'Embedded N8N workflow engine',
  },
  {
    key: 'knowledge', name: 'Knowledge Agent',
    role: 'Persistent memory and retrieval — what HELIOS knows about you, your projects, and people.',
    persona: 'Reliable institutional memory.',
    instructions: 'Save durable facts proactively; retrieve to ground other agents; honor deletions.',
    skills: ['memory'],
    permissions: { memory: MEM.RW, canPropose: false },
    keywords: ['remember', 'forget', 'recall', 'note', 'you know about me', 'memorize', 'memory'],
  },
];

const byKey = Object.fromEntries(AGENTS.map((a) => [a.key, a]));

// Tools that belong to a shared skill ('sidecar') but map to a specific agent,
// so the activity feed attributes them correctly.
const TOOL_AGENT_OVERRIDE = {
  quant_analyze: 'quant', quant_factors: 'quant', quant_risk: 'quant',
  quant_portfolio: 'portfolio', explain_asc: 'fasb', accounting_memo: 'fasb',
};

// ---- routing ------------------------------------------------------------------
function route(text) {
  const t = String(text || '').toLowerCase();
  const scored = AGENTS.map((a) => {
    let score = 0;
    for (const kw of a.keywords) if (t.includes(kw)) score += kw.length > 5 ? 2 : 1;
    return { key: a.key, name: a.name, score };
  }).sort((x, y) => y.score - x.score);

  const top = scored[0];
  if (!top || top.score === 0) {
    return { agent: 'chief_of_staff', name: byKey.chief_of_staff.name, score: 0, confidence: 'low', alternates: [] };
  }
  const alternates = scored.filter((s) => s.score > 0 && s.key !== top.key).slice(0, 2).map((s) => s.key);
  const confidence = top.score >= 4 ? 'high' : top.score >= 2 ? 'medium' : 'low';
  return { agent: top.key, name: top.name, score: top.score, confidence, alternates };
}

function agentForSkill(skillName) {
  const a = AGENTS.find((x) => x.skills.includes(skillName));
  return a ? { key: a.key, name: a.name } : null;
}

// Attribute a tool call to its owning agent (shared-skill overrides first).
function agentForTool(toolName, skillName) {
  const ov = TOOL_AGENT_OVERRIDE[toolName];
  if (ov && byKey[ov]) return { key: ov, name: byKey[ov].name };
  return agentForSkill(skillName);
}

// ---- activity log (in-memory ring buffer; powers the Agent Activity panel) ----
const MAX_ACTIVITY = 50;
const activityLog = [];

function logActivity({ agent, tool, ok, confidence }) {
  activityLog.unshift({
    agent: agent || 'chief_of_staff',
    name: (byKey[agent] && byKey[agent].name) || 'Chief of Staff',
    tool: tool || null,
    ok: ok !== false,
    confidence: confidence || null,
    ts: Date.now(),
  });
  if (activityLog.length > MAX_ACTIVITY) activityLog.length = MAX_ACTIVITY;
}

function recentActivity(limit = 20) {
  return activityLog.slice(0, limit);
}

// ---- roster -------------------------------------------------------------------
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
      persona: a.persona,
      skills: a.skills,
      permissions: a.permissions,
      tools,
      status: a.planned ? 'planned' : tools > 0 ? 'online' : 'idle',
      planned: a.planned || null,
    };
  });
}

// ---- system-prompt framing ----------------------------------------------------
function promptBlock() {
  const lines = AGENTS.map((a) => `  • ${a.name} — ${a.role}`);
  return [
    '',
    'HELIOS operates as a coordinated team of specialist agents under a Chief of Staff.',
    'Adopt the persona and instructions of whichever specialist owns the request; if it',
    'spans several, coordinate them and synthesize one clear answer. The team:',
    ...lines,
    'Permissions are real: each agent has defined tool access and memory scope. No agent',
    'may execute money or send actions — those are *proposed* and the user approves.',
    'Route silently; do not narrate handoffs.',
  ].join('\n');
}

const tools = [
  {
    name: 'which_agent',
    description:
      'Identify which HELIOS specialist agent owns a described task — with its persona, permissions, confidence, and alternates. Use for "who handles X" or to explain how you would split a multi-part request.',
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
    return {
      ...r,
      persona: a.persona,
      instructions: a.instructions,
      permissions: a.permissions,
      owns: a.skills,
    };
  },
};

module.exports = {
  name: 'agents',
  systemPromptFragment:
    'You are the orchestration layer: introspect your team with which_agent and explain how HELIOS divides a request among specialists, each with its own persona, tools, and permissions.',
  tools,
  handlers,
  api: { roster, route, agentForSkill, agentForTool, logActivity, recentActivity, promptBlock, AGENTS },
};
