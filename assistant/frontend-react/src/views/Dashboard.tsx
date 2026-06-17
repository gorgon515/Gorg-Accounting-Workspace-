import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { MetricCard, Panel, Timeline, Table, EmptyState } from '../components';
import type { Column } from '../components';
import { fmtMoney, fmtPct, dirColor } from '../lib/format';
import { useNav } from '../router';
import type { Quote, Task } from '../ipc/types';

export function Dashboard() {
  const { navigate } = useNav();
  const cfg = useAsync(() => helios.config(), []);
  const side = useAsync(() => helios.sidecar.status(), [], 15000);
  const cpa = useAsync(() => helios.study.cpa(), []);
  const lang = useAsync(() => helios.language.progress(), []);
  const acct = useAsync(() => helios.accounting.summary(), []);
  const watch = useAsync(() => helios.stocks.watchlistQuotes(), [], 60000);
  const tasks = useAsync(() => helios.productivity.tasks('open'), []);
  const agenda = useAsync(() => helios.google.agenda(), []);
  const mem = useAsync(() => helios.memory.list(), []);
  const roster = useAsync(() => helios.agents.roster(), []);

  const brainReady = cfg.data?.brain?.ready;
  const onlineAgents = roster.data?.filter((a) => a.status === 'online').length ?? 0;
  const movers = (watch.data ?? []).filter((q) => !q.error).slice(0, 5);

  const moverCols: Column<Quote>[] = [
    { key: 's', header: 'Symbol', render: (q) => <span className="text-ivory">{q.symbol}</span> },
    { key: 'p', header: 'Price', align: 'right', render: (q) => fmtMoney(q.price) },
    {
      key: 'c', header: 'Chg%', align: 'right',
      render: (q) => <span className={dirColor(q.change)}>{fmtPct(q.changePercent)}</span>,
    },
  ];

  return (
    <Page title="Home" subtitle="HELIOS Command Center — daily briefing">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Brain" accent value={brainReady ? 'Online' : 'Offline'}
          sub={cfg.data?.brain?.model || '—'} />
        <MetricCard label="Sidecar" value={side.data?.ready ? 'Ready' : 'Offline'}
          sub="quant + accounting" />
        <MetricCard label="Agents online" value={onlineAgents} sub={`${roster.data?.length ?? 0} total`} />
        <MetricCard label="Net (P&L)" accent value={fmtMoney(acct.data?.net)} sub="this period" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="CPA overall" value={cpa.data ? `${cpa.data.overallProgress}%` : '—'} sub="Becker" />
        <MetricCard label={lang.data ? `${lang.data.flag} ${lang.data.name}` : 'Language'}
          value={lang.data ? `~${lang.data.estimatedLevel}` : '—'}
          sub={lang.data ? `${lang.data.words} words · ${lang.data.streakDays}d streak` : ''} />
        <MetricCard label="Cash" value={fmtMoney(acct.data?.cash)} sub="position" />
        <MetricCard label="Receivable" value={fmtMoney(acct.data?.receivable)} sub="outstanding" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Today's schedule" subtitle="Google Calendar" className="min-h-[180px]"
          actions={<button className="mono text-[10px] text-gold" onClick={() => navigate('calendar')}>open ↗</button>}>
          <Timeline
            empty={agenda.error ? 'Connect Google in the desktop app.' : 'No events today.'}
            items={(agenda.data?.events ?? []).slice(0, 6).map((e: any) => ({
              title: e.summary || e.title || 'Event',
              time: e.time || e.start || '',
            }))}
          />
        </Panel>

        <Panel title="Market summary" subtitle="watchlist movers" className="min-h-[180px]"
          actions={<button className="mono text-[10px] text-gold" onClick={() => navigate('markets')}>open ↗</button>}>
          <Table columns={moverCols} rows={movers} empty={watch.error ? 'Market data offline.' : 'No watchlist.'} />
        </Panel>

        <Panel title="Open tasks" className="min-h-[160px]"
          actions={<button className="mono text-[10px] text-gold" onClick={() => navigate('calendar')}>plan ↗</button>}>
          {(tasks.data ?? []).length ? (
            <ul className="flex flex-col gap-1.5">
              {(tasks.data as Task[]).slice(0, 6).map((t) => (
                <li key={t.id} className="flex items-center gap-2 text-[12px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-gold/70" />
                  <span className="flex-1 truncate">{t.title || t.text}</span>
                  {t.due && <span className="mono text-[10px] text-warmgray">{t.due}</span>}
                </li>
              ))}
            </ul>
          ) : <EmptyState message="No open tasks." />}
        </Panel>

        <Panel title="Recent memories" className="min-h-[160px]"
          actions={<button className="mono text-[10px] text-gold" onClick={() => navigate('memory')}>open ↗</button>}>
          {(mem.data ?? []).length ? (
            <ul className="flex flex-col gap-1.5">
              {(mem.data ?? []).slice(0, 5).map((m) => (
                <li key={m.id} className="text-[12px] text-ivory/90 flex gap-2">
                  <span className="mono text-[9px] text-gold uppercase shrink-0 mt-0.5">{m.category}</span>
                  <span className="truncate">{m.fact}</span>
                </li>
              ))}
            </ul>
          ) : <EmptyState message={mem.error ? 'Live in the desktop app.' : 'No memories yet.'} />}
        </Panel>
      </div>
    </Page>
  );
}
