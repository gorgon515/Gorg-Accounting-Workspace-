import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Signals', 'Fusion', 'Agents', 'Approvals'] as const;
type Tab = typeof TABS[number];

export function SignalsDashboard() {
  const [tab, setTab] = useState<Tab>('Signals');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Signals Dashboard." />;
  return (
    <Page
      title="Signals Dashboard"
      subtitle="market signals · intelligence fusion · agent operations"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Signals' && <MarketSignalsTab />}
      {tab === 'Fusion' && <FusionTab />}
      {tab === 'Agents' && <AgentsTab />}
      {tab === 'Approvals' && <ApprovalsTab />}
    </Page>
  );
}

function MarketSignalsTab() {
  const signals = useAsync(() => helios.marketIntel.signals({ status: 'active' }), []);
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(signals.data) ? signals.data : [];

  async function detect() {
    setBusy(true);
    try { await helios.marketIntel.detectSignals(); signals.reload(); }
    finally { setBusy(false); }
  }

  return (
    <Panel title="Market Signals"
      subtitle="momentum, macro shifts, volume — detected from the Financial Data Hub"
      actions={<Button size="sm" variant="gold" onClick={detect} disabled={busy}>{busy ? 'Detecting…' : 'Detect Signals'}</Button>}
    >
      {signals.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No active signals. Detect signals after populating prices/economic data." />
      ) : (
        <div className="grid gap-2">
          {list.map((s: any) => (
            <div key={s.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <DirectionArrow direction={s.direction} />
                  <span className="text-sm truncate">{s.title}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StrengthBar value={s.strength ?? 0.5} />
                  <Button size="sm" variant="ghost" onClick={() => helios.marketIntel.dismissSignal(s.id).then(() => signals.reload())}>✕</Button>
                </div>
              </div>
              {s.description && <p className="text-[11px] text-warmgray mt-0.5">{s.description}</p>}
              <span className="mono text-[10px] text-gold">{s.signal_type} · {s.timeframe}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function FusionTab() {
  const events = useAsync(() => helios.fusion.events({ status: 'new' }), []);
  const rules = useAsync(() => helios.fusion.rules(), []);
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(events.data) ? events.data : [];
  const ruleList: any[] = Array.isArray(rules.data) ? rules.data : [];

  async function run() {
    setBusy(true);
    try { await helios.fusion.run(); events.reload(); rules.reload(); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-3">
      <Panel title="Intelligence Fusion"
        subtitle="cross-source correlation → risk alerts & advisory opportunities"
        actions={<Button size="sm" variant="gold" onClick={run} disabled={busy}>{busy ? 'Running…' : 'Run Fusion'}</Button>}
      >
        {events.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No fusion events. Run fusion after intelligence items accumulate across domains." />
        ) : (
          <div className="grid gap-2">
            {list.map((e: any) => (
              <div key={e.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm">{e.title}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="mono text-[10px] text-gold">{Math.round((e.confidence ?? 0) * 100)}%</span>
                    <Button size="sm" onClick={() => helios.fusion.acknowledgeEvent(e.id).then(() => events.reload())}>Ack</Button>
                  </div>
                </div>
                {e.description && <p className="text-[11px] text-warmgray mt-0.5">{e.description}</p>}
                {e.draft_action && <p className="text-[11px] text-helgreen mt-1">{e.draft_action}</p>}
                <span className="mono text-[10px] text-warmgray">{e.pattern} · {e.action_type}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Fusion Rules">
        <div className="grid gap-1.5">
          {ruleList.map((r: any) => (
            <div key={r.id} className="flex items-center justify-between text-[12px]">
              <span>{r.name}</span>
              <span className="mono text-[10px] text-warmgray">{r.pattern} · ×{r.triggered_count ?? 0}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

const AGENTS = [
  { id: 'market', name: 'Market Intelligence' },
  { id: 'economic', name: 'Economic Intelligence' },
  { id: 'regulatory', name: 'Regulatory Intelligence' },
  { id: 'research', name: 'Research Operations' },
  { id: 'connector', name: 'Connector Operations' },
  { id: 'event', name: 'Event Detection' },
];

function AgentsTab() {
  const stats = useAsync(() => helios.workforceAgents.stats(), []);
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, any>>({});
  const s = stats.data ?? {};

  async function run(id: string) {
    setRunning((r) => ({ ...r, [id]: true }));
    try {
      const res = await helios.workforceAgents.run(id);
      setResults((x) => ({ ...x, [id]: res }));
      stats.reload();
    } finally {
      setRunning((r) => ({ ...r, [id]: false }));
    }
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Completed Runs" value={s.completed_runs ?? 0} accent />
        <MetricCard label="Errors" value={s.error_runs ?? 0} />
        <MetricCard label="Pending Approvals" value={s.pending_approvals ?? 0} />
        <MetricCard label="Approved Actions" value={s.approved_actions ?? 0} />
      </div>
      <Panel title="Workforce Agents" subtitle="each agent proposes — humans approve high-impact actions">
        <div className="grid gap-2">
          {AGENTS.map((a) => {
            const res = results[a.id];
            return (
              <div key={a.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{a.name} Agent</span>
                  <Button size="sm" onClick={() => run(a.id)} disabled={running[a.id]}>
                    {running[a.id] ? 'Running…' : 'Run'}
                  </Button>
                </div>
                {res && (
                  <p className="mono text-[10px] text-warmgray mt-1">
                    {res.summary} {res.error ? `· error: ${res.error}` : ''}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}

function ApprovalsTab() {
  const approvals = useAsync(() => helios.workforceAgents.pendingApprovals(), [], 20000);
  const list: any[] = Array.isArray(approvals.data) ? approvals.data : [];
  return (
    <Panel title="Approval Queue" subtitle="agent-proposed actions awaiting human decision">
      {approvals.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No pending approvals. Agent-proposed high-impact actions appear here." />
      ) : (
        <div className="grid gap-2">
          {list.map((a: any) => (
            <div key={a.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <span className="text-sm truncate">{a.title}</span>
                  <p className="mono text-[10px] text-warmgray">{a.agent_id} · {a.action_type}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Button size="sm" variant="gold" onClick={() => helios.workforceAgents.approve(a.id).then(() => approvals.reload())}>Approve</Button>
                  <Button size="sm" variant="danger" onClick={() => helios.workforceAgents.reject(a.id).then(() => approvals.reload())}>Reject</Button>
                </div>
              </div>
              {a.description && <p className="text-[11px] text-warmgray mt-1">{a.description}</p>}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function DirectionArrow({ direction }: { direction: string }) {
  if (direction === 'up') return <span className="text-helgreen">▲</span>;
  if (direction === 'down') return <span className="text-helred">▼</span>;
  return <span className="text-warmgray">●</span>;
}

function StrengthBar({ value }: { value: number }) {
  const pct = Math.min(value * 100, 100);
  return (
    <div className="w-16 h-1.5 rounded-full bg-ivory/10 overflow-hidden">
      <div className={cls('h-full rounded-full', pct >= 70 ? 'bg-gold' : 'bg-helgreen')} style={{ width: `${pct}%` }} />
    </div>
  );
}
