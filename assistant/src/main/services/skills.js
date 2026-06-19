'use strict';

// Skill registry. Each skill module exports { name, systemPromptFragment,
// tools, handlers, api }. To add Accounting / Study / Productivity later,
// create a sibling module and register it here — nothing else changes.

const config = require('../config');
const stocks = require('./stocks');
const trading = require('./trading');
const productivity = require('./productivity');
const alerts = require('./alerts');
const google = require('./google');
const analysis = require('./analysis');
const accounting = require('./accounting');
const study = require('./study');
const strategy = require('./strategy');
const memory = require('./memory');
const language = require('./language');
const agents = require('./agents');
const sidecar = require('./sidecar');

const skills = [stocks, trading, productivity, alerts, google, analysis, accounting, study, strategy, memory, language, sidecar, agents];

function allTools() {
  return skills.flatMap((s) => s.tools || []);
}

function handlerFor(toolName) {
  for (const s of skills) {
    if (s.handlers && toolName in s.handlers) return s.handlers[toolName];
  }
  return null;
}

// The skill module that owns a tool (first match) — used to attribute tool calls
// to an agent for the activity log.
function skillForTool(toolName) {
  for (const s of skills) {
    if (s.handlers && toolName in s.handlers) return s;
  }
  return null;
}

function systemPrompt() {
  const fragments = skills
    .filter((s) => s.systemPromptFragment)
    .map((s) => `- ${s.name}: ${s.systemPromptFragment}`)
    .join('\n');
  return [
    'You are ARIA, the assistant runtime of HELIOS — a local-first personal intelligence platform. You are concise, calm, and practical.',
    'You help with stocks and trading, accounting, language immersion, studying, and general productivity, operating as a coordinated team of specialist agents.',
    'When you call a tool, do not narrate routine steps — just answer with the result.',
    'Your replies may be read aloud by a text-to-speech voice, so keep them tight and free of markdown tables or long lists unless explicitly asked.',
    '',
    'Capabilities:',
    fragments,
    agents.api.promptBlock(),
    config.persona ? '\nOperator persona/instructions:\n' + config.persona : '',
    memory.api.promptBlock(),
  ].join('\n');
}

function getSkill(name) {
  return skills.find((s) => s.name === name) || null;
}

module.exports = { skills, allTools, handlerFor, skillForTool, systemPrompt, getSkill };
