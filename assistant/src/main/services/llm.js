'use strict';

// Embedded local chat engine — the zero-setup brain. Runs a small instruct
// model fully in-process via transformers.js (onnxruntime, CPU): the same
// runtime that already powers the local Whisper voice. No Ollama install, no
// API key, no account. The model weights download once to the local cache
// (like the voice model); after that it works completely offline.
//
// Tool calling is prompt-based (Hermes/Qwen format): the model is told the
// tool list and asked to emit <tool_call>{"name":...,"arguments":{...}}</tool_call>
// when it wants one. brain.js runs the same loop as the other engines, so the
// approval gates are identical — this engine cannot execute trades either.

const config = require('../config');

let pipePromise = null;
let queue = Promise.resolve(); // serialize generations: one model, one session

function pkgInstalled() {
  try {
    require.resolve('@huggingface/transformers');
    return true;
  } catch {
    return false;
  }
}

// Lazily build the text-generation pipeline once. transformers.js is ESM, so
// import() it from CommonJS (same pattern as stt.js).
function getPipeline() {
  if (pipePromise) return pipePromise;
  if (!pkgInstalled()) {
    return Promise.reject(
      new Error('Embedded brain (@huggingface/transformers) is not installed. Run: npm install')
    );
  }
  pipePromise = (async () => {
    const transformers = await import('@huggingface/transformers');
    const { pipeline, env } = transformers;
    if (config.sttModelDir) env.cacheDir = config.sttModelDir;
    let lastFile = '';
    return pipeline('text-generation', config.embeddedModel, {
      dtype: config.embeddedDtype,
      progress_callback: (p) => {
        // First run downloads the weights; log progress so it isn't a silent wait.
        if (p.status === 'progress' && p.file && p.file !== lastFile && p.progress >= 99) {
          lastFile = p.file;
          console.log(`[llm] downloaded ${p.file}`);
        }
      },
    });
  })().catch((err) => {
    pipePromise = null; // allow retry on next attempt
    throw err;
  });
  return pipePromise;
}

// messages: flat [{ role, content }] chat. Returns the assistant's text.
function generate(messages) {
  const run = queue.then(async () => {
    const generator = await getPipeline();
    const out = await generator(messages, {
      max_new_tokens: config.embeddedMaxTokens,
      do_sample: false,
      return_full_text: false,
    });
    const g = out && out[0] && out[0].generated_text;
    if (Array.isArray(g)) {
      // Chat-shaped output: the conversation with the new assistant turn last.
      const last = g[g.length - 1];
      return String((last && last.content) || '');
    }
    return String(g || '');
  });
  queue = run.catch(() => {}); // keep the chain alive after failures
  return run;
}

// ---------- prompt-based tool calling ----------

// Compact one-line signature per tool. 47 full JSON schemas would swamp a
// small CPU model's context; name(args) + a trimmed description is enough.
function toolPrompt(tools) {
  const lines = tools.map((t) => {
    const props = (t.input_schema && t.input_schema.properties) || {};
    const required = new Set((t.input_schema && t.input_schema.required) || []);
    const args = Object.entries(props)
      .map(([k, v]) => `${k}${required.has(k) ? '' : '?'}: ${(v && v.type) || 'any'}`)
      .join(', ');
    const desc = String(t.description || '').replace(/\s+/g, ' ').trim().slice(0, 160);
    return `${t.name}(${args}) — ${desc}`;
  });
  return [
    'You can use tools. To use one, reply with ONLY a tool call, nothing else:',
    '<tool_call>{"name": "tool_name", "arguments": {"arg": "value"}}</tool_call>',
    'Make one tool call at a time. The result will come back inside',
    '<tool_response> tags; then either call another tool or answer the user in',
    'plain text. Arguments marked with ? are optional. Never invent tool names.',
    '',
    'Available tools:',
    ...lines,
  ].join('\n');
}

// Parse <tool_call> blocks (tolerating a missing closing tag and bare JSON —
// small models get the format mostly-right). Returns [{ name, arguments }].
function parseToolCalls(text) {
  const calls = [];
  const tryPush = (raw) => {
    try {
      const obj = JSON.parse(raw);
      if (obj && typeof obj.name === 'string') {
        calls.push({ name: obj.name, arguments: obj.arguments || obj.parameters || {} });
      }
    } catch {
      /* not valid JSON — ignore */
    }
  };
  const tagged = text.matchAll(/<tool_call>\s*([\s\S]*?)\s*<\/tool_call>/g);
  for (const m of tagged) tryPush(m[1]);
  if (!calls.length) {
    // Unclosed tag: take from <tool_call> to the end.
    const open = text.match(/<tool_call>\s*([\s\S]+)$/);
    if (open) tryPush(open[1].trim());
  }
  if (!calls.length) {
    // Whole reply is a bare JSON object that looks like a call.
    const trimmed = text.trim();
    if (trimmed.startsWith('{') && trimmed.includes('"name"')) tryPush(trimmed);
  }
  return calls;
}

// Remove tool markup from a final answer so stray tags never reach the user.
function stripToolMarkup(text) {
  return text
    .replace(/<tool_call>[\s\S]*?(<\/tool_call>|$)/g, '')
    .replace(/<\/?tool_(call|response)>/g, '')
    .trim();
}

function available() {
  return pkgInstalled();
}

function info() {
  return {
    model: config.embeddedModel,
    dtype: config.embeddedDtype,
    pkgInstalled: pkgInstalled(),
  };
}

module.exports = { generate, toolPrompt, parseToolCalls, stripToolMarkup, available, info };
