'use strict';

// Google integration — Gmail (unread) + Calendar (today + write) for the
// Productivity pillar. Uses the OAuth 2.0 desktop "loopback" flow with PKCE:
// we spin a tiny localhost server, open the consent screen in the system
// browser, capture the redirect, and exchange the code for tokens.
//
// Setup (one-time, by the user): create an OAuth client of type "Desktop app"
// in Google Cloud Console, enable the Gmail + Calendar APIs, and put the client
// id/secret in .env as GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.

const http = require('http');
const crypto = require('crypto');
const { shell } = require('electron');
const store = require('../store');

const AUTH = 'https://accounts.google.com/o/oauth2/v2/auth';
const TOKEN = 'https://oauth2.googleapis.com/token';
const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.readonly',
  // calendar.events grants write access to create/update events; broadening
  // scopes requires the user to re-consent on next connect — the flow already
  // uses prompt=consent + access_type=offline so that happens automatically.
  'https://www.googleapis.com/auth/calendar.events',
];

const clientId = () => process.env.GOOGLE_CLIENT_ID || '';
const clientSecret = () => process.env.GOOGLE_CLIENT_SECRET || '';
const configured = () => Boolean(clientId() && clientSecret());

// auth = { access, expiry(ms epoch), email }; refresh token kept as a secret.
const auth = () => store.get('googleAuth', null);
function saveAuth({ access, expiry, email, refresh }) {
  store.set('googleAuth', { access, expiry, email: email ?? auth()?.email ?? null });
  if (refresh) store.setSecret('googleRefresh', refresh);
}
const refreshToken = () => store.getSecret('googleRefresh');

function pkce() {
  const verifier = crypto.randomBytes(32).toString('base64url');
  const challenge = crypto.createHash('sha256').update(verifier).digest('base64url');
  return { verifier, challenge };
}

async function form(url, params) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params).toString(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error_description || data.error || `token HTTP ${res.status}`);
  return data;
}

async function gfetch(url, accessToken) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });
  if (!res.ok) throw new Error(`Google API ${res.status}`);
  return res.json();
}

// POST JSON with bearer auth — mirrors gfetch for write operations.
async function gpost(url, accessToken, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error?.message || `Google API ${res.status}`);
  return data;
}

// Interactive consent. Resolves { connected, email }.
function startAuth() {
  return new Promise((resolve, reject) => {
    if (!configured()) {
      return reject(new Error('Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.'));
    }
    const { verifier, challenge } = pkce();
    const state = crypto.randomBytes(8).toString('hex');
    let port = 0;
    let settled = false;
    const done = (fn, arg) => { if (!settled) { settled = true; try { server.close(); } catch {} fn(arg); } };

    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      const code = url.searchParams.get('code');
      const error = url.searchParams.get('error');
      if (!code && !error) { res.writeHead(204); res.end(); return; }
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body style="font-family:sans-serif;background:#0E0E10;color:#F2EDE4;padding:40px"><h2>ARIA connected to Google.</h2><p>You can close this tab and return to the app.</p></body></html>');
      if (error) return done(reject, new Error(error));
      if (url.searchParams.get('state') !== state) return done(reject, new Error('OAuth state mismatch'));
      try {
        const redirectUri = `http://127.0.0.1:${port}`;
        const tok = await form(TOKEN, {
          client_id: clientId(),
          client_secret: clientSecret(),
          code,
          code_verifier: verifier,
          grant_type: 'authorization_code',
          redirect_uri: redirectUri,
        });
        const email = await gfetch('https://gmail.googleapis.com/gmail/v1/users/me/profile', tok.access_token)
          .then((p) => p.emailAddress)
          .catch(() => null);
        saveAuth({
          access: tok.access_token,
          expiry: Date.now() + (tok.expires_in || 3600) * 1000,
          refresh: tok.refresh_token,
          email,
        });
        done(resolve, { connected: true, email });
      } catch (e) {
        done(reject, e);
      }
    });

    server.on('error', (e) => done(reject, e));
    server.listen(0, '127.0.0.1', () => {
      port = server.address().port;
      const u = new URL(AUTH);
      u.searchParams.set('client_id', clientId());
      u.searchParams.set('redirect_uri', `http://127.0.0.1:${port}`);
      u.searchParams.set('response_type', 'code');
      u.searchParams.set('scope', SCOPES.join(' '));
      u.searchParams.set('access_type', 'offline');
      u.searchParams.set('prompt', 'consent');
      u.searchParams.set('code_challenge', challenge);
      u.searchParams.set('code_challenge_method', 'S256');
      u.searchParams.set('state', state);
      shell.openExternal(u.toString());
    });

    setTimeout(() => done(reject, new Error('Google authorization timed out.')), 180000);
  });
}

async function getAccessToken() {
  const a = auth();
  if (a && a.access && a.expiry && a.expiry > Date.now() + 60000) return a.access;
  const refresh = refreshToken();
  if (!refresh) throw new Error('Not connected to Google.');
  const tok = await form(TOKEN, {
    client_id: clientId(),
    client_secret: clientSecret(),
    refresh_token: refresh,
    grant_type: 'refresh_token',
  });
  saveAuth({ access: tok.access_token, expiry: Date.now() + (tok.expires_in || 3600) * 1000 });
  return tok.access_token;
}

async function listUnread() {
  const at = await getAccessToken();
  const list = await gfetch(
    'https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread&maxResults=8',
    at
  );
  const ids = (list.messages || []).map((m) => m.id);
  const items = await Promise.all(
    ids.map(async (id) => {
      const m = await gfetch(
        `https://gmail.googleapis.com/gmail/v1/users/me/messages/${id}?format=metadata&metadataHeaders=From&metadataHeaders=Subject`,
        at
      );
      const h = Object.fromEntries((m.payload?.headers || []).map((x) => [x.name.toLowerCase(), x.value]));
      return { from: h.from || '', subject: h.subject || '(no subject)', snippet: m.snippet || '' };
    })
  );
  return { unread: list.resultSizeEstimate ?? items.length, items };
}

async function listEvents() {
  const at = await getAccessToken();
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();
  const data = await gfetch(
    `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${encodeURIComponent(start)}&timeMax=${encodeURIComponent(end)}&singleEvents=true&orderBy=startTime&maxResults=10`,
    at
  );
  return (data.items || []).map((e) => ({
    summary: e.summary || '(no title)',
    start: e.start?.dateTime || e.start?.date || null,
    end: e.end?.dateTime || e.end?.date || null,
    location: e.location || '',
  }));
}

// Creates a Google Calendar event on the user's primary calendar. Returns a
// tidy summary object; the full event is also reachable via htmlLink.
// Parameters:
//   summary      (string, required) — event title
//   start        (string, required) — ISO 8601 datetime or YYYY-MM-DD for allDay
//   end          (string, optional) — ISO 8601 datetime / YYYY-MM-DD; defaults
//                                     to start+60 min (timed) or start+1 day (allDay)
//   description  (string, optional)
//   location     (string, optional)
//   timeZone     (string, optional) — IANA tz; defaults to the host system tz
//   allDay       (boolean, optional) — when true uses date-only start/end fields
async function createEvent({ summary, start, end, description, location, timeZone, allDay } = {}) {
  if (!summary) throw new Error('createEvent: summary is required.');
  if (!start) throw new Error('createEvent: start is required.');

  const at = await getAccessToken();
  const tz = timeZone || Intl.DateTimeFormat().resolvedOptions().timeZone;

  let startField, endField;
  if (allDay) {
    // Google all-day events use date-only strings; end date is exclusive.
    const startDate = start.slice(0, 10); // keep YYYY-MM-DD portion
    let endDate;
    if (end) {
      endDate = end.slice(0, 10);
    } else {
      const d = new Date(startDate + 'T00:00:00');
      d.setDate(d.getDate() + 1);
      endDate = d.toISOString().slice(0, 10);
    }
    startField = { date: startDate };
    endField = { date: endDate };
  } else {
    const startDt = new Date(start);
    let endDt;
    if (end) {
      endDt = new Date(end);
    } else {
      endDt = new Date(startDt.getTime() + 60 * 60 * 1000); // +60 minutes
    }
    startField = { dateTime: startDt.toISOString(), timeZone: tz };
    endField = { dateTime: endDt.toISOString(), timeZone: tz };
  }

  const body = { summary, start: startField, end: endField };
  if (description) body.description = description;
  if (location) body.location = location;

  const ev = await gpost(
    'https://www.googleapis.com/calendar/v3/calendars/primary/events',
    at,
    body
  );

  return {
    id: ev.id,
    summary: ev.summary,
    start: ev.start,
    end: ev.end,
    htmlLink: ev.htmlLink,
  };
}

function status() {
  return { configured: configured(), connected: Boolean(refreshToken()), email: auth()?.email || null };
}

function disconnect() {
  store.set('googleAuth', null);
  store.setSecret('googleRefresh', null);
  return { connected: false };
}

const tools = [
  {
    name: 'check_email',
    description: 'Get the user\'s unread Gmail (sender + subject). Call when they ask about email or their inbox. Requires Google to be connected.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'get_agenda',
    description: 'Get the user\'s Google Calendar events for today. Call when they ask about their schedule, agenda, or meetings. Requires Google to be connected.',
    input_schema: { type: 'object', properties: {} },
  },
  {
    name: 'add_calendar_event',
    description: 'Create an event on the user\'s Google Calendar (syncs to their phone). Call when the user asks to schedule/add/remind something with a date or time. Requires Google connected.',
    input_schema: {
      type: 'object',
      properties: {
        summary: {
          type: 'string',
          description: 'Event title (required).',
        },
        start: {
          type: 'string',
          description: 'ISO 8601 datetime (e.g. 2026-06-14T09:00:00) or YYYY-MM-DD for all-day events (required).',
        },
        end: {
          type: 'string',
          description: 'ISO 8601 datetime or YYYY-MM-DD. Optional — omit to use durationMinutes or the default of 60 min.',
        },
        durationMinutes: {
          type: 'number',
          description: 'Duration in minutes, used to compute end when end is omitted. Defaults to 60.',
        },
        description: {
          type: 'string',
          description: 'Optional event notes or description.',
        },
        location: {
          type: 'string',
          description: 'Optional event location (address or room).',
        },
        allDay: {
          type: 'boolean',
          description: 'Set to true for all-day events. start/end should be YYYY-MM-DD strings.',
        },
      },
      required: ['summary', 'start'],
    },
  },
];

const handlers = {
  check_email: async () => {
    if (!status().connected) return { connected: false, note: 'Google is not connected. Ask the user to connect it in the app.' };
    return listUnread();
  },
  get_agenda: async () => {
    if (!status().connected) return { connected: false, note: 'Google is not connected. Ask the user to connect it in the app.' };
    return { events: await listEvents() };
  },
  add_calendar_event: async ({ summary, start, end, durationMinutes, description, location, allDay } = {}) => {
    if (!status().connected) return { connected: false, note: 'Google is not connected. Ask the user to connect it in the Connections panel.' };
    // Translate durationMinutes into an explicit end time when end is omitted.
    let resolvedEnd = end;
    if (!resolvedEnd && !allDay && durationMinutes) {
      const startDt = new Date(start);
      resolvedEnd = new Date(startDt.getTime() + durationMinutes * 60 * 1000).toISOString();
    }
    const event = await createEvent({ summary, start, end: resolvedEnd, description, location, allDay });
    return { created: true, event };
  },
};

module.exports = {
  name: 'google',
  systemPromptFragment:
    'When Google is connected you can read the user\'s unread Gmail, read today\'s Google Calendar events, AND add new events to the user\'s Google Calendar via add_calendar_event (events sync to their phone automatically). ' +
    'If any tool call returns connected:false, tell the user to connect Google in the Connections panel — do not guess or fabricate data. ' +
    'After successfully creating a calendar event, confirm the event title and time back to the user.',
  tools,
  handlers,
  api: { startAuth, status, disconnect, listUnread, listEvents, createEvent },
};
