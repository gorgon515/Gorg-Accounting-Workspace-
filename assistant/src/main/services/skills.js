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

const skills = [stocks, trading, productivity, alerts, google];

function allTools() {
  return skills.flatMap((s) => s.tools || []);
}

function handlerFor(toolName) {
  for (const s of skills) {
    if (s.handlers && toolName in s.handlers) return s.handlers[toolName];
  }
  return null;
}

function systemPrompt() {
  const fragments = skills
    .filter((s) => s.systemPromptFragment)
    .map((s) => `- ${s.name}: ${s.systemPromptFragment}`)
    .join('\n');
  return [
    'You are ARIA, an integrated desktop assistant. You are concise, calm, and practical.',
    'You help with stocks, accounting, studying, and general productivity. Right now the Stocks capability is live; the others are coming.',
    'When you call a tool, do not narrate routine steps — just answer with the result.',
    'Your replies may be read aloud by a text-to-speech voice, so keep them tight and free of markdown tables or long lists unless explicitly asked.',
    '',
    'Capabilities:',
    fragments,
    config.persona ? '\nOperator persona/instructions:\n' + config.persona : '',
  ].join('\n');
}

function getSkill(name) {
  return skills.find((s) => s.name === name) || null;
}

module.exports = { skills, allTools, handlerFor, systemPrompt, getSkill };
