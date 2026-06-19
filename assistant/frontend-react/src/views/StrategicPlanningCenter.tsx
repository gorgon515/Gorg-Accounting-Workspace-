import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Strategy', 'Proposals', 'Advisory'] as const;
type Tab = typeof TABS[number];

export function StrategicPlanningCenter() {
  const [tab, setTab] = useState<Tab>('Strategy');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for strategic planning." />;
  return (
    <Page
      title="Strategic Planning Center"
      subtitle="recommendations · proposal loop · advisory"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Strategy' && <StrategyTab />}
      {tab === 'Proposals' && <ProposalsTab />}
      {tab === 'Advisory' && <AdvisoryTab />}
    </Page>
  );
}

function StrategyTab() {
  const rec = useAsync(() => helios.reasoning.recommend(), []);
  if (rec.loading) return <Loading />;
  const d = rec.data ?? {};
  const recs: any[] = d.recommendations ?? [];
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Recommendations" value={recs.length} accent />
        <MetricCard label="Opportunities" value={d.opportunity_count ?? 0} />
        <MetricCard label="Risks" value={d.risk_count ?? 0} />
      </div>
      <Panel title="Strategic Summary">
        <p className="text-[12px] text-warmgray">{d.summary ?? '—'}</p>
      </Panel>
      <Panel title="Risk-Adjusted Recommendations">
        {recs.length === 0 ? (
          <EmptyState message="No recommendations available." />
        ) : (
          <ul className="grid gap-1.5">
            {recs.map((r, i) => (
              <li key={i} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{r.title}</span>
                  <span className={cls('mono text-[10px] uppercase',
                    r.type === 'risk_mitigation' ? 'text-helred' : 'text-helgreen')}>
                    {r.type === 'risk_mitigation' ? 'risk' : 'opportunity'} · {Math.round(r.score)}
                  </span>
                </div>
                <p className="text-[11px] text-warmgray mt-0.5">{r.rationale}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function ProposalsTab() {
  const proposals = useAsync(() => helios.reasoning.listProposals('pending'), []);
  const stats = useAsync(() => helios.reasoning.proposalStats(), []);
  const [running, setRunning] = useState(false);
  const [briefing, setBriefing] = useState<string | null>(null);

  const list: any[] = proposals.data?.proposals ?? [];

  async function runLoop() {
    setRunning(true);
    try {
      const res = await helios.reasoning.runProposals();
      setBriefing(res?.briefing ?? null);
      proposals.reload();
      stats.reload();
    } finally {
      setRunning(false);
    }
  }

  async function decide(id: string, decision: string) {
    await helios.reasoning.decideProposal(id, decision);
    proposals.reload();
    stats.reload();
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-2 gap-3 flex-1 mr-3">
          <MetricCard label="Pending" value={stats.data?.pending ?? list.length} accent />
          <MetricCard label="Total Decided"
            value={Object.entries(stats.data?.by_status ?? {}).filter(([k]) => k !== 'pending').reduce((s, [, v]) => s + (v as number), 0)} />
        </div>
        <Button variant="gold" size="sm" onClick={runLoop} disabled={running}>
          {running ? 'Scanning…' : 'Run Morning Briefing'}
        </Button>
      </div>

      {briefing && (
        <Panel title="Daily Strategic Briefing">
          <pre className="mono text-[11px] text-warmgray whitespace-pre-wrap">{briefing}</pre>
        </Panel>
      )}

      <Panel title="Approval Queue" subtitle="nothing executes automatically above Tier 1">
        {proposals.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No pending proposals. Run the morning briefing to generate drafts." />
        ) : (
          <div className="grid gap-2">
            {list.map((p) => (
              <div key={p.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{p.title}</span>
                  <div className="flex items-center gap-2">
                    <span className="mono text-[10px] uppercase text-warmgray">{p.kind} · T{p.tier}</span>
                    <Button size="sm" variant="primary" onClick={() => decide(p.id, 'approved')}>Approve</Button>
                    <Button size="sm" variant="danger" onClick={() => decide(p.id, 'rejected')}>Reject</Button>
                  </div>
                </div>
                <p className="text-[12px] text-warmgray mt-1">{p.detail}</p>
                <p className="mono text-[10px] text-warmgray mt-0.5">{p.rationale}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function AdvisoryTab() {
  const [horizon, setHorizon] = useState('weekly');
  const personal = useAsync(() => helios.advisory.personalRecommendations(horizon), [horizon]);
  const business = useAsync(() => helios.advisory.executiveReport(), []);

  const recs: string[] = personal.data?.recommendations ?? [];
  const biz = business.data ?? {};

  return (
    <div className="grid gap-3">
      <Panel
        title="Personal Advisory"
        actions={
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={horizon} onChange={(e) => setHorizon(e.target.value)}>
            {['weekly', 'monthly', 'quarterly', 'annual'].map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        }
      >
        {personal.loading ? <Loading /> : (
          <ul className="grid gap-1">
            {recs.map((r, i) => <li key={i} className="text-[12px] text-ivory/90">• {r}</li>)}
          </ul>
        )}
      </Panel>
      <Panel title="Business Advisory — Executive Report">
        {business.loading ? <Loading /> : (
          <div className="grid gap-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard label="Profit Margin" value={`${biz.analysis?.profit_margin_pct ?? 0}%`} accent />
              <MetricCard label="Health" value={<span className="capitalize">{biz.analysis?.health ?? '—'}</span>} />
              <MetricCard label="AR Ratio" value={`${biz.analysis?.ar_ratio_pct ?? 0}%`} />
              <MetricCard label="Workload" value={biz.analysis?.workload_pending ?? 0} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <div className="mono text-[10px] uppercase text-warmgray mb-1">Growth Recommendations</div>
                <ul className="grid gap-1">
                  {(biz.growth_recommendations ?? []).map((r: string, i: number) => (
                    <li key={i} className="text-[12px] text-helgreen">↗ {r}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="mono text-[10px] uppercase text-warmgray mb-1">Operational Recommendations</div>
                <ul className="grid gap-1">
                  {(biz.operational_recommendations ?? []).map((r: string, i: number) => (
                    <li key={i} className="text-[12px] text-ivory/90">• {r}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
