'use strict';

// Agent orchestration: routing, roster, tool attribution, and activity logging.
// agents.js has no electron dependency, so it loads directly.

const test = require('node:test');
const assert = require('node:assert');
const agents = require('../src/main/services/agents').api;

test('router classifies representative requests', () => {
  const cases = [
    ['analyze NVDA RSI and MACD', 'quant'],
    ['buy 10 shares of AAPL', 'trading'],
    ['teach me 5 Spanish words', 'language_coach'],
    ['summarize my unread email', 'email'],
    ['schedule a meeting tomorrow at 3pm', 'calendar'],
    ['remember I prefer defined-risk spreads', 'knowledge'],
    ['build a workflow that files invoices', 'automation'],
    ['add an expense to the ledger', 'accounting'],
    ['what new FASB updates affect leases', 'fasb'],
    ['summarize the latest 10-K filing', 'sec'],
    ['help me study for the FAR exam', 'cpa_coach'],
    ['analyze my portfolio concentration and sector exposure', 'portfolio'],
    ['plan my day', 'chief_of_staff'],
    ['asdfqwer zzz', 'chief_of_staff'],
  ];
  for (const [text, expected] of cases) {
    assert.equal(agents.route(text).agent, expected, `"${text}" should route to ${expected}`);
  }
});

test('route returns a numeric score and confidence', () => {
  const r = agents.route('analyze NVDA RSI MACD volatility');
  assert.equal(typeof r.score, 'number');
  assert.ok(['low', 'medium', 'high'].includes(r.confidence));
});

test('roster exposes permissions and status', () => {
  const roster = agents.roster([
    { name: 'accounting', tools: [1, 2, 3] },
    { name: 'sidecar', tools: [1, 2, 3, 4, 5, 6] },
  ]);
  assert.ok(roster.length >= 12);
  const acct = roster.find((a) => a.key === 'accounting');
  assert.ok(acct.permissions);
  assert.equal(acct.permissions.canPropose, true);
  const auto = roster.find((a) => a.key === 'automation');
  assert.equal(auto.status, 'planned');
});

test('tool attribution maps shared-skill tools to the right agent', () => {
  assert.equal(agents.agentForTool('quant_analyze', 'sidecar').key, 'quant');
  assert.equal(agents.agentForTool('accounting_memo', 'sidecar').key, 'fasb');
  assert.equal(agents.agentForTool('set_target_language', 'language').key, 'language_coach');
});

test('activity log records and returns recent calls', () => {
  agents.logActivity({ agent: 'quant', tool: 'quant_analyze', ok: true });
  agents.logActivity({ agent: 'fasb', tool: 'explain_asc', ok: true });
  const recent = agents.recentActivity(5);
  assert.equal(recent[0].tool, 'explain_asc');
  assert.equal(recent[0].name, 'FASB Agent');
});

test('promptBlock lists the team and the no-execute rule', () => {
  const block = agents.promptBlock();
  assert.match(block, /Chief of Staff/);
  assert.match(block, /proposed/);
});
