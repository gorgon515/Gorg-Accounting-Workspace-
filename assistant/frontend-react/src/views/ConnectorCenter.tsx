import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Catalog', 'Health'] as const;
type Tab = typeof TABS[number];

export function ConnectorCenter() {
  const [tab, setTab] = useState<Tab>('Catalog');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Connector Center." />;
  return (
    <Page
      title="Connector Center"
      subtitle="universal connector framework · 26 data sources"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Catalog' && <CatalogTab />}
      {tab === 'Health' && <HealthTab />}
    </Page>
  );
}

function CatalogTab() {
  const stats = useAsync(() => helios.connectors.stats(), []);
  const list = useAsync(() => helios.connectors.list(), []);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const conns: any[] = Array.isArray(list.data) ? list.data : [];
  const s = stats.data ?? {};

  async function toggle(c: any) {
    setBusy((b) => ({ ...b, [c.id]: true }));
    try {
      if (c.status === 'active') await helios.connectors.disable(c.id);
      else await helios.connectors.enable(c.id);
      list.reload();
      stats.reload();
    } finally {
      setBusy((b) => ({ ...b, [c.id]: false }));
    }
  }

  const byCategory: Record<string, any[]> = {};
  for (const c of conns) (byCategory[c.category] ??= []).push(c);

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Connectors" value={s.total ?? conns.length} accent />
        <MetricCard label="Categories" value={Object.keys(byCategory).length} />
        <MetricCard label="Healthy" value={s.healthy ?? 0} />
        <MetricCard label="Active" value={(s.by_status?.active ?? 0)} />
      </div>
      {list.loading ? <Loading /> : Object.entries(byCategory).map(([cat, items]) => (
        <Panel key={cat} title={cat} subtitle={`${items.length} connector(s)`}>
          <div className="grid gap-2">
            {items.map((c: any) => (
              <div key={c.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{c.name}</span>
                    <span className="mono text-[10px] text-warmgray">{c.kind}</span>
                    {c.requires_credential ? <span className="mono text-[9px] text-gold">🔑 credential</span> : null}
                  </div>
                  {c.description && <p className="text-[11px] text-warmgray truncate">{c.description}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusDot status={c.status} health={c.health_status} />
                  <Button size="sm" onClick={() => toggle(c)} disabled={busy[c.id]}>
                    {c.status === 'active' ? 'Disable' : 'Enable'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  );
}

function HealthTab() {
  const list = useAsync(() => helios.connectors.list(), []);
  const [results, setResults] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const conns: any[] = Array.isArray(list.data) ? list.data : [];

  async function check(id: string) {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      const r = await helios.connectors.health(id);
      setResults((x) => ({ ...x, [id]: r }));
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  }

  return (
    <Panel title="Connector Health" subtitle="probe data sources for reachability">
      {list.loading ? <Loading /> : (
        <div className="grid gap-2">
          {conns.map((c: any) => {
            const r = results[c.id];
            return (
              <div key={c.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                <div>
                  <span className="text-sm">{c.name}</span>
                  <p className="mono text-[10px] text-warmgray">{c.id}</p>
                </div>
                <div className="flex items-center gap-3">
                  {r && (
                    <span className={cls('mono text-[10px]', r.healthy ? 'text-helgreen' : 'text-helred')}>
                      {r.healthy ? `✓ ${r.latency_ms ?? '?'}ms` : `✕ ${(r.error ?? 'unhealthy').slice(0, 40)}`}
                    </span>
                  )}
                  <Button size="sm" onClick={() => check(c.id)} disabled={busy[c.id]}>
                    {busy[c.id] ? '…' : 'Check'}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function StatusDot({ status, health }: { status: string; health?: string }) {
  const color = status === 'active'
    ? (health === 'healthy' ? 'bg-helgreen' : health === 'degraded' ? 'bg-helred' : 'bg-gold')
    : 'bg-warmgray';
  return <span className={cls('w-2 h-2 rounded-full', color)} title={`${status} · ${health ?? 'unknown'}`} />;
}
