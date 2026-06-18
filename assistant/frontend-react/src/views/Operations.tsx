import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Approvals', 'Month-End Close', 'Outcomes'] as const;
type Tab = typeof TABS[number];
const TIER = ['', 'low', 'moderate', 'high', 'critical'];

export function Operations() {
  const [tab, setTab] = useState<Tab>('Approvals');
  return (
    <Page title="Operations" subtitle="execution engine · approvals · close · learning"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>)}
        </div>
      }>
      {tab === 'Approvals' && <Approvals />}
      {tab === 'Month-End Close' && <Close />}
      {tab === 'Outcomes' && <Outcomes />}
    </Page>
  );
}

function Approvals() {
  const actions = useAsync(() => helios.sidecar.execActions(), [], 5000);
  const list = actions.data?.actions ?? [];
  async function approve(a: any) {
    await helios.sidecar.execApprove({ id: a.id, confirm: a.tier === 4 });
    await helios.sidecar.execExecute(a.id);
    actions.reload();
  }
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Proposed" accent value={list.filter((a: any) => a.status === 'proposed').length} />
        <MetricCard label="Executed" value={list.filter((a: any) => a.status === 'executed').length} />
        <MetricCard label="Failed" value={list.filter((a: any) => a.status === 'failed').length} />
        <MetricCard label="Total" value={list.length} />
      </div>
      <Panel title="Action queue" subtitle="HELIOS proposes — you approve. Tier 4 prepares only." scroll className="max-h-[520px]">
        {actions.loading ? <Loading /> : !list.length ? <EmptyState message="No actions. The brain proposes drafts here for your approval." /> : (
          <ul className="flex flex-col gap-1.5">
            {list.map((a: any) => (
              <li key={a.id} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className={cls('mono text-[9px] uppercase px-1.5 py-0.5 rounded border',
                    a.tier >= 4 ? 'text-helred border-helred/40' : a.tier === 3 ? 'text-gold border-gold/40' : 'text-warmgray border-hairline')}>
                    T{a.tier} {TIER[a.tier]}
                  </span>
                  <span className="text-[12px] flex-1">{a.type}</span>
                  <StatusBadge status={a.status === 'executed' ? 'ready' : a.status === 'failed' ? 'error' : 'idle'} label={a.status} />
                </div>
                {a.status === 'proposed' && (
                  <div className="flex gap-2 mt-1.5">
                    <Button size="sm" variant="gold" onClick={() => approve(a)}>
                      {a.tier === 4 ? 'Confirm & prepare' : 'Approve & execute'}
                    </Button>
                    <Button size="sm" onClick={async () => { await helios.sidecar.execReject({ id: a.id }); actions.reload(); }}>Reject</Button>
                  </div>
                )}
                {a.status === 'executed' && a.result?.entry_id && (
                  <Button size="sm" className="mt-1.5" onClick={async () => { await helios.sidecar.execRollback(a.id); actions.reload(); }}>Roll back</Button>
                )}
                {a.error && <div className="text-helred text-[11px] mt-1">{a.error}</div>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}

function Close() {
  const dash = useAsync(() => helios.sidecar.closeDashboard(), []);
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const periods = dash.data?.periods ?? [];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Month-end close" actions={<Button size="sm" variant="gold" onClick={async () => { await helios.sidecar.closeStart(period); dash.reload(); }}>Start {period}</Button>}>
        <input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="YYYY-MM"
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono mb-3" />
        {dash.loading ? <Loading /> : !periods.length ? <EmptyState message="No close started. Pick a period and Start." /> : (
          periods.map((p: any) => (
            <div key={p.period} className="mb-3">
              <div className="flex justify-between text-[12px] mb-1">
                <span className="mono text-gold">{p.period}</span>
                <span>{p.progress}% · {p.ready_to_close ? 'ready ✓' : p.status}</span>
              </div>
              <div className="h-1.5 rounded bg-obsidian overflow-hidden mb-2"><div className="h-full bg-gold" style={{ width: `${p.progress}%` }} /></div>
              {p.checklist.map((it: any) => (
                <button key={it.key} onClick={async () => { await helios.sidecar.closeUpdate({ period: p.period, key: it.key, status: it.status === 'done' ? 'pending' : 'done' }); dash.reload(); }}
                  className="flex items-center gap-2 w-full text-left text-[12px] py-1">
                  <span className={cls('w-4 h-4 rounded border text-[9px] flex items-center justify-center', it.status === 'done' ? 'border-helgreen text-helgreen' : 'border-hairline')}>{it.status === 'done' ? '✓' : ''}</span>
                  <span className={it.status === 'done' ? 'line-through opacity-60' : ''}>{it.label}</span>
                </button>
              ))}
            </div>
          ))
        )}
      </Panel>
      <Panel title="How it works">
        <p className="text-[12px] text-warmgray leading-relaxed">
          The close checklist tracks journal entries, accruals, prepaids, depreciation, reconciliations,
          review, closing entries, and statements. When complete, HELIOS assembles a close package
          (trial balance + balance sheet + income statement + cash flow) from the live books. Posting
          entries during close still flows through the approval queue.
        </p>
      </Panel>
    </div>
  );
}

function Outcomes() {
  const m = useAsync(() => helios.sidecar.outcomesMetrics(), []);
  const d = m.data;
  return m.loading ? <Loading /> : !d ? <EmptyState message="No outcomes recorded yet." /> : (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Recommendations" value={d.recommendations} />
        <MetricCard label="Outcomes recorded" value={d.outcomes_recorded} />
        <MetricCard label="Completion" value={`${Math.round((d.completion_rate || 0) * 100)}%`} />
        <MetricCard label="Accuracy" accent value={d.overall_accuracy != null ? `${Math.round(d.overall_accuracy * 100)}%` : '—'} />
      </div>
      <Panel title="Agent performance & learning feedback">
        {!(d.by_agent?.length) ? <EmptyState message="Record recommendation outcomes to build calibration." /> : (
          <table className="w-full text-[12px]">
            <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Agent</th><th className="text-right">Recs</th><th className="text-right">Accuracy</th><th className="text-right">Avg conf</th><th className="text-right">Calibration</th></tr></thead>
            <tbody>
              {d.by_agent.map((a: any) => (
                <tr key={a.agent} className="border-t border-hairline">
                  <td className="py-1">{a.agent}</td>
                  <td className="text-right">{a.recommendations}</td>
                  <td className="text-right">{a.accuracy != null ? `${Math.round(a.accuracy * 100)}%` : '—'}</td>
                  <td className="text-right">{a.avg_confidence != null ? `${Math.round(a.avg_confidence * 100)}%` : '—'}</td>
                  <td className={cls('text-right', (a.suggested_confidence_adjustment || 0) < 0 ? 'text-helred' : 'text-helgreen')}>
                    {a.suggested_confidence_adjustment != null ? a.suggested_confidence_adjustment : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}
