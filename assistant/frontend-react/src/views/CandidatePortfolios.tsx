import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Candidate Portfolios — assemble advisory model portfolios in five styles from
// the discovered universe. Nothing trades; these are starting points.
export function CandidatePortfolios() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Candidate Portfolios." />;
  const styles = useAsync(() => helios.discovery.portfolios(), []);
  const [style, setStyle] = useState('conservative');
  const [size, setSize] = useState(10);
  const [built, setBuilt] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const styleList: any[] = Array.isArray(styles.data) ? styles.data : (styles.data?.styles ?? []);

  async function build() {
    setBusy(true);
    try { setBuilt(await helios.discovery.buildPortfolio({ style, size })); }
    finally { setBusy(false); }
  }

  const holdings: any[] = built?.holdings ?? [];

  return (
    <Page title="Candidate Portfolios" subtitle="conservative · growth · value · dividend · small-cap — all advisory">
      <div className="grid gap-3">
        <Panel title="Build a Candidate">
          <div className="flex flex-wrap gap-1.5 mb-3">
            {(styleList.length ? styleList : DEFAULT_STYLES).map((s: any) => {
              const id = s.id ?? s;
              return (
                <button key={id} onClick={() => setStyle(id)}
                  className={cls('px-2.5 py-1.5 rounded border text-[11px] mono capitalize transition-colors',
                    style === id ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
                  {(s.name ?? id).replace(/_/g, ' ')}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2">
            <span className="mono text-[10px] text-warmgray">Holdings</span>
            {[5, 10, 15, 20].map((n) => (
              <button key={n} onClick={() => setSize(n)}
                className={cls('px-2 py-0.5 rounded border text-[10px] mono',
                  size === n ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>{n}</button>
            ))}
            <Button size="sm" variant="gold" onClick={build} disabled={busy} className="ml-auto">
              {busy ? 'Building…' : 'Build Portfolio'}
            </Button>
          </div>
        </Panel>

        {built && (
          <Panel title={`${(built.style ?? style).replace(/_/g, ' ')} portfolio`} subtitle={built.notes}>
            {holdings.length === 0 ? <EmptyState message="No holdings produced." /> : (
              <div className="grid gap-1.5">
                {holdings.map((h: any) => (
                  <div key={h.symbol} className="flex items-center gap-2">
                    <span className="mono text-[12px] w-16">{h.symbol}</span>
                    <span className="text-[12px] w-36 truncate text-warmgray">{h.name}</span>
                    <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                      <div className="h-full rounded-full bg-gold" style={{ width: `${(h.weight ?? 0) * 100}%` }} />
                    </div>
                    <span className="mono text-[10px] text-gold w-12 text-right">{((h.weight ?? 0) * 100).toFixed(1)}%</span>
                  </div>
                ))}
                <div className="mt-2 pt-2 border-t border-hairline grid gap-1">
                  {holdings.filter((h) => h.reason).slice(0, 8).map((h: any) => (
                    <div key={h.symbol} className="flex gap-2 text-[10px] text-warmgray">
                      <span className="mono w-16">{h.symbol}</span><span className="flex-1">{h.reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Panel>
        )}
      </div>
    </Page>
  );
}

const DEFAULT_STYLES = [
  { id: 'conservative', name: 'Conservative' }, { id: 'growth', name: 'Growth' },
  { id: 'value', name: 'Value' }, { id: 'dividend', name: 'Dividend' }, { id: 'small_cap', name: 'Small Cap' },
];
