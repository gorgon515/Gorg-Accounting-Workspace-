import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function FactorCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Factor Center." />;
  const library = useAsync(() => helios.factors.library(), []);
  const [symbols, setSymbols] = useState('');
  const [factor, setFactor] = useState('value');
  const [ranked, setRanked] = useState<any[] | null>(null);
  const [busy, setBusy] = useState(false);
  const factors: any[] = Array.isArray(library.data) ? library.data : [];

  async function rank() {
    const syms = symbols.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
    if (syms.length === 0) return;
    setBusy(true);
    try {
      const r = await helios.factors.rank({ symbols: syms, factor });
      setRanked(Array.isArray(r) ? r : []);
    } finally { setBusy(false); }
  }

  return (
    <Page title="Factor Center" subtitle="factor library · cross-sectional ranking · persistence">
      <div className="grid gap-3">
        <Panel title="Factor Library">
          {library.loading ? <Loading /> : (
            <div className="grid grid-cols-2 gap-2">
              {factors.map((f: any) => (
                <div key={f.name} className="rounded-lg border border-hairline px-3 py-2">
                  <span className="text-sm capitalize">{f.name}</span>
                  <p className="text-[11px] text-warmgray">{f.description}</p>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Cross-Sectional Ranking">
          <div className="flex gap-2 mb-3">
            <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
              placeholder="Tickers — e.g. AAPL, MSFT, GOOG, NVDA"
              value={symbols} onChange={(e) => setSymbols(e.target.value)} />
            <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
              value={factor} onChange={(e) => setFactor(e.target.value)}>
              {factors.map((f: any) => <option key={f.name} value={f.name}>{f.name}</option>)}
            </select>
            <Button size="sm" variant="gold" onClick={rank} disabled={busy}>{busy ? '…' : 'Rank'}</Button>
          </div>
          {ranked === null ? (
            <p className="text-[12px] text-warmgray">Rank symbols by a factor. Requires price/fundamental data in the Financial Hub.</p>
          ) : ranked.length === 0 ? (
            <EmptyState message="No scores available for those symbols." />
          ) : (
            <div className="grid gap-1.5">
              {ranked.map((r: any) => (
                <div key={r.symbol} className="flex items-center gap-3">
                  <span className="mono text-[11px] w-8 text-warmgray">#{r.rank}</span>
                  <span className="mono text-[11px] w-16">{r.symbol}</span>
                  <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                    <div className={cls('h-full rounded-full', r.score >= 60 ? 'bg-helgreen' : r.score >= 40 ? 'bg-gold' : 'bg-helred')}
                      style={{ width: `${r.score}%` }} />
                  </div>
                  <span className="mono text-[10px] text-warmgray w-10 text-right">{r.score?.toFixed?.(0)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}
