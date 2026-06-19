import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Feed', 'Alerts', 'Signals', 'Sources'] as const;
type Tab = typeof TABS[number];
const DOMAINS = ['', 'accounting', 'tax', 'finance', 'markets', 'strategy'];

export function IntelligenceCenter() {
  const [tab, setTab] = useState<Tab>('Feed');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Intelligence Center." />;
  return (
    <Page
      title="Intelligence Center"
      subtitle="live intelligence platform · continuous monitoring"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      <StatsRow />
      {tab === 'Feed' && <FeedTab />}
      {tab === 'Alerts' && <AlertsTab />}
      {tab === 'Signals' && <SignalsTab />}
      {tab === 'Sources' && <SourcesTab />}
    </Page>
  );
}

function StatsRow() {
  const stats = useAsync(() => helios.liveIntel.stats(), [], 30000);
  const s = stats.data ?? {};
  return (
    <div className="grid grid-cols-4 gap-3 mb-3">
      <MetricCard label="Intel Items" value={s.total_items ?? 0} accent />
      <MetricCard label="Active Alerts" value={s.active_alerts ?? 0} />
      <MetricCard label="Active Signals" value={s.active_signals ?? 0} />
      <MetricCard label="Sources" value={s.sources ?? 0} />
    </div>
  );
}

function FeedTab() {
  const [domain, setDomain] = useState('');
  const items = useAsync(() => helios.liveIntel.items({ domain: domain || undefined, limit: 40 }), [domain]);
  const list: any[] = Array.isArray(items.data) ? items.data : [];
  return (
    <Panel
      title="Intelligence Feed"
      subtitle="deduplicated, importance-ranked"
      actions={
        <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
          value={domain} onChange={(e) => setDomain(e.target.value)}>
          {DOMAINS.map((d) => <option key={d} value={d}>{d || 'all domains'}</option>)}
        </select>
      }
    >
      {items.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No intelligence items yet. Poll a connector from the Connector Center or run a research mission." />
      ) : (
        <div className="grid gap-2">
          {list.map((it: any) => (
            <div key={it.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm truncate">{it.title}</span>
                <ImportanceBar value={it.importance ?? 0.5} />
              </div>
              {it.content && <p className="text-[11px] text-warmgray line-clamp-2 mt-0.5">{it.content}</p>}
              <div className="mono text-[10px] text-warmgray mt-1 flex gap-3">
                <span>{it.connector_id}</span>
                <span>{it.domain}</span>
                {it.published_at && <span>{String(it.published_at).slice(0, 10)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function AlertsTab() {
  const alerts = useAsync(() => helios.liveIntel.alerts('new'), []);
  const list: any[] = Array.isArray(alerts.data) ? alerts.data : [];
  async function ack(id: string) { await helios.liveIntel.acknowledgeAlert(id); alerts.reload(); }
  return (
    <Panel title="Active Alerts">
      {alerts.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No active alerts." />
      ) : (
        <div className="grid gap-2">
          {list.map((a: any) => (
            <div key={a.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <SeverityTag severity={a.severity} />
                  <span className="text-sm truncate">{a.title}</span>
                </div>
                {a.description && <p className="text-[11px] text-warmgray truncate">{a.description}</p>}
              </div>
              <Button size="sm" onClick={() => ack(a.id)}>Acknowledge</Button>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function SignalsTab() {
  const signals = useAsync(() => helios.liveIntel.signals({ limit: 40 }), []);
  const list: any[] = Array.isArray(signals.data) ? signals.data : [];
  return (
    <Panel title="Intelligence Signals" subtitle="ranked by confidence × impact">
      {signals.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No signals generated yet." />
      ) : (
        <div className="grid gap-2">
          {list.map((sig: any) => (
            <div key={sig.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{sig.title}</span>
                <span className="mono text-[10px] text-gold">{Math.round((sig.confidence ?? 0) * 100)}% conf</span>
              </div>
              {sig.description && <p className="text-[11px] text-warmgray mt-0.5">{sig.description}</p>}
              <span className="mono text-[10px] text-warmgray">{sig.signal_type} · {sig.domain}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function SourcesTab() {
  const sources = useAsync(() => helios.liveIntel.sources(), []);
  const list: any[] = Array.isArray(sources.data) ? sources.data : [];
  return (
    <Panel title="Monitored Sources" subtitle="reliability-scored intelligence sources">
      {sources.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No sources yet. Poll a connector to register it as a source." />
      ) : (
        <div className="grid gap-2">
          {list.map((s: any) => (
            <div key={s.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div>
                <span className="text-sm">{s.name}</span>
                <p className="mono text-[10px] text-warmgray">{s.domain} · {s.item_count ?? 0} items</p>
              </div>
              <span className="mono text-[10px] text-helgreen">rel {Math.round((s.reliability_score ?? 0.7) * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function ImportanceBar({ value }: { value: number }) {
  const pct = Math.min(value * 100, 100);
  return (
    <div className="w-14 h-1.5 rounded-full bg-ivory/10 overflow-hidden shrink-0">
      <div className={cls('h-full rounded-full', pct >= 70 ? 'bg-helred' : pct >= 55 ? 'bg-gold' : 'bg-helgreen')}
        style={{ width: `${pct}%` }} />
    </div>
  );
}

function SeverityTag({ severity }: { severity: string }) {
  const color = severity === 'critical' || severity === 'high' ? 'text-helred'
    : severity === 'medium' ? 'text-gold' : 'text-warmgray';
  return <span className={cls('mono text-[9px] uppercase', color)}>{severity}</span>;
}
