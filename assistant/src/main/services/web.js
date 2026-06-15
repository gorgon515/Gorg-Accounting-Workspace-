'use strict';

// Web access — lets ARIA "go online" on ANY brain (local Ollama or Claude),
// keyless. Two tools: web_search (DuckDuckGo) and fetch_url (read a page).
// Runs in the main process, so no renderer CSP applies. Best-effort: if the
// network or a provider is unavailable, it returns a clear error rather than
// throwing, so the brain can recover gracefully.
//
// (When the brain is Claude, it ALSO has Anthropic's server-side web search;
//  these tools give the local engine the same reach and add raw page reading.)

const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

function decodeEntities(s) {
  return String(s || '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/&#x2F;/g, '/');
}
const stripTags = (s) => decodeEntities(String(s || '').replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();

// DuckDuckGo's HTML endpoint wraps result links in a redirect (…/l/?uddg=…).
function unwrap(href) {
  try {
    const m = /[?&]uddg=([^&]+)/.exec(href);
    if (m) return decodeURIComponent(m[1]);
  } catch { /* fall through */ }
  return href && href.startsWith('//') ? 'https:' + href : href;
}

async function webSearch(query) {
  const q = String(query || '').trim();
  if (!q) throw new Error('Empty search query.');
  const res = await fetch('https://html.duckduckgo.com/html/?q=' + encodeURIComponent(q), {
    headers: { 'User-Agent': UA, Accept: 'text/html' },
  });
  if (!res.ok) throw new Error(`Search failed (HTTP ${res.status}).`);
  const html = await res.text();
  const results = [];
  const linkRe = /<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
  const snipRe = /<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>([\s\S]*?)<\/a>/g;
  const snippets = [];
  let s;
  while ((s = snipRe.exec(html)) !== null) snippets.push(stripTags(s[1]));
  let m;
  let i = 0;
  while ((m = linkRe.exec(html)) !== null && results.length < 6) {
    const url = unwrap(m[1]);
    const title = stripTags(m[2]);
    if (title && url) results.push({ title, url, snippet: snippets[i] || '' });
    i++;
  }
  return { query: q, results, note: results.length ? undefined : 'No results found.' };
}

async function fetchUrl(url) {
  let u = String(url || '').trim();
  if (!u) throw new Error('No URL provided.');
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  const res = await fetch(u, { headers: { 'User-Agent': UA, Accept: 'text/html,*/*' }, redirect: 'follow' });
  if (!res.ok) throw new Error(`Fetch failed (HTTP ${res.status}).`);
  const ct = res.headers.get('content-type') || '';
  const raw = await res.text();
  if (!/html/i.test(ct)) {
    return { url: u, contentType: ct, text: raw.slice(0, 6000) };
  }
  const titleM = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(raw);
  const body = raw
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ');
  const text = stripTags(body).slice(0, 6000);
  return { url: u, title: titleM ? stripTags(titleM[1]) : '', text };
}

const tools = [
  {
    name: 'web_search',
    description:
      'Search the live web (keyless) and get the top results with titles, URLs, and snippets. Call this whenever the answer depends on current, real-world, or external information you are not certain of — news, prices of non-stock things, definitions, how-tos, facts that may have changed. Prefer searching over guessing.',
    input_schema: {
      type: 'object',
      properties: { query: { type: 'string', description: 'What to search for' } },
      required: ['query'],
    },
  },
  {
    name: 'fetch_url',
    description:
      'Fetch a web page (or a URL returned by web_search) and return its readable text. Call this to read an article or page in detail after a search, or when the user gives you a link.',
    input_schema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'The URL to read' } },
      required: ['url'],
    },
  },
];

const handlers = {
  web_search: ({ query }) => webSearch(query),
  fetch_url: ({ url }) => fetchUrl(url),
};

module.exports = {
  name: 'web',
  systemPromptFragment:
    'You can go ONLINE: web_search runs a live web search and fetch_url reads a page. Use them whenever current or external information would make your answer better or more accurate, then synthesize and cite the source. Do not claim to lack internet access — search instead.',
  tools,
  handlers,
  api: { webSearch, fetchUrl },
};
