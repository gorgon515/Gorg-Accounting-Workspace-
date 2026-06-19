import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

function statusColor(status: string): string {
  return status === 'critical' ? 'text-helred'
    : status === 'warning' ? 'text-gold'
    : status === 'ok' ? 'text-helgreen'
    : 'text-warmgray';
}

function Bar({ label, pct }: { label: string; pct: number }) {
  const color = pct > 90 ? 'bg-helred' : pct > 75 ? 'bg-gold' : 'bg-helgreen';
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-warmgray">{label}</span>
        <span className="mono">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-obsidian rounded overflow-hidden">
        <div className={cls('h-full rounded transition-all', color)} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}

export function OperationsDashboard() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Operations Dashboard." />;
  const overview = useAsync(() => helios.opsDashboard.overview(), [], 8000);
  const daily = useAsync(() => helios.runtime.dailyDriver(), []);
  const [busy, setBusy] = useState(false);

  const o = overview.data ?? ({} as any);
  const sys = o.system_health ?? {};
  const agents = o.agent_health ?? {};
  const conns = o.connector_health ?? {};
  const voice = o.voice_health ?? {};
  const storage = o.storage_usage ?? {};
  const mem = o.memory_growth ?? {};
  const failures: any[] = o.recent_failures ?? [];
  const mostUsed: any[] = o.most_used_features ?? [];
  const approvals = o.pending_approvals ?? {};
  const dd = daily.data ?? ({} as any);

  async function snapshot() {
    setBusy(true);
    try { await helios.opsDashboard.snapshot(); overview.reload(); }
    finally { setBusy(false); }
  }

  return (
    <Page title="Daily Operations Dashboard" subtitle="the single pane of glass for running HELIOS every day"
      actions={
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={snapshot} disabled={busy}>Snapshot</Button>
          <Button size="sm" onClick={() => { overview.reload(); daily.reload(); }}>Refresh</Button>
        </div>
      }
    >
      {overview.loading && !overview.data ? <Loading /> : (
        <div className="grid gap-3">
          {/* Daily Driver banner */}
          <Panel title="Daily Driver — Morning Operating Picture">
            <div className="grid grid-cols-5 gap-3">
              <MetricCard label="Health" value={dd.health_ok ? 'OK' : '—'} accent={!!dd.health_ok} />
              <MetricCard label="Approvals" value={String(dd.pending_approvals ?? '—')} />
              <MetricCard label="Unread" value={String(dd.unread_notifications ?? '—')} />
              <MetricCard label="Presence" value={String(dd.presence_mode ?? '—').toUpperCase()} />
              <MetricCard label="Voice" value={dd.voice_ready ? 'READY' : '—'} />
            </div>
            {dd.briefing_preview ? (
              <div className="mt-3 border-t border-hairline pt-2 text-[12px] text-ivory/80 italic">
                “{dd.briefing_preview}”
              </div>
            ) : null}
          </Panel>

          {/* Health row */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="System" value={(sys.status || 'unknown').toUpperCase()} />
            <MetricCard label="Agents" value={String(agents.agent_count ?? 0)} />
            <MetricCard label="Connectors" value={String(conns.connector_count ?? 0)} />
            <MetricCard label="Pending Approvals" value={String(approvals.total ?? 0)} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Panel title="System Health">
              <div className="flex flex-col gap-2.5">
                <div className={cls('mono text-[11px] uppercase', statusColor(sys.status))}>{sys.status || 'unknown'}</div>
                <Bar label="CPU" pct={Number(sys.cpu_percent ?? 0)} />
                <Bar label="Memory" pct={Number(sys.memory_percent ?? 0)} />
                <Bar label="Disk" pct={Number(sys.disk_percent ?? 0)} />
              </div>
            </Panel>

            <Panel title="Subsystem Status">
              <div className="grid gap-1.5">
                {[
                  ['Voice OS', voice.status, voice.mode],
                  ['Agents', agents.status, `${agents.agent_count ?? 0} agents`],
                  ['Connectors', conns.status, `${conns.connector_count ?? 0} connectors`],
                ].map(([name, status, detail]: any) => (
                  <div key={name} className="flex items-center justify-between text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span>{name}</span>
                    <span className="flex items-center gap-2">
                      <span className="text-warmgray text-[10px]">{detail}</span>
                      <span className={cls('mono text-[10px] uppercase', statusColor(status))}>{status || '—'}</span>
                    </span>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Panel title="Storage & Memory Growth">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-warmgray">Total storage</span>
                  <span className="mono">{(storage.total_mb ?? 0).toFixed?.(2) ?? storage.total_mb} MB</span>
                </div>
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-warmgray">Databases</span>
                  <span className="mono">{storage.database_count ?? 0}</span>
                </div>
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-warmgray">Memory leak suspected</span>
                  <span className={cls('mono', mem.leak_suspected ? 'text-helred' : 'text-helgreen')}>
                    {mem.leak_suspected ? 'YES' : 'NO'}
                  </span>
                </div>
                <div className="border-t border-hairline pt-2 flex flex-col gap-1 max-h-32 overflow-y-auto scroll-thin">
                  {(storage.databases ?? []).slice(0, 8).map((d: any) => (
                    <div key={d.name} className="flex items-center justify-between text-[10px] mono text-warmgray">
                      <span>{d.name}</span>
                      <span>{(d.size_bytes / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>

            <Panel title="Most-Used Features">
              {mostUsed.length === 0 ? <EmptyState message="No usage data yet." /> : (
                <div className="flex flex-col gap-1.5">
                  {mostUsed.slice(0, 8).map((f: any, i) => (
                    <div key={i} className="flex items-center justify-between text-[12px]">
                      <span>{f.feature || '—'}</span>
                      <span className="mono text-[10px] text-gold">{f.evaluations}</span>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <Panel title="Recent Failures">
            {failures.length === 0 ? <EmptyState message="No recent failures. System stable." /> : (
              <div className="flex flex-col gap-1.5">
                {failures.slice(0, 10).map((f: any, i) => (
                  <div key={i} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className={cls('mono text-[10px] uppercase', statusColor(f.severity === 'critical' ? 'critical' : 'warning'))}>
                      {f.severity || 'error'}
                    </span>
                    <span className="text-ivory/80">{f.component || f.title || '—'}</span>
                    <span className="text-warmgray text-[10px] truncate ml-auto max-w-[50%]">{f.error || ''}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}
    </Page>
  );
}
