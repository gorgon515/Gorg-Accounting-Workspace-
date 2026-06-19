import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, EmptyState, Loading } from '../components';

export function CPACenter() {
  const cpa = useAsync(() => helios.study.cpa(), []);
  const stats = useAsync(() => helios.study.stats(), []);

  return (
    <Page title="CPA Center" subtitle="FAR · REG · AUD · TCP (+ BAR · ISC)">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Overall" accent value={cpa.data ? `${cpa.data.overallProgress}%` : '—'} sub={cpa.data?.provider || 'Becker'} />
        <MetricCard label="Cards due" value={stats.data?.cards?.due ?? '—'} sub={`${stats.data?.cards?.total ?? 0} total`} />
        <MetricCard label="Study streak" value={stats.data?.streakDays ?? '—'} sub="days" />
        <MetricCard label="Minutes" value={stats.data?.totalMinutes ?? '—'} sub="logged" />
      </div>

      <Panel title="Section progress" subtitle="weakness tracking ties to accounting updates">
        {cpa.loading ? <Loading /> : cpa.error ? <EmptyState message="Progress lives in the desktop app." />
          : (cpa.data?.sections ?? []).map((s) => (
            <div key={s.section} className="flex items-center gap-3 mb-2.5">
              <span className="mono text-[12px] w-12 text-gold">{s.section}</span>
              <div className="flex-1 h-2 rounded-full bg-obsidian overflow-hidden border border-hairline">
                <div className="h-full bg-gradient-to-r from-gold/60 to-gold" style={{ width: `${s.progress}%` }} />
              </div>
              <span className="mono text-[11px] text-warmgray w-10 text-right">{s.progress}%</span>
              <span className="text-[10px] text-warmgray w-20 truncate">{s.status}</span>
            </div>
          ))}
        <p className="text-[11px] text-warmgray/70 mt-3">
          Question bank, simulations, and adaptive learning build on this tracker; the Accounting
          Intelligence feed links new ASC updates to the affected exam sections.
        </p>
      </Panel>
    </Page>
  );
}
