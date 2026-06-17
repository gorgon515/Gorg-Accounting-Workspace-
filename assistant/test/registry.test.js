'use strict';

// Registry integrity: no broken wiring, no duplicate tools, no missing pieces.
// store.js requires 'electron'; stub it so the registry loads under plain Node.

const test = require('node:test');
const assert = require('node:assert');
const os = require('os');
const path = require('path');
const fs = require('fs');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'helios-test-'));
const electronStub = {
  app: { getPath: () => tmp },
  safeStorage: { isEncryptionAvailable: () => false },
};
const Module = require('module');
const origLoad = Module._load;
Module._load = function (request, ...rest) {
  if (request === 'electron') return electronStub;
  return origLoad.call(this, request, ...rest);
};

const skills = require('../src/main/services/skills');

test('all expected skills are registered', () => {
  const names = skills.skills.map((s) => s.name);
  for (const expected of ['stocks', 'trading', 'accounting', 'study', 'memory',
    'language', 'sidecar', 'agents']) {
    assert.ok(names.includes(expected), `missing skill: ${expected}`);
  }
  assert.equal(skills.skills.length, 13);
});

test('no duplicate tool names across the registry', () => {
  const names = skills.allTools().map((t) => t.name);
  const seen = new Set();
  const dupes = [];
  for (const n of names) {
    if (seen.has(n)) dupes.push(n);
    seen.add(n);
  }
  assert.deepEqual(dupes, [], `duplicate tools: ${dupes.join(', ')}`);
});

test('every tool has a handler (no broken wiring)', () => {
  for (const t of skills.allTools()) {
    assert.equal(typeof skills.handlerFor(t.name), 'function', `no handler for ${t.name}`);
  }
});

test('Phase-2 tools are present', () => {
  const names = skills.allTools().map((t) => t.name);
  for (const t of ['daily_missions', 'which_agent', 'quant_analyze', 'quant_risk',
    'explain_asc', 'accounting_memo', 'add_quick_note']) {
    assert.ok(names.includes(t), `missing tool: ${t}`);
  }
});

test('system prompt frames HELIOS as an agent team', () => {
  const sp = skills.systemPrompt();
  assert.match(sp, /HELIOS/);
  assert.match(sp, /Chief of Staff/);
});

test.after(() => fs.rmSync(tmp, { recursive: true, force: true }));
