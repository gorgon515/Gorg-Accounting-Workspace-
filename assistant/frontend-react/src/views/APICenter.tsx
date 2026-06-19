import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, timeAgo } from '../lib/format';

const TABS = ['API Keys', 'Rate Limits', 'Webhooks'] as const;
type Tab = typeof TABS[number];
const SCOPES = ['accounting:read', 'reports:read', 'memory:read', 'vault:read'];
const EVENTS = ['accounting.updated', 'backup.completed', 'security.alert', 'sync.completed'];

export function APICenter() {
  const [tab, setTab] = useState<Tab>('API Keys');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to manage the public API." />;
  return (
    <Page
      title="API Center"
      subtitle="keys · rate limits · webhooks"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'API Keys' && <KeysTab />}
      {tab === 'Rate Limits' && <RateLimitsTab />}
      {tab === 'Webhooks' && <WebhooksTab />}
    </Page>
  );
}

function KeysTab() {
  const keys = useAsync(() => helios.publicApi.listKeys(), []);
  const stats = useAsync(() => helios.publicApi.keyStats(), []);
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<string[]>([]);
  const [rpm, setRpm] = useState(60);
  const [created, setCreated] = useState<string | null>(null);

  const list: any[] = keys.data?.keys ?? [];

  function toggleScope(s: string) {
    setScopes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  }

  async function create() {
    if (!name) return;
    const res = await helios.publicApi.createKey({ name, scopes, rate_limit_rpm: rpm });
    setCreated(res?.api_key ?? null);
    setName('');
    setScopes([]);
    keys.reload();
    stats.reload();
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total Keys" value={stats.data?.total_keys ?? '—'} />
        <MetricCard label="Active Keys" value={stats.data?.active_keys ?? '—'} accent />
        <MetricCard label="Total Requests" value={stats.data?.total_requests ?? '—'} />
      </div>
      {created && (
        <Panel title="New API Key — copy it now (shown once)">
          <code className="mono text-[12px] text-gold break-all">{created}</code>
          <div className="mt-2"><Button size="sm" onClick={() => setCreated(null)}>Dismiss</Button></div>
        </Panel>
      )}
      <Panel title="Create API Key">
        <div className="flex flex-wrap items-end gap-2">
          <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
            placeholder="key name" value={name} onChange={(e) => setName(e.target.value)} />
          <input type="number" className="border border-hairline bg-transparent rounded px-2 py-1 text-sm w-24"
            value={rpm} onChange={(e) => setRpm(parseInt(e.target.value) || 60)} />
          <div className="flex flex-wrap gap-2">
            {SCOPES.map((s) => (
              <label key={s} className="mono text-[11px] flex items-center gap-1 text-warmgray">
                <input type="checkbox" checked={scopes.includes(s)} onChange={() => toggleScope(s)} />{s}
              </label>
            ))}
          </div>
          <Button variant="gold" size="sm" onClick={create} disabled={!name}>Create</Button>
        </div>
      </Panel>
      <Panel title="API Keys">
        {keys.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No API keys." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Name</th><th>Prefix</th><th>RPM</th><th>Status</th><th>Last Used</th><th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((k) => (
                <tr key={k.id} className="border-t border-hairline">
                  <td className="py-1.5">{k.name}</td>
                  <td className="mono text-[11px]">{k.key_prefix}…</td>
                  <td>{k.rate_limit_rpm}</td>
                  <td className={cls('mono text-[11px]', k.status === 'active' ? 'text-helgreen' : 'text-helred')}>{k.status}</td>
                  <td className="text-warmgray text-[11px]">{k.last_used_at ? timeAgo(k.last_used_at) : 'never'}</td>
                  <td className="text-right">
                    <Button size="sm" variant="danger"
                      onClick={async () => { await helios.publicApi.revokeKey(k.id); keys.reload(); }}>Revoke</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function RateLimitsTab() {
  const keys = useAsync(() => helios.publicApi.listKeys('active'), []);
  const list: any[] = (keys.data?.keys ?? []).filter((k: any) => k.status === 'active');
  return (
    <Panel title="Rate Limits (per active key)">
      {keys.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No active keys." />
      ) : (
        <div className="grid gap-2">
          {list.map((k) => <RateLimitRow key={k.id} k={k} />)}
        </div>
      )}
    </Panel>
  );
}

function RateLimitRow({ k }: { k: any }) {
  const stats = useAsync(() => helios.publicApi.rateLimitStats(k.id), [k.id]);
  const s = stats.data ?? {};
  return (
    <div className="flex items-center justify-between rounded-lg border border-hairline px-3 py-2">
      <div>
        <span className="text-sm">{k.name}</span>
        <span className="mono text-[11px] text-warmgray ml-2">{k.key_prefix}…</span>
      </div>
      <div className="flex items-center gap-4 mono text-[11px]">
        <span>{s.requests_last_minute ?? 0} / {k.rate_limit_rpm} rpm</span>
        <span className="text-warmgray">blocked: {s.blocked_count ?? 0}</span>
        <Button size="sm" onClick={async () => { await helios.publicApi.rateLimitReset(k.id); stats.reload(); }}>Reset</Button>
      </div>
    </div>
  );
}

function WebhooksTab() {
  const hooks = useAsync(() => helios.publicApi.listWebhooks(), []);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [events, setEvents] = useState<string[]>([]);
  const [secret, setSecret] = useState('');

  const list: any[] = hooks.data?.webhooks ?? [];

  function toggleEvent(e: string) {
    setEvents((cur) => (cur.includes(e) ? cur.filter((x) => x !== e) : [...cur, e]));
  }

  async function create() {
    if (!name || !url) return;
    await helios.publicApi.createWebhook({ name, url, events, secret });
    setName(''); setUrl(''); setEvents([]); setSecret('');
    hooks.reload();
  }

  return (
    <div className="grid gap-3">
      <Panel title="Create Webhook">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-end gap-2">
            <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
              placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
            <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm flex-1 min-w-[220px]"
              placeholder="https://endpoint" value={url} onChange={(e) => setUrl(e.target.value)} />
            <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
              placeholder="signing secret" value={secret} onChange={(e) => setSecret(e.target.value)} />
          </div>
          <div className="flex flex-wrap gap-2">
            {EVENTS.map((e) => (
              <label key={e} className="mono text-[11px] flex items-center gap-1 text-warmgray">
                <input type="checkbox" checked={events.includes(e)} onChange={() => toggleEvent(e)} />{e}
              </label>
            ))}
          </div>
          <div><Button variant="gold" size="sm" onClick={create} disabled={!name || !url}>Create Webhook</Button></div>
        </div>
      </Panel>
      <Panel title="Webhooks">
        {hooks.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No webhooks registered." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Name</th><th>URL</th><th>Events</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((w) => (
                <tr key={w.id} className="border-t border-hairline">
                  <td className="py-1.5">{w.name}</td>
                  <td className="mono text-[11px] text-warmgray truncate max-w-[200px]">{w.url}</td>
                  <td className="mono text-[11px]">{(w.events || []).length}</td>
                  <td className={cls('mono text-[11px]', w.status === 'active' ? 'text-helgreen' : 'text-warmgray')}>{w.status}</td>
                  <td className="text-right flex justify-end gap-1 py-1.5">
                    <Button size="sm" onClick={async () => { await helios.publicApi.deliverWebhook(w.id, { event_type: (w.events || [])[0] || 'accounting.updated', payload: { test: true } }); hooks.reload(); }}>Test</Button>
                    <Button size="sm" variant="danger" onClick={async () => { await helios.publicApi.deleteWebhook(w.id); hooks.reload(); }}>Delete</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
