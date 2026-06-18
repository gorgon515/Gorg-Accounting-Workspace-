import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Dashboard', 'Accuracy', 'Priorities'] as const;
type Tab = typeof TABS[number];

const TREND_COLOR: Record<string, string> = {
  improving: 'text-helgreen',
  declining: 'text-helred',
  stable: 'text-warmgray',
  insufficient_data: 'text-warmgray',
};

export function LearningCenter() {
  const [tab, setTab] = useState<Tab>('Dashboard');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Learning Center." />;
  return (
    <Page
      title="Learning Center"
      subtitle="self-improvement · accuracy tracking · knowledge gaps"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Dashboard' && <DashboardTab />}
      {tab === 'Accuracy' && <AccuracyTab />}
      {tab === 'Priorities' && <PrioritiesTab />}
    </Page>
  );
}

function DashboardTab() {
  const dash = useAsync(() => helios.selfImprovement.dashboard(), []);
  const [running, setRunning] = useState(false);
  const [cycleResult, setCycleResult] = useState<any>(null);

  const d = dash.data ?? {};
  const accByKind = d.accuracy_by_kind ?? {};
  const kinds = Object.keys(accByKind);

  async function runCycle() {
    setRunning(true);
    try {
      const res = await helios.selfImprovement.runCycle();
      setCycleResult(res);
      dash.reload();
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Overall Accuracy" value={`${Math.round((d.overall_accuracy ?? 0) * 100)}%`} accent />
        <MetricCard label="Open Opportunities" value={d.open_opportunities ?? 0} />
        <MetricCard label="Training Priorities" value={d.training_priorities ?? 0} />
        <MetricCard label="Learning Cycles" value={d.learning_cycles ?? 0} />
      </div>

      <div className="flex items-center justify-end">
        <Button size="sm" variant="gold" onClick={runCycle} disabled={running}>
          {running ? 'Running Cycle…' : 'Run Learning Cycle'}
        </Button>
      </div>

      {cycleResult && (
        <Panel title="Learning Cycle Results">
          <div className="grid gap-1">
            <p className="text-[12px] text-ivory/90">
              {cycleResult.improvements_proposed ?? 0} improvement opportunities identified
            </p>
            {(cycleResult.opportunities ?? []).map((o: any, i: number) => (
              <p key={i} className="text-[11px] text-gold">↑ {o.description}</p>
            ))}
          </div>
        </Panel>
      )}

      {kinds.length > 0 && (
        <Panel title="Accuracy by Kind">
          <div className="grid gap-2">
            {kinds.map((kind) => {
              const acc = accByKind[kind];
              const pct = Math.round(acc * 100);
              return (
                <div key={kind} className="flex items-center gap-3">
                  <span className="text-[12px] w-32 truncate">{kind}</span>
                  <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                    <div
                      className={cls('h-full rounded-full',
                        pct >= 80 ? 'bg-helgreen' : pct >= 60 ? 'bg-gold' : 'bg-helred')}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <span className={cls('mono text-[10px] w-10 text-right',
                    pct >= 80 ? 'text-helgreen' : pct >= 60 ? 'text-gold' : 'text-helred')}>
                    {pct}%
                  </span>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      <OpportunitiesPanel />
    </div>
  );
}

function OpportunitiesPanel() {
  const opps = useAsync(() => helios.selfImprovement.opportunities('open'), []);
  const list: any[] = opps.data?.opportunities ?? [];
  return (
    <Panel title="Improvement Opportunities">
      {opps.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No improvement opportunities. Run a learning cycle to detect them." />
      ) : (
        <div className="grid gap-2">
          {list.map((o: any) => (
            <div key={o.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <p className="text-[12px] text-ivory/90">{o.description}</p>
                <span className={cls('mono text-[10px] shrink-0',
                  o.priority >= 0.7 ? 'text-helred' : o.priority >= 0.4 ? 'text-gold' : 'text-warmgray')}>
                  p{Math.round(o.priority * 100)}
                </span>
              </div>
              <div className="mono text-[10px] text-warmgray mt-0.5">{o.kind} · {o.domain}</div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function AccuracyTab() {
  const history = useAsync(() => helios.selfImprovement.history(), []);
  const list: any[] = history.data?.records ?? [];

  return (
    <Panel title="Accuracy History">
      {history.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No accuracy records yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Kind</th>
                <th>Domain</th>
                <th>Predicted</th>
                <th>Actual</th>
                <th>Accuracy</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {list.map((r: any) => (
                <tr key={r.id} className="border-t border-hairline">
                  <td className="py-1.5">{r.kind}</td>
                  <td className="text-warmgray">{r.domain}</td>
                  <td className="tabular-nums">{r.predicted?.toFixed(1)}</td>
                  <td className="tabular-nums">{r.actual?.toFixed(1)}</td>
                  <td className={cls('tabular-nums',
                    r.accuracy >= 0.8 ? 'text-helgreen' : r.accuracy >= 0.6 ? 'text-gold' : 'text-helred')}>
                    {Math.round(r.accuracy * 100)}%
                  </td>
                  <td className="mono text-[10px] text-warmgray">{r.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function PrioritiesTab() {
  const priorities = useAsync(() => helios.selfImprovement.priorities(), []);
  const list: any[] = priorities.data?.priorities ?? [];

  return (
    <Panel title="Training Priorities" subtitle="domains and topics that need more knowledge">
      {priorities.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No training priorities. Run a learning cycle to identify gaps." />
      ) : (
        <div className="grid gap-2">
          {list.map((p: any) => (
            <div key={p.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-sm">{p.topic}</span>
                  <div className="mono text-[10px] text-warmgray mt-0.5">{p.domain}</div>
                  {p.reason && <p className="text-[11px] text-warmgray mt-0.5">{p.reason}</p>}
                </div>
                <span className={cls('mono text-[10px] shrink-0',
                  p.priority >= 0.7 ? 'text-helred' : p.priority >= 0.4 ? 'text-gold' : 'text-warmgray')}>
                  p{Math.round(p.priority * 100)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
