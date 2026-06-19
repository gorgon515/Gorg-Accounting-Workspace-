import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function PortfolioLab() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Portfolio Lab." />;
  const methods = useAsync(() => helios.portfolioLab.methods(), []);
  const portfolios = useAsync(() => helios.portfolioLab.list(), []);
  const [name, setName] = useState('');
  const [symbols, setSymbols] = useState('');
  const [method, setMethod] = useState('maximum_sharpe');
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<any>(null);

  const methodList: any[] = Array.isArray(methods.data) ? methods.data : [];
  const list: any[] = Array.isArray(portfolios.data) ? portfolios.data : [];

  async function construct() {
    const syms = symbols.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
    if (!name.trim() || syms.length === 0) return;
    setBusy(true);
    try {
      const pf = await helios.portfolioLab.construct({ name, symbols: syms, method });
      setSelected(pf);
      setName(''); setSymbols('');
      portfolios.reload();
    } finally { setBusy(false); }
  }

  return (
    <Page title="Portfolio Lab" subtitle="portfolio construction · optimization · rebalancing">
      <div className="grid gap-3">
        <Panel title="Construct Portfolio">
          <div className="grid gap-2">
            <div className="flex gap-2">
              <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
                placeholder="Portfolio name" value={name} onChange={(e) => setName(e.target.value)} />
              <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
                value={method} onChange={(e) => setMethod(e.target.value)}>
                {methodList.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
                placeholder="Tickers, comma-separated — e.g. AAPL, MSFT, GOOG"
                value={symbols} onChange={(e) => setSymbols(e.target.value)} />
              <Button size="sm" variant="gold" onClick={construct} disabled={busy || !name.trim()}>
                {busy ? 'Optimizing…' : 'Optimize'}
              </Button>
            </div>
          </div>
        </Panel>

        {selected && <PortfolioDetail pf={selected} onRebalance={() => portfolios.reload()} />}

        <Panel title="Portfolios">
          {portfolios.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No portfolios yet. Construct one above (requires price data in the Financial Hub)." />
          ) : (
            <div className="grid gap-2">
              {list.map((p: any) => (
                <div key={p.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-ivory/5"
                  onClick={() => setSelected(p)}>
                  <div>
                    <span className="text-sm">{p.name}</span>
                    <p className="mono text-[10px] text-warmgray">{p.method} · {(p.symbols ?? []).length} assets</p>
                  </div>
                  <div className="mono text-[10px] text-gold">
                    Sharpe {p.stats?.sharpe?.toFixed?.(2) ?? '—'} · vol {fmtPct(p.stats?.volatility)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function PortfolioDetail({ pf, onRebalance }: { pf: any; onRebalance: () => void }) {
  const [rebal, setRebal] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const weights = pf.weights ?? {};
  const stats = pf.stats ?? {};

  async function propose() {
    setBusy(true);
    try {
      const r = await helios.portfolioLab.rebalance(pf.id);
      setRebal(r);
      onRebalance();
    } finally { setBusy(false); }
  }

  return (
    <Panel title={`${pf.name} — Allocation`}
      subtitle={pf.method}
      actions={<Button size="sm" onClick={propose} disabled={busy}>{busy ? '…' : 'Propose Rebalance'}</Button>}
    >
      <div className="grid grid-cols-4 gap-3 mb-3">
        <MetricCard label="Expected Return" value={fmtPct(stats.expected_return)} accent />
        <MetricCard label="Volatility" value={fmtPct(stats.volatility)} />
        <MetricCard label="Sharpe" value={stats.sharpe?.toFixed?.(2) ?? '—'} />
        <MetricCard label="Eff. N" value={stats.effective_n ?? '—'} />
      </div>
      <div className="grid gap-1.5">
        {Object.entries(weights).sort((a: any, b: any) => b[1] - a[1]).map(([sym, w]: any) => (
          <div key={sym} className="flex items-center gap-2">
            <span className="mono text-[11px] w-16">{sym}</span>
            <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
              <div className="h-full rounded-full bg-gold" style={{ width: `${w * 100}%` }} />
            </div>
            <span className="mono text-[10px] text-warmgray w-12 text-right">{(w * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
      {rebal && rebal.trades && (
        <div className="mt-3 pt-3 border-t border-hairline">
          <p className="mono text-[10px] text-warmgray mb-1">
            Rebalance proposal (advisory) — turnover {fmtPct(rebal.turnover)}, est. cost {fmtPct(rebal.est_cost)}
          </p>
          {rebal.trades.map((t: any) => (
            <div key={t.symbol} className="flex items-center justify-between text-[11px]">
              <span className="mono">{t.symbol}</span>
              <span className={cls('mono', t.action === 'buy' ? 'text-helgreen' : 'text-helred')}>
                {t.action} {fmtPct(Math.abs(t.delta))}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function fmtPct(v: any): string {
  return typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—';
}
