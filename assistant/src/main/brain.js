'use strict';

// The Claude "brain": turns a natural-language (or voice) command into actions
// by running a manual tool-use loop against the skill registry.
//
// Manual loop (not the SDK tool-runner) is deliberate — it gives us a place to
// gate, log, or require approval for sensitive actions later (e.g. trades or
// posting accounting entries), which is exactly where you want human-in-the-loop.

const Anthropic = require('@anthropic-ai/sdk');
const config = require('./config');
const skills = require('./services/skills');

let client = null;
function getClient() {
  if (!config.hasBrain()) return null;
  if (!client) client = new Anthropic({ apiKey: config.anthropicApiKey });
  return client;
}

const MAX_TURNS = 6;

// history: array of prior {role, content} messages for multi-turn context.
async function ask(userText, history = []) {
  const anthropic = getClient();
  if (!anthropic) {
    return {
      ok: false,
      text:
        'The AI brain is offline because no Anthropic API key is set. ' +
        'You can still use the watchlist and search panels. Add ANTHROPIC_API_KEY to .env to enable voice and chat.',
      toolEvents: [],
      history,
    };
  }

  const messages = [...history, { role: 'user', content: userText }];
  const tools = skills.allTools();
  const toolEvents = [];

  try {
    for (let turn = 0; turn < MAX_TURNS; turn++) {
      const res = await anthropic.messages.create({
        model: config.model,
        max_tokens: 4000,
        thinking: { type: 'adaptive' },
        system: skills.systemPrompt(),
        tools,
        messages,
      });

      messages.push({ role: 'assistant', content: res.content });

      if (res.stop_reason !== 'tool_use') {
        const text = res.content
          .filter((b) => b.type === 'text')
          .map((b) => b.text)
          .join('')
          .trim();
        return { ok: true, text, toolEvents, history: messages };
      }

      // Execute every requested tool, collect results for the next turn.
      const toolResults = [];
      for (const block of res.content) {
        if (block.type !== 'tool_use') continue;
        const handler = skills.handlerFor(block.name);
        let result;
        try {
          if (!handler) throw new Error(`Unknown tool: ${block.name}`);
          const data = await handler(block.input || {});
          result = JSON.stringify(data);
          toolEvents.push({ name: block.name, input: block.input, ok: true });
        } catch (err) {
          result = `Error: ${err.message}`;
          toolEvents.push({ name: block.name, input: block.input, ok: false, error: err.message });
        }
        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: result,
          is_error: !handler ? true : undefined,
        });
      }
      messages.push({ role: 'user', content: toolResults });
    }

    return {
      ok: true,
      text: "I worked through several steps but didn't reach a final answer. Try narrowing the request.",
      toolEvents,
      history: messages,
    };
  } catch (err) {
    console.error('[brain] error:', err);
    return { ok: false, text: `Brain error: ${err.message}`, toolEvents, history };
  }
}

module.exports = { ask };
