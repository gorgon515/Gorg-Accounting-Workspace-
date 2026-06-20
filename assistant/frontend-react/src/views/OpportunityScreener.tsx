import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Opportunity Screener — scan the universe by investing style and inspect the
// signals behind each surfaced name.
export function OpportunityScreener() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Opportunity Screener." />;
  const strategies = useAsync(() => helios.discovery.strategies(), []);
  const [strategy, setStrategy] = useState('value');
  const [limit, setLimit] = useState(25);
  const scan = useAsync(() => helios.discovery.scan(strategy, limit), [strategy, limit]);
  const [open, setOpen] = useState<string | null>(null);

  const stratList: any[] = Array.isArray(strategies.data) ? strategies.data : [];
  const results: any[] = Array.isArray(scan.data) ? scan.data : (scan.data?.results ?? []);
  const current = stratList.find((s) => s.id === strategy);

  return (
    <Page title="Opportunity Screener" subtitle="value · growth · quality · turnaround · compounders · hidden gems">
      <div className="grid gap-3">
        <Panel title="Scan Strategy">
          <div className="flex flex-wrap gap-1.5">
            {stratList.map((s) => (
              <button key={s.id} onClick={() => setStrategy(s.id)}
                className={cls('px-2.5 py-1.5 rounded border text-[11px] mono transition-colors',
                  strategy === s.id ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
                {s.name ?? s.id}
              </button>
            ))}
          </div>
          {current?.description && <p className="text-[11px] text-warmgray mt-2">{current.description}</p>}
          <div className="flex items-center gap-2 mt-3">
            <span className="mono text-[10px] text-warmgray">Show</span>
            {[10, 25, 50, 100].map((n) => (
              <button key={n} onClick={() => setLimit(n)}
                className={cls('px-2 py-0.5 rounded border text-[10px] mono',
                  limit === n ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>{n}</button>
            ))}
          </div>
        </Panel>

        <Panel title={`Results — ${current?.name ?? strategy}`} subtitle={`${results.length} names`}>
          {scan.loading ? <Loading /> : results.length === 0 ? (
            <EmptyState message="No matches. Refresh the universe in the Discovery Center." />
          ) : (
            <div className="grid gap-1.5">
              {results.map((r: any, n: number) => (
                <div key={r.symbol}>
                  <div className="flex items-center gap-2 px-2 py-1.5 rounded border border-hairline cursor-pointer hover:bg-ivory/5"
                    onClick={() => setOpen(open === r.symbol ? null : r.symbol)}>
                    <span className="mono text-[10px] text-warmgray w-5">{n + 1}</span>
                    <span className="mono text-[12px] w-16">{r.symbol}</span>
                    <span className="flex-1 text-[12px] truncate text-warmgray">{r.name}</span>
                    <div className="w-28 h-1.5 rounded-full bg-ivory/10 overflow-hidden">
                      <div className="h-full bg-gold" style={{ width: `${Math.min(100, r.score ?? 0)}%` }} />
                    </div>
                    <span className="mono text-[11px] text-gold w-10 text-right">{fmtNum(r.score)}</span>
                  </div>
                  {open === r.symbol && (
                    <div className="px-3 py-2 ml-7 mb-1 rounded border border-hairline/60 bg-obsidian/40">
                      {r.rationale && <p className="text-[11px] text-ivory/80 mb-2">{r.rationale}</p>}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5">
                        {Object.entries(r.signals ?? {}).map(([k, v]: any) => (
                          <div key={k} className="flex items-center justify-between text-[10px] px-1.5 py-1 rounded bg-ivory/5">
                            <span className="text-warmgray capitalize">{k.replace(/_/g, ' ')}</span>
                            <span className="mono text-gold">{fmtNum(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function fmtNum(v: any): string {
  return typeof v === 'number' ? v.toFixed(1) : '—';
}
