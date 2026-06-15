'use strict';

// The brain: turns natural-language (or voice) commands into actions by
// running a tool-use loop against the skill registry.
//
// Two engines:
//   • 'local'  — Ollama (http://127.0.0.1:11434). Fully on-device, no API key.
//                Install from https://ollama.com and `ollama pull qwen2.5:7b`.
//   • 'claude' — Anthropic API (claude-opus-4-8). Strongest reasoning; needs
//                ANTHROPIC_API_KEY.
// Default: claude if a key is set, otherwise local.
//
// Both run the same manual loop so approval gates and logging stay in one
// place — the brain can only call tools the skills expose; trade execution is
// not one of them.

const Anthropic = require('@anthropic-ai/sdk');
const config = require('./config');
const skills = require('./services/skills');

const MAX_TURNS = 6;

// Real-time web news: Anthropic's server-side web_search tool. Executed on
// Anthropic's side (we never runTool it). ON by default whenever a Claude key
// is present; force off with BRAIN_WEB_SEARCH=false. Read straight from the
// environment so we don't have to touch config.js.
const WEB_SEARCH = process.env.BRAIN_WEB_SEARCH !== 'false';

// Blocks the manual loop must never hand to runTool — they're server-side.
function isServerToolBlock(block) {
  return (
    block.name === 'web_search' ||
    block.type === 'server_tool_use' ||
    block.type === 'web_search_tool_result'
  );
}

// ---------- Claude engine ----------
let client = null;
function getClient() {
  if (!config.anthropicApiKey) return null;
  if (!client) client = new Anthropic({ apiKey: config.anthropicApiKey });
  return client;
}

// Build the tools array sent to Claude: the skill tools plus (optionally) the
// server-side web_search tool. The LAST entry carries cache_control so the tool
// schemas are cached alongside the system prompt — they're stable across turns.
function claudeTools() {
  const tools = skills.allTools().map((t) => ({ ...t }));
  if (WEB_SEARCH && config.anthropicApiKey) {
    tools.push({ type: 'web_search_20250305', name: 'web_search', max_uses: 5 });
  }
  if (tools.length) {
    tools[tools.length - 1] = {
      ...tools[tools.length - 1],
      cache_control: { type: 'ephemeral' },
    };
  }
  return tools;
}

// System prompt as cacheable blocks. Last block carries cache_control so the
// (stable) preamble is cached across turns and requests.
function claudeSystem() {
  return [{ type: 'text', text: skills.systemPrompt(), cache_control: { type: 'ephemeral' } }];
}

async function askClaude(userText, history, toolEvents, onEvent) {
  const anthropic = getClient();
  const messages = [...history, { role: 'user', content: userText }];
  const tools = claudeTools();
  const system = claudeSystem();
  let fullText = '';

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const stream = anthropic.messages.stream({
      model: config.model,
      max_tokens: 4000,
      thinking: { type: 'adaptive' },
      system,
      tools,
      messages,
    });

    // Forward assistant text deltas as they arrive.
    if (onEvent) {
      stream.on('text', (delta) => {
        fullText += delta;
        onEvent({ type: 'delta', text: delta });
      });
    } else {
      // Still accumulate text even when nobody's listening for deltas.
      stream.on('text', (delta) => { fullText += delta; });
    }

    const res = await stream.finalMessage();
    messages.push({ role: 'assistant', content: res.content });

    if (res.stop_reason !== 'tool_use') {
      const text = fullText.trim();
      if (onEvent) onEvent({ type: 'done', text, history: messages, toolEvents });
      return { text, history: messages };
    }

    // Run only the local skill tools. The server-side web_search blocks are
    // already resolved inside the streamed turn, so we skip them here.
    const toolResults = [];
    for (const block of res.content) {
      if (block.type !== 'tool_use') continue;
      if (isServerToolBlock(block)) continue;
      const { result, ok, error } = await runTool(block.name, block.input || {});
      toolEvents.push({ name: block.name, input: block.input, ok, error });
      if (onEvent) onEvent({ type: 'tool_result', name: block.name, ok, error });
      toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: result });
    }

    if (!toolResults.length) {
      // Only server-side tools ran this turn — nothing to feed back; the next
      // turn continues so Claude can synthesize the final answer.
      continue;
    }
    messages.push({ role: 'user', content: toolResults });
  }
  const text = (fullText || "I worked through several steps but didn't reach a final answer. Try narrowing the request.").trim();
  if (onEvent) onEvent({ type: 'done', text, history: messages, toolEvents });
  return { text, history: messages };
}

// ---------- Local engine (Ollama) ----------
let resolvedLocalModel = null; // actual model in use (may differ from config)

function toOllamaTools(tools) {
  return tools.map((t) => ({
    type: 'function',
    function: { name: t.name, description: t.description, parameters: t.input_schema },
  }));
}

async function ollamaChat(messages, tools) {
  const res = await fetch(`${config.ollamaUrl.replace(/\/$/, '')}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: resolvedLocalModel || config.ollamaModel,
      messages,
      tools,
      stream: false,
    }),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw new Error(`Ollama ${res.status}: ${t.slice(0, 200)}`);
  }
  return res.json();
}

async function askLocal(userText, history, toolEvents, onEvent) {
  // history is kept in Ollama's flat {role, content} shape for this engine.
  const messages = [
    { role: 'system', content: skills.systemPrompt() },
    ...history.filter((m) => m.role !== 'system'),
    { role: 'user', content: userText },
  ];
  const tools = toOllamaTools(skills.allTools());

  // Ollama runs non-streaming here, but we still emit a single delta+done so the
  // UI has one code path regardless of engine.
  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const data = await ollamaChat(messages, tools);
    const msg = data.message || {};
    messages.push(msg);

    const calls = msg.tool_calls || [];
    if (!calls.length) {
      const text = (msg.content || '').trim();
      const hist = messages.slice(1); // drop system
      if (onEvent) {
        if (text) onEvent({ type: 'delta', text });
        onEvent({ type: 'done', text, history: hist, toolEvents });
      }
      return { text, history: hist };
    }
    for (const call of calls) {
      const name = call.function?.name;
      let input = call.function?.arguments || {};
      if (typeof input === 'string') {
        try { input = JSON.parse(input); } catch { input = {}; }
      }
      const { result, ok, error } = await runTool(name, input);
      toolEvents.push({ name, input, ok, error });
      if (onEvent) onEvent({ type: 'tool_result', name, ok, error });
      messages.push({ role: 'tool', content: result });
    }
  }
  const text = "I worked through several steps but didn't reach a final answer. Try narrowing the request.";
  const hist = messages.slice(1);
  if (onEvent) {
    onEvent({ type: 'delta', text });
    onEvent({ type: 'done', text, history: hist, toolEvents });
  }
  return { text, history: hist };
}

// Names that aren't usable as the chat brain (embedders, STT, etc.).
const NON_CHAT = /embed|whisper|bge|nomic|minilm|rerank/i;

// Prefer strong tool-calling families when auto-picking an installed model.
const PREFER = ['qwen3', 'qwen2.5', 'qwen2', 'llama3.3', 'llama3.2', 'llama3.1', 'llama3', 'mistral', 'gemma'];

// Parameter size from an Ollama tag, in billions (e.g. "qwen2.5:32b" -> 32,
// "qwen3:30b-a3b" -> 30, "...:1.5b" -> 1.5). Bigger model = stronger, so among
// installed models of the preferred family we pick the LARGEST — "the best
// qwen possible" the user has pulled.
function paramSize(name) {
  const m = /(\d+(?:\.\d+)?)\s*b\b/i.exec(name);
  return m ? parseFloat(m[1]) : 0;
}

function pickModel(names) {
  const chat = names.filter((n) => !NON_CHAT.test(n));
  if (!chat.length) return null;
  const want = config.ollamaModel;
  // 1. exact configured model, only if it's actually installed.
  if (want && chat.includes(want)) return want;
  // 2. strongest available family, and within it the LARGEST variant.
  for (const fam of PREFER) {
    const inFam = chat.filter((n) => n.toLowerCase().startsWith(fam));
    if (inFam.length) return inFam.slice().sort((a, b) => paramSize(b) - paramSize(a))[0];
  }
  // 3. otherwise just the largest chat-capable model.
  return chat.slice().sort((a, b) => paramSize(b) - paramSize(a))[0];
}

async function localReady() {
  try {
    const res = await fetch(`${config.ollamaUrl.replace(/\/$/, '')}/api/tags`, { signal: AbortSignal.timeout(1500) });
    if (!res.ok) return { ready: false, reason: `Ollama responded ${res.status}` };
    const data = await res.json();
    const names = (data.models || []).map((m) => m.name);
    const chosen = pickModel(names);
    if (chosen) {
      resolvedLocalModel = chosen;
      return { ready: true };
    }
    return {
      ready: false,
      reason: names.length
        ? `Ollama is running but only non-chat models are installed (${names.join(', ')}). Run: ollama pull ${config.ollamaModel}`
        : `Ollama is running but no models are pulled. Run: ollama pull ${config.ollamaModel}`,
    };
  } catch {
    return { ready: false, reason: 'Ollama is not running. Install it from https://ollama.com, then: ollama pull ' + config.ollamaModel };
  }
}

// ---------- shared ----------
async function runTool(name, input) {
  const handler = skills.handlerFor(name);
  if (!handler) return { result: `Error: Unknown tool: ${name}`, ok: false, error: 'unknown tool' };
  try {
    const data = await handler(input);
    return { result: JSON.stringify(data), ok: true };
  } catch (err) {
    return { result: `Error: ${err.message}`, ok: false, error: err.message };
  }
}

async function status() {
  if (config.brainEngine === 'claude') {
    return config.anthropicApiKey
      ? { engine: 'claude', model: config.model, ready: true, local: false }
      : { engine: 'claude', model: config.model, ready: false, local: false, reason: 'ANTHROPIC_API_KEY not set' };
  }
  const r = await localReady();
  return { engine: 'local', model: resolvedLocalModel || config.ollamaModel, ready: r.ready, local: true, reason: r.reason };
}

async function ask(userText, history = [], { onEvent } = {}) {
  const toolEvents = [];
  try {
    const s = await status();
    if (!s.ready) {
      const text = `The brain is offline: ${s.reason || 'not configured'} ` +
        '(Panels still work without it.)';
      if (onEvent) onEvent({ type: 'error', error: s.reason || 'not configured' });
      return { ok: false, text, toolEvents, history };
    }
    const out = s.engine === 'claude'
      ? await askClaude(userText, history, toolEvents, onEvent)
      : await askLocal(userText, history, toolEvents, onEvent);
    return { ok: true, text: out.text, toolEvents, history: out.history };
  } catch (err) {
    console.error('[brain] error:', err);
    if (onEvent) onEvent({ type: 'error', error: err.message });
    return { ok: false, text: `Brain error: ${err.message}`, toolEvents, history };
  }
}

module.exports = { ask, status };
