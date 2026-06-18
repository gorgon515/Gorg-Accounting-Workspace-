import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function OpportunityCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for opportunities." />;
  const opps = useAsync(() => helios.intelligence.listOpportunities({ status: 'open' }), []);
  const list: any[] = opps.data?.opportunities ?? [];

  async function scan() {
    await helios.intelligence.scanOpportunities();
    opps.reload();
  }

  async function action(id: string) {
    await helios.intelligence.setOpportunityStatus(id, 'actioned');
    opps.reload();
  }

  const avgScore = list.length ? Math.round(list.reduce((s, o) => s + o.score, 0) / list.length) : 0;

  return (
    <Page
      title="Opportunity Center"
      subtitle="cross-domain opportunity detection"
      actions={<Button size="sm" variant="gold" onClick={scan}>Re-scan</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-3 gap-3">
          <MetricCard label="Open Opportunities" value={list.length} accent />
          <MetricCard label="Avg Score" value={avgScore} />
          <MetricCard label="Top Score" value={list[0] ? Math.round(list[0].score) : 0} />
        </div>
        {opps.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No open opportunities. Run a scan to detect them." />
        ) : (
          <div className="grid gap-2">
            {list.map((o) => (
              <Panel key={o.id} title={o.title} subtitle={`${o.domain} · score ${Math.round(o.score)}`}
                actions={<Button size="sm" onClick={() => action(o.id)}>Mark Actioned</Button>}>
                <p className="text-[12px] text-warmgray">{o.description}</p>
                <div className="flex flex-wrap gap-4 mt-2 mono text-[11px]">
                  <span>impact <span className="text-gold">{Math.round((o.expected_impact ?? 0) * 100)}%</span></span>
                  <span>effort <span className="text-warmgray">{Math.round((o.required_effort ?? 0) * 100)}%</span></span>
                  <span>confidence <span className="text-helgreen">{Math.round((o.confidence ?? 0) * 100)}%</span></span>
                </div>
                <ScoreBar score={o.score} />
              </Panel>
            ))}
          </div>
        )}
      </div>
    </Page>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="mt-2 h-1.5 rounded-full bg-ivory/10 overflow-hidden">
      <div className={cls('h-full rounded-full', score >= 60 ? 'bg-helgreen' : score >= 30 ? 'bg-gold' : 'bg-warmgray')}
        style={{ width: `${Math.min(score, 100)}%` }} />
    </div>
  );
}
