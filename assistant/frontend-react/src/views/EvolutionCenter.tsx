import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const PRIORITIES = ['low', 'medium', 'high', 'critical'];
const STATUSES = ['backlog', 'planned', 'in_progress', 'done', 'wont_fix'];

function prioColor(p: string): string {
  return p === 'critical' ? 'text-helred'
    : p === 'high' ? 'text-gold'
    : p === 'medium' ? 'text-ivory'
    : 'text-warmgray';
}

export function EvolutionCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Evolution Center." />;
  const prioritized = useAsync(() => helios.evolution.prioritized(), [], 10000);
  const stats = useAsync(() => helios.evolution.stats(), [], 10000);
  const friction = useAsync(() => helios.feedback.topFriction(), [], 10000);
  const fbSummary = useAsync(() => helios.feedback.summary(), [], 10000);
  const crashAnalysis = useAsync(() => helios.stability.crashAnalysis(), [], 10000);
  const clusters = useAsync(() => helios.stability.clusters(), [], 10000);
  const memLeak = useAsync(() => helios.stability.memoryLeak(), [], 10000);
  const agentRel = useAsync(() => helios.stability.agentReliability(), [], 10000);

  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');
  const [priority, setPriority] = useState('medium');

  const s = stats.data ?? ({} as any);
  const items: any[] = prioritized.data ?? [];
  const fric: any[] = friction.data ?? [];
  const fbs = fbSummary.data ?? ({} as any);
  const ca = crashAnalysis.data ?? ({} as any);
  const clus: any[] = clusters.data ?? [];
  const ml = memLeak.data ?? ({} as any);
  const ar: any[] = agentRel.data ?? [];

  async function addItem() {
    if (!problem.trim()) return;
    setBusy(true);
    try {
      await helios.evolution.add({ problem: problem.trim(), priority, source: 'manual' });
      setProblem(''); prioritized.reload(); stats.reload();
    } finally { setBusy(false); }
  }

  async function advance(item: any, status: string) {
    setBusy(true);
    try { await helios.evolution.setStatus(item.id, { status }); prioritized.reload(); stats.reload(); }
    finally { setBusy(false); }
  }

  async function promoteFriction(f: any) {
    setBusy(true);
    try {
      await helios.evolution.add({
        problem: f.title, impact: 'recurring friction', frequency: f.frequency,
        suggested_solution: f.suggested_fix || '', priority: f.frequency > 3 ? 'high' : 'medium',
        source: 'feedback',
      });
      prioritized.reload(); stats.reload();
    } finally { setBusy(false); }
  }

  return (
    <Page title="Continuous Evolution" subtitle="improvement backlog · stability analytics · user feedback"
      actions={<Button size="sm" onClick={() => { prioritized.reload(); stats.reload(); friction.reload(); crashAnalysis.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Backlog Open" value={String(s.open ?? 0)} accent />
          <MetricCard label="Total Items" value={String(s.total ?? 0)} />
          <MetricCard label="Crashes" value={String(ca.total ?? 0)} />
          <MetricCard label="Memory Leak" value={ml.leak_suspected ? 'SUSPECTED' : 'CLEAR'} />
        </div>

        {/* Improvement backlog */}
        <Panel title="Improvement Backlog (prioritized)">
          <div className="flex gap-1.5 mb-3">
            <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
              placeholder="Describe a problem to track" value={problem}
              onChange={(e) => setProblem(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addItem()} />
            <select value={priority} onChange={(e) => setPriority(e.target.value)}
              className="bg-obsidian border border-hairline rounded px-2 py-1 text-[11px] mono">
              {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <Button size="sm" variant="gold" onClick={addItem} disabled={busy}>Add</Button>
          </div>
          {prioritized.loading ? <Loading /> : items.length === 0 ? (
            <EmptyState message="Backlog empty. The platform is stable." />
          ) : (
            <div className="flex flex-col gap-1.5">
              {items.slice(0, 12).map((it: any) => (
                <div key={it.id} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                  <span className={cls('mono text-[10px] uppercase w-14', prioColor(it.priority))}>{it.priority}</span>
                  <span className="flex-1">{it.problem}</span>
                  {it.frequency > 1 && <span className="mono text-[10px] text-warmgray">×{it.frequency}</span>}
                  <span className="mono text-[9px] text-warmgray uppercase">{it.source}</span>
                  <select value={it.status} onChange={(e) => advance(it, e.target.value)}
                    className="bg-obsidian border border-hairline rounded px-1.5 py-0.5 text-[10px] mono">
                    {STATUSES.map((st) => <option key={st} value={st}>{st}</option>)}
                  </select>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <div className="grid grid-cols-2 gap-3">
          {/* Feedback friction */}
          <Panel title="Top Friction Points">
            {friction.loading ? <Loading /> : fric.length === 0 ? (
              <EmptyState message="No friction captured." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {fric.slice(0, 8).map((f: any) => (
                  <div key={f.id} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className="mono text-[9px] text-warmgray uppercase w-14">{f.kind}</span>
                    <span className="flex-1">{f.title}</span>
                    <span className="mono text-[10px] text-gold">×{f.frequency}</span>
                    <Button size="sm" variant="ghost" onClick={() => promoteFriction(f)} disabled={busy}>Promote</Button>
                  </div>
                ))}
              </div>
            )}
            <div className="border-t border-hairline mt-2 pt-2 grid grid-cols-3 gap-2 text-[11px]">
              <div><span className="text-warmgray">Total: </span><span className="mono">{fbs.total ?? 0}</span></div>
              <div><span className="text-warmgray">Open: </span><span className="mono text-gold">{fbs.open ?? 0}</span></div>
              <div><span className="text-warmgray">Resolved: </span><span className="mono text-helgreen">{fbs.resolved ?? 0}</span></div>
            </div>
          </Panel>

          {/* Stability analytics */}
          <Panel title="Stability Analytics">
            <div className="flex flex-col gap-2.5">
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-1">Failure Clusters</div>
                {clus.length === 0 ? (
                  <div className="text-[11px] text-warmgray">No failure clusters.</div>
                ) : (
                  <div className="flex flex-col gap-1">
                    {clus.slice(0, 5).map((c: any) => (
                      <div key={c.signature} className="flex items-center gap-2 text-[11px]">
                        <span className="text-ivory/80">{c.component}</span>
                        <span className="text-warmgray text-[10px] truncate flex-1">{c.sample_error}</span>
                        <span className="mono text-[10px] text-helred">×{c.count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="border-t border-hairline pt-2">
                <div className="mono text-[9px] text-warmgray uppercase mb-1">Agent Reliability</div>
                {ar.length === 0 ? (
                  <div className="text-[11px] text-warmgray">No reliability data.</div>
                ) : (
                  <div className="flex flex-col gap-1">
                    {ar.slice(0, 5).map((r: any) => (
                      <div key={r.name} className="flex items-center gap-2 text-[11px]">
                        <span className="flex-1">{r.name}</span>
                        <span className={cls('mono text-[10px]',
                          r.score >= 0.9 ? 'text-helgreen' : r.score >= 0.6 ? 'text-gold' : 'text-helred')}>
                          {(r.score * 100).toFixed(0)}%
                        </span>
                        <span className="mono text-[9px] text-warmgray">{r.success}/{r.total}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </Page>
  );
}
