import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Table, Chart, StatusBadge, EmptyState, Loading } from '../components';
import type { Column } from '../components';
import { fmtMoney, fmtPct, dirColor } from '../lib/format';
import type { Quote } from '../ipc/types';

export function Markets() {
  const [sym, setSym] = useState<string | null>(null);
  const watch = useAsync(() => helios.stocks.watchlistQuotes(), [], 60000);
  const hist = useAsync(() => (sym ? helios.stocks.history(sym, '6mo') : Promise.resolve(null)), [sym]);
  const analysis = useAsync(() => (sym ? helios.sidecar.analyze({ symbol: sym }) : Promise.resolve(null)), [sym]);
  const quotes = (watch.data ?? []).filter((q) => !q.error);
  const brief = useAsync(
    () => (quotes.length ? helios.sidecar.marketBriefing({ quotes }) : Promise.resolve(null)),
    [watch.data],
  );

  const cols: Column<Quote>[] = [
    { key: 's', header: 'Symbol', render: (q) => <span className="text-ivory font-medium">{q.symbol}</span> },
    { key: 'n', header: 'Name', render: (q) => <span className="text-warmgray truncate">{q.name || ''}</span> },
    { key: 'p', header: 'Price', align: 'right', render: (q) => fmtMoney(q.price) },
    { key: 'c', header: 'Chg%', align: 'right', render: (q) => <span className={dirColor(q.change)}>{fmtPct(q.changePercent)}</span> },
  ];

  const series: number[] = hist.data?.prices ?? hist.data?.points?.map((p: any) => p.close) ?? [];

  const mb = brief.data;

  return (
    <Page title="Market Intelligence" subtitle="watchlist · charts · quant analysis · daily briefing">
      <Panel title="Daily market briefing" subtitle="computed from your watchlist" className="mb-3"
        actions={mb && <span className="mono text-[10px] text-warmgray">tone: {mb.market_overview?.tone}</span>}>
        {!mb ? <EmptyState message={watch.error ? 'Market data offline (desktop app).' : 'Loads from your watchlist.'} /> : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
            <div>
              <div className="mono text-[10px] uppercase text-warmgray mb-1">Overview</div>
              {mb.market_overview?.advancers} up · {mb.market_overview?.decliners} down · avg {mb.market_overview?.avg_change_percent}%
            </div>
            <div>
              <div className="mono text-[10px] uppercase text-warmgray mb-1">Top movers</div>
              {(mb.top_movers?.gainers ?? []).slice(0, 3).map((g: any) => (
                <span key={g.symbol} className="mr-2 text-helgreen">{g.symbol} +{g.change_percent}%</span>
              ))}
            </div>
            <div>
              <div className="mono text-[10px] uppercase text-warmgray mb-1">Research flags</div>
              {(mb.opportunities ?? []).map((o: any) => <div key={o.symbol}>{o.symbol}</div>) || '—'}
            </div>
          </div>
        )}
      </Panel>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Watchlist" subtitle="click a symbol to analyze" scroll className="max-h-[460px]">
          <Table columns={cols} rows={(watch.data ?? []).filter((q) => !q.error)}
            empty={watch.error ? 'Market data offline (desktop app).' : 'No watchlist symbols.'}
            onRow={(q) => setSym(q.symbol)} />
        </Panel>

        <div className="flex flex-col gap-3">
          <Panel title={sym ? `Chart · ${sym}` : 'Chart'} subtitle="6-month close">
            {!sym ? <EmptyState message="Select a symbol." />
              : hist.loading ? <Loading />
              : series.length ? <Chart data={series} height={120} stroke="auto" />
              : <EmptyState message="No price history." />}
          </Panel>

          <Panel title="Quant analysis" subtitle="Intelligence Sidecar">
            {!sym ? <EmptyState message="Select a symbol to run the Quant Research Engine." />
              : analysis.loading ? <Loading />
              : analysis.error ? <EmptyState message="Sidecar offline — start the desktop app." />
              : analysis.data ? (
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <StatusBadge status="ready" label={analysis.data.trend ? `trend ${analysis.data.trend}` : 'analyzed'} />
                    {analysis.data.rsi14 != null && <span className="mono text-[11px] text-warmgray">RSI {analysis.data.rsi14}</span>}
                    {analysis.data.volatility_annualized != null && (
                      <span className="mono text-[11px] text-warmgray">vol {(analysis.data.volatility_annualized * 100).toFixed(1)}%</span>
                    )}
                  </div>
                  <ul className="flex flex-col gap-1">
                    {analysis.data.signals.map((s, i) => (
                      <li key={i} className="text-[12px] text-ivory/90">• {s}</li>
                    ))}
                  </ul>
                </div>
              ) : <EmptyState message="No analysis." />}
          </Panel>
        </div>
      </div>
    </Page>
  );
}
