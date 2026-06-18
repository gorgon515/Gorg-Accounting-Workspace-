import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, timeAgo } from '../lib/format';

const TABS = ['Dashboard', 'Errors', 'Incidents'] as const;
type Tab = typeof TABS[number];

export function PerformanceMonitor() {
  const [tab, setTab] = useState<Tab>('Dashboard');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to view monitoring." />;
  return (
    <Page
      title="Performance Monitor"
      subtitle="metrics · errors · incidents"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Dashboard' && <DashboardTab />}
      {tab === 'Errors' && <ErrorsTab />}
      {tab === 'Incidents' && <IncidentsTab />}
    </Page>
  );
}

function DashboardTab() {
  const dash = useAsync(() => helios.monitoring.performanceDashboard(), [], 30000);
  if (dash.loading && !dash.data) return <Loading />;
  const metrics: any[] = dash.data?.metrics ?? [];
  const avg = metrics.length ? (metrics.reduce((s, m) => s + (m.mean || 0), 0) / metrics.length).toFixed(1) : '—';

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Metrics" value={metrics.length} />
        <MetricCard label="Samples" value={dash.data?.sample_count ?? 0} />
        <MetricCard label="Avg (mean)" value={avg} accent />
      </div>
      <Panel title="Metric Percentiles" subtitle="auto-refresh 30s">
        {metrics.length === 0 ? (
          <EmptyState message="No performance samples recorded." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Metric</th><th>Count</th><th>p50</th><th>p95</th><th>p99</th><th>Min</th><th>Max</th><th>Mean</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.metric_name} className="border-t border-hairline">
                  <td className="py-1.5">{m.metric_name}</td>
                  <td>{m.count}</td>
                  <td className="tabular-nums">{m.p50}</td>
                  <td className="tabular-nums">{m.p95}</td>
                  <td className="tabular-nums text-gold">{m.p99}</td>
                  <td className="tabular-nums">{m.min}</td>
                  <td className="tabular-nums">{m.max}</td>
                  <td className="tabular-nums">{m.mean}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function ErrorsTab() {
  const [severity, setSeverity] = useState('');
  const errors = useAsync(() => helios.monitoring.listErrors(severity ? { severity } : undefined), [severity]);
  const stats = useAsync(() => helios.monitoring.errorStats(), []);
  const list: any[] = errors.data?.errors ?? [];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total" value={stats.data?.total ?? 0} />
        <MetricCard label="Unresolved" value={stats.data?.unresolved ?? 0} accent />
        <MetricCard label="Last 24h" value={stats.data?.recent_24h ?? 0} />
      </div>
      <Panel
        title="Errors"
        actions={
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">all severities</option>
            <option value="critical">critical</option>
            <option value="error">error</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
        }
      >
        {errors.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No errors recorded." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Type</th><th>Message</th><th>Component</th><th>Severity</th><th>When</th><th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((e) => (
                <tr key={e.id} className="border-t border-hairline">
                  <td className="py-1.5 mono text-[11px]">{e.error_type}</td>
                  <td className="text-warmgray truncate max-w-[260px]">{(e.message || '').slice(0, 60)}</td>
                  <td className="mono text-[11px]">{e.component || '—'}</td>
                  <td className={cls('mono text-[11px] uppercase',
                    e.severity === 'critical' ? 'text-helred' : e.severity === 'warning' ? 'text-gold' : 'text-warmgray')}>
                    {e.severity}
                  </td>
                  <td className="text-warmgray text-[11px]">{timeAgo(e.created_at)}</td>
                  <td className="text-right">
                    {!e.resolved && (
                      <Button size="sm" onClick={async () => { await helios.monitoring.resolveError(String(e.id), {}); errors.reload(); stats.reload(); }}>
                        Resolve
                      </Button>
                    )}
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

function IncidentsTab() {
  const [status, setStatus] = useState('');
  const incidents = useAsync(() => helios.monitoring.listIncidents(status ? { status } : undefined), [status]);
  const mttr = useAsync(() => helios.monitoring.mttrStats(), []);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [sev, setSev] = useState('medium');

  const list: any[] = incidents.data?.incidents ?? [];

  async function create() {
    if (!title) return;
    await helios.monitoring.createIncident({ title, description: desc, severity: sev });
    setTitle(''); setDesc('');
    incidents.reload();
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Resolved" value={mttr.data?.total_resolved ?? 0} />
        <MetricCard label="Mean MTTR (min)" value={mttr.data?.mean_minutes ?? 0} accent />
        <MetricCard label="Median (min)" value={mttr.data?.median_minutes ?? 0} />
      </div>
      <Panel title="Create Incident">
        <div className="flex flex-wrap items-end gap-2">
          <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
            placeholder="title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm flex-1 min-w-[200px]"
            placeholder="description" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-sm"
            value={sev} onChange={(e) => setSev(e.target.value)}>
            {['low', 'medium', 'high', 'critical'].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <Button variant="gold" size="sm" onClick={create} disabled={!title}>Create</Button>
        </div>
      </Panel>
      <Panel
        title="Incidents"
        actions={
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all</option>
            {['open', 'investigating', 'resolved', 'closed'].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        }
      >
        {incidents.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No incidents." />
        ) : (
          <div className="grid gap-1">
            {list.map((i) => (
              <div key={i.id} className="rounded-lg border border-hairline">
                <button className="w-full flex items-center justify-between px-3 py-2 text-left"
                  onClick={() => setExpanded(expanded === i.id ? null : i.id)}>
                  <span className="text-sm">{i.title}</span>
                  <span className="flex items-center gap-3 mono text-[11px]">
                    <span className={cls(i.severity === 'critical' || i.severity === 'high' ? 'text-helred' : 'text-gold')}>{i.severity}</span>
                    <span className="text-warmgray uppercase">{i.status}</span>
                  </span>
                </button>
                {expanded === i.id && <IncidentDetail id={i.id} onChange={() => incidents.reload()} />}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function IncidentDetail({ id, onChange }: { id: string; onChange: () => void }) {
  const single = useAsync(() => helios.monitoring.listIncidents().then((r: any) =>
    (r.incidents || []).find((x: any) => x.id === id) || null), [id]);

  const inc: any = single.data;
  if (!inc) return <div className="px-3 pb-3"><Loading /></div>;

  return (
    <div className="px-3 pb-3 border-t border-hairline">
      <p className="text-[12px] text-warmgray mt-2">{inc.description || 'No description.'}</p>
      <div className="flex gap-1 mt-2">
        {inc.status !== 'investigating' && (
          <Button size="sm" onClick={async () => { await helios.monitoring.updateIncident(id, { status: 'investigating' }); onChange(); single.reload(); }}>Investigate</Button>
        )}
        {inc.status !== 'resolved' && (
          <Button size="sm" variant="primary" onClick={async () => { await helios.monitoring.resolveIncident(id, { resolution: 'Resolved from HUD' }); onChange(); single.reload(); }}>Resolve</Button>
        )}
      </div>
    </div>
  );
}
