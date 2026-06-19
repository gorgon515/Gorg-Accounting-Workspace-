import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { bus } from '../lib/eventBus';
import { cls, fmtMoney } from '../lib/format';

export function ExecutiveCommandCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Command Center." />;
  const cc = useAsync(() => helios.executive.commandCenter(), [], 60000);

  if (cc.loading && !cc.data) return <Loading label="Assembling command center…" />;
  const d = cc.data ?? {};
  const fin = d.financials ?? {};
  const goals = d.goals ?? {};
  const risks: any[] = d.risks ?? [];
  const opps: any[] = d.opportunities ?? [];
  const recs: any[] = d.recommendations ?? [];
  const health = d.health ?? {};

  return (
    <Page
      title="Executive Command Center"
      subtitle="priorities · risks · opportunities · forecasts"
      actions={<Button size="sm" variant="primary" onClick={() => cc.reload()}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Net Income" value={fmtMoney(fin.net)} accent />
          <MetricCard label="Active Goals" value={goals.active ?? '—'} sub={`${goals.at_risk ?? 0} at risk`} />
          <MetricCard label="Open Risks" value={d.risk_summary?.open_risks ?? risks.length} />
          <MetricCard label="Pending Proposals" value={d.pending_proposals ?? 0} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="Top Priorities"
            actions={<Button size="sm" onClick={() => bus.emit('navigate', 'strategy')}>Plan</Button>}>
            {recs.length === 0 ? (
              <EmptyState message="No recommendations yet — run the morning briefing." />
            ) : (
              <ul className="grid gap-1.5">
                {recs.map((r, i) => (
                  <li key={i} className="rounded-lg border border-hairline px-3 py-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{r.title}</span>
                      <span className="mono text-[10px] text-gold">{Math.round(r.score)}</span>
                    </div>
                    <p className="text-[11px] text-warmgray mt-0.5">{r.rationale}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Emerging Risks"
            actions={<Button size="sm" onClick={() => bus.emit('navigate', 'risks')}>View all</Button>}>
            {risks.length === 0 ? (
              <EmptyState message="No open risks detected." />
            ) : (
              <ul className="grid gap-1.5">
                {risks.map((r) => (
                  <li key={r.id} className="flex items-center justify-between rounded-lg border border-hairline px-3 py-2">
                    <span className="text-sm">{r.title}</span>
                    <span className={cls('mono text-[10px] uppercase',
                      r.severity === 'critical' || r.severity === 'high' ? 'text-helred' : 'text-gold')}>
                      {r.severity}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Opportunities"
            actions={<Button size="sm" onClick={() => bus.emit('navigate', 'opportunities')}>View all</Button>}>
            {opps.length === 0 ? (
              <EmptyState message="No opportunities detected." />
            ) : (
              <ul className="grid gap-1.5">
                {opps.map((o) => (
                  <li key={o.id} className="flex items-center justify-between rounded-lg border border-hairline px-3 py-2">
                    <span className="text-sm">{o.title}</span>
                    <span className="mono text-[10px] text-helgreen">{Math.round(o.score)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Forecast & Health"
            actions={<Button size="sm" onClick={() => bus.emit('navigate', 'forecast')}>Forecasts</Button>}>
            <div className="grid gap-2">
              <div className="rounded-lg border border-hairline px-3 py-2">
                <div className="mono text-[10px] uppercase text-warmgray">12-Month Cash Flow (expected)</div>
                <div className="text-lg font-light text-gold">{fmtMoney(d.forecast?.expected_ending)}</div>
                <div className="mono text-[10px] text-warmgray">confidence {Math.round((d.forecast?.confidence ?? 0) * 100)}%</div>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-hairline px-3 py-2">
                <span className="text-sm">System Health</span>
                <span className={cls('mono text-[11px] uppercase',
                  health.status === 'healthy' ? 'text-helgreen' :
                  health.status === 'critical' ? 'text-helred' : 'text-gold')}>
                  {health.status ?? 'unknown'}
                </span>
              </div>
            </div>
          </Panel>
        </div>

        <Panel title="Autonomous Proposal Loop">
          <div className="flex items-center justify-between">
            <p className="text-[12px] text-warmgray">
              Run the morning scan to generate a strategic briefing and draft actions.
              All drafts enter the approval queue — nothing executes automatically.
            </p>
            <Button variant="gold" size="sm" onClick={() => bus.emit('navigate', 'strategy')}>Open Planning</Button>
          </div>
        </Panel>
      </div>
    </Page>
  );
}
