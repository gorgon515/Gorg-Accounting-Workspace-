'use strict';

// The brain: turns natural-language (or voice) commands into actions by
// running a tool-use loop against the skill registry.
//
// Three engines:
//   • 'embedded' — built-in model via transformers.js, fully in-process. Zero
//                  setup: no API key, no Ollama; weights download once, then
//                  it works offline. The out-of-the-box default.
//   • 'local'    — Ollama (http://127.0.0.1:11434). Fully on-device, stronger
//                  than embedded if you've installed it and pulled a model.
//   • 'claude'   — Anthropic API (claude-opus-4-8). Strongest reasoning; needs
//                  ANTHROPIC_API_KEY.
// Default ('auto'): claude if a key is set → Ollama if it's running → embedded.
//
// All run the same manual loop so approval gates and logging stay in one
// place — the brain can only call tools the skills expose; trade execution is
// not one of them.

const Anthropic = require('@anthropic-ai/sdk');
const config = require('./config');
const skills = require('./services/skills');
const llm = require('./services/llm');
const store = require('./store');

const MAX_TURNS = 6;

// Live brain preferences: persisted choices (set in-app) override .env defaults
// so the user can switch engines/keys at runtime without editing files. The
// Anthropic key is read from the encrypted secret store, falling back to env.
function prefs() {
  const s = store.get('brainPrefs', {}) || {};
  return {
    engine: String(s.engine || config.brainEngine || 'auto').toLowerCase(),
    anthropicApiKey: store.getSecret('anthropicKey') || config.anthropicApiKey || '',
    model: s.claudeModel || config.model,
  };
}

// ---------- Claude engine ----------
let client = null;
let clientKey = null;
function getClient(apiKey) {
  if (!apiKey) return null;
  if (!client || clientKey !== apiKey) { client = new Anthropic({ apiKey }); clientKey = apiKey; }
  return client;
}

async function askClaude(userText, history, toolEvents) {
  const p = prefs();
  const anthropic = getClient(p.anthropicApiKey);
  const messages = [...history, { role: 'user', content: userText }];
  const tools = skills.allTools();

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const res = await anthropic.messages.create({
      model: p.model,
      max_tokens: 4000,
      thinking: { type: 'adaptive' },
      system: skills.systemPrompt(),
      tools,
      messages,
    });

    messages.push({ role: 'assistant', content: res.content });

    if (res.stop_reason !== 'tool_use') {
      const text = res.content.filter((b) => b.type === 'text').map((b) => b.text).join('').trim();
      return { text, history: messages };
    }

    const toolResults = [];
    for (const block of res.content) {
      if (block.type !== 'tool_use') continue;
      const { result, ok, error } = await runTool(block.name, block.input || {});
      toolEvents.push({ name: block.name, input: block.input, ok, error });
      toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: result });
    }
    messages.push({ role: 'user', content: toolResults });
  }
  return { text: "I worked through several steps but didn't reach a final answer. Try narrowing the request.", history: messages };
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

async function askLocal(userText, history, toolEvents) {
  // history is kept in Ollama's flat {role, content} shape for this engine.
  const messages = [
    { role: 'system', content: skills.systemPrompt() },
    ...history.filter((m) => m.role !== 'system'),
    { role: 'user', content: userText },
  ];
  const tools = toOllamaTools(skills.allTools());

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const data = await ollamaChat(messages, tools);
    const msg = data.message || {};
    messages.push(msg);

    const calls = msg.tool_calls || [];
    if (!calls.length) {
      return { text: (msg.content || '').trim(), history: messages.slice(1) }; // drop system
    }
    for (const call of calls) {
      const name = call.function?.name;
      let input = call.function?.arguments || {};
      if (typeof input === 'string') {
        try { input = JSON.parse(input); } catch { input = {}; }
      }
      const { result, ok, error } = await runTool(name, input);
      toolEvents.push({ name, input, ok, error });
      messages.push({ role: 'tool', content: result });
    }
  }
  return { text: "I worked through several steps but didn't reach a final answer. Try narrowing the request.", history: messages.slice(1) };
}

// Names that aren't usable as the chat brain (embedders, STT, etc.).
const NON_CHAT = /embed|whisper|bge|nomic|minilm|rerank/i;

// Prefer strong tool-calling families when auto-picking an installed model.
const PREFER = ['qwen3', 'qwen2.5', 'qwen2', 'llama3.3', 'llama3.2', 'llama3.1', 'llama3', 'mistral', 'gemma'];

function pickModel(names) {
  const want = config.ollamaModel;
  // 1. exact or same-family match with the configured model
  const exact = names.find((n) => n === want) || names.find((n) => n.startsWith(want.split(':')[0]));
  if (exact) return exact;
  // 2. best available by family preference
  const chat = names.filter((n) => !NON_CHAT.test(n));
  for (const fam of PREFER) {
    const hit = chat.find((n) => n.toLowerCase().startsWith(fam));
    if (hit) return hit;
  }
  // 3. anything chat-capable
  return chat[0] || null;
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

// ---------- Embedded engine (in-process, transformers.js) ----------
async function askEmbedded(userText, history, toolEvents) {
  // Flat {role, content} history, like the Ollama engine. Tool results are
  // wrapped as user turns in <tool_response> tags (Hermes/Qwen convention)
  // rather than a 'tool' role, which not every chat template accepts.
  const system = skills.systemPrompt() + '\n\n' + llm.toolPrompt(skills.allTools());
  const messages = [
    { role: 'system', content: system },
    ...history.filter((m) => m.role !== 'system'),
    { role: 'user', content: userText },
  ];

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const reply = await llm.generate(messages);
    messages.push({ role: 'assistant', content: reply });

    const calls = llm.parseToolCalls(reply);
    if (!calls.length) {
      return { text: llm.stripToolMarkup(reply), history: messages.slice(1) }; // drop system
    }
    for (const call of calls) {
      const { result, ok, error } = await runTool(call.name, call.arguments);
      toolEvents.push({ name: call.name, input: call.arguments, ok, error });
      messages.push({ role: 'user', content: `<tool_response>\n${result}\n</tool_response>` });
    }
  }
  return { text: "I worked through several steps but didn't reach a final answer. Try narrowing the request.", history: messages.slice(1) };
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

function embeddedStatus() {
  return llm.available()
    ? { engine: 'embedded', model: config.embeddedModel, ready: true, local: true }
    : {
        engine: 'embedded', model: config.embeddedModel, ready: false, local: true,
        reason: 'The built-in model package (@huggingface/transformers) is missing. Run: npm install',
      };
}

async function status() {
  const p = prefs();
  const engine = p.engine;
  if (engine === 'claude' || (engine === 'auto' && p.anthropicApiKey)) {
    return p.anthropicApiKey
      ? { engine: 'claude', model: p.model, ready: true, local: false }
      : { engine: 'claude', model: p.model, ready: false, local: false, reason: 'No Anthropic API key — add one to use Claude.' };
  }
  if (engine === 'embedded') return embeddedStatus();
  const r = await localReady();
  if (r.ready || engine === 'local') {
    return { engine: 'local', model: resolvedLocalModel || config.ollamaModel, ready: r.ready, local: true, reason: r.reason };
  }
  // auto: Ollama isn't available — fall back to the zero-setup embedded brain.
  return embeddedStatus();
}

// ---------- in-app brain settings (the "stronger brain" switcher) ----------
const VALID_ENGINES = ['auto', 'embedded', 'local', 'claude'];

// Snapshot for the UI: which engine is chosen, whether a key is present, how
// each option's availability looks, and the resolved live status. The key
// itself is never returned to the renderer.
async function getSettings() {
  const s = store.get('brainPrefs', {}) || {};
  const storedKey = store.getSecret('anthropicKey');
  const live = await status();
  const ollama = await localReady();
  return {
    engine: String(s.engine || config.brainEngine || 'auto').toLowerCase(),
    status: live,
    hasKey: Boolean(storedKey || config.anthropicApiKey),
    keySource: storedKey ? 'stored' : (config.anthropicApiKey ? 'env' : null),
    encryptionAvailable: store.encryptionAvailable(),
    claudeModel: prefs().model,
    ollama: { ready: ollama.ready, reason: ollama.reason },
    embeddedAvailable: llm.available(),
  };
}

function setEngine(engine) {
  engine = String(engine || '').toLowerCase();
  if (!VALID_ENGINES.includes(engine)) throw new Error(`engine must be one of ${VALID_ENGINES.join(', ')}`);
  const s = store.get('brainPrefs', {}) || {};
  s.engine = engine;
  store.set('brainPrefs', s);
  return getSettings();
}

// Validate the key with a 1-token call, then persist (encrypted) and switch to
// Claude. A clear auth failure is rejected; a network/other error still saves
// the key (marked unverified) so offline setup isn't blocked.
async function setKey(apiKey) {
  apiKey = String(apiKey || '').trim();
  if (!apiKey) throw new Error('API key is required.');
  let verified = false;
  try {
    const test = new Anthropic({ apiKey });
    await test.messages.create({ model: config.model, max_tokens: 1, messages: [{ role: 'user', content: 'hi' }] });
    verified = true;
  } catch (e) {
    const code = e && (e.status || e.statusCode);
    if (code === 401 || code === 403) throw new Error('That API key was rejected by Anthropic. Check it and try again.');
    // else: network/other — accept but unverified.
  }
  store.setSecret('anthropicKey', apiKey);
  const s = store.get('brainPrefs', {}) || {};
  s.engine = 'claude';
  store.set('brainPrefs', s);
  client = null; clientKey = null; // force rebuild with the new key
  return { ...(await getSettings()), verified };
}

function clearKey() {
  store.setSecret('anthropicKey', null);
  const s = store.get('brainPrefs', {}) || {};
  if (s.engine === 'claude') s.engine = 'auto'; // don't strand on a keyless Claude
  store.set('brainPrefs', s);
  client = null; clientKey = null;
  return getSettings();
}

async function ask(userText, history = []) {
  const toolEvents = [];
  try {
    const s = await status();
    if (!s.ready) {
      return {
        ok: false,
        text: `The brain is offline: ${s.reason || 'not configured'} ` +
          '(Panels still work without it.)',
        toolEvents,
        history,
      };
    }
    const out = s.engine === 'claude'
      ? await askClaude(userText, history, toolEvents)
      : s.engine === 'embedded'
        ? await askEmbedded(userText, history, toolEvents)
        : await askLocal(userText, history, toolEvents);
    return { ok: true, text: out.text, toolEvents, history: out.history };
  } catch (err) {
    console.error('[brain] error:', err);
    return { ok: false, text: `Brain error: ${err.message}`, toolEvents, history };
  }
}

// Preload the local model in the background when the embedded engine is the
// active one, so the user's first message gets a fast (warm) reply. No-op for
// the claude/ollama engines. Never throws to the caller.
async function warmup() {
  try {
    const s = await status();
    if (s.engine === 'embedded' && s.ready) await llm.warmup();
    return { engine: s.engine, warmed: s.engine === 'embedded' };
  } catch {
    return { warmed: false };
  }
}

module.exports = { ask, status, warmup, getSettings, setEngine, setKey, clearKey };
