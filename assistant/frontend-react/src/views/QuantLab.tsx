import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';

const TABS = ['Strategies', 'Experiments', 'Hypotheses'] as const;
type Tab = typeof TABS[number];

export function QuantLab() {
  const [tab, setTab] = useState<Tab>('Strategies');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Quant Lab." />;
  return (
    <Page
      title="Quant Lab"
      subtitle="strategy research · experiments · hypothesis tracking"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      <StatsRow />
      {tab === 'Strategies' && <StrategiesTab />}
      {tab === 'Experiments' && <ExperimentsTab />}
      {tab === 'Hypotheses' && <HypothesesTab />}
    </Page>
  );
}

function StatsRow() {
  const stats = useAsync(() => helios.quantLab.stats(), []);
  const s = stats.data ?? {};
  return (
    <div className="grid grid-cols-4 gap-3 mb-3">
      <MetricCard label="Strategies" value={s.strategies ?? 0} accent />
      <MetricCard label="Experiments" value={s.experiments ?? 0} />
      <MetricCard label="Open Hypotheses" value={s.open_hypotheses ?? 0} />
      <MetricCard label="Notebooks" value={s.notebooks ?? 0} />
    </div>
  );
}

function StrategiesTab() {
  const strategies = useAsync(() => helios.quantLab.strategies(), []);
  const [name, setName] = useState('');
  const [kind, setKind] = useState('sma_cross');
  const list: any[] = Array.isArray(strategies.data) ? strategies.data : [];

  async function create() {
    if (!name.trim()) return;
    await helios.quantLab.createStrategy({ name, definition: { kind }, category: 'signal' });
    setName('');
    strategies.reload();
  }

  return (
    <div className="grid gap-3">
      <Panel title="New Strategy">
        <div className="flex gap-2">
          <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
            placeholder="Strategy name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={kind} onChange={(e) => setKind(e.target.value)}>
            {['sma_cross', 'momentum', 'mean_reversion'].map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <Button size="sm" variant="gold" onClick={create} disabled={!name.trim()}>Create</Button>
        </div>
      </Panel>
      <Panel title="Strategies">
        {strategies.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No strategies yet. Create one to begin research." />
        ) : (
          <div className="grid gap-2">
            {list.map((s: any) => (
              <div key={s.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                <div>
                  <span className="text-sm">{s.name}</span>
                  <p className="mono text-[10px] text-warmgray">{s.category} · v{s.version} · {s.definition?.kind}</p>
                </div>
                <span className="mono text-[10px] text-gold">{s.status}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function ExperimentsTab() {
  const experiments = useAsync(() => helios.quantLab.experiments(), []);
  const strategies = useAsync(() => helios.quantLab.strategies(), []);
  const [symbol, setSymbol] = useState('');
  const [kind, setKind] = useState('sma_cross');
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(experiments.data) ? experiments.data : [];

  async function run() {
    if (!symbol.trim()) return;
    setBusy(true);
    try {
      await helios.quantLab.runExperiment({
        name: `${kind} ${symbol}`, symbol: symbol.toUpperCase(),
        definition: { kind, fast: 10, slow: 30, window: 30 },
      });
      experiments.reload();
    } finally { setBusy(false); }
  }

  return (
    <div className="grid gap-3">
      <Panel title="Run Experiment" subtitle="generates signals, backtests, records metrics">
        <div className="flex gap-2">
          <input className="bg-obsidian border border-hairline rounded px-3 py-2 text-sm w-28"
            placeholder="SYMBOL" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={kind} onChange={(e) => setKind(e.target.value)}>
            {['sma_cross', 'momentum', 'mean_reversion'].map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <Button size="sm" variant="gold" onClick={run} disabled={busy || !symbol.trim()}>
            {busy ? 'Running…' : 'Run Backtest'}
          </Button>
        </div>
      </Panel>
      <Panel title="Experiment Results">
        {experiments.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No experiments yet. Run one above (requires price data in the Financial Hub)." />
        ) : (
          <div className="grid gap-2">
            {list.map((e: any) => {
              const m = e.result?.metrics ?? {};
              return (
                <div key={e.id} className="rounded-lg border border-hairline px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{e.name}</span>
                    <span className="mono text-[10px] text-gold">Sharpe {m.sharpe ?? '—'}</span>
                  </div>
                  <div className="mono text-[10px] text-warmgray mt-1 flex gap-3">
                    <span>CAGR {fmtPct(m.cagr)}</span>
                    <span>maxDD {fmtPct(m.max_drawdown)}</span>
                    <span>hit {fmtPct(m.hit_rate)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}

function HypothesesTab() {
  const hypotheses = useAsync(() => helios.quantLab.hypotheses(), []);
  const [statement, setStatement] = useState('');
  const list: any[] = Array.isArray(hypotheses.data) ? hypotheses.data : [];

  async function create() {
    if (!statement.trim()) return;
    await helios.quantLab.createHypothesis({ statement });
    setStatement('');
    hypotheses.reload();
  }

  return (
    <div className="grid gap-3">
      <Panel title="New Hypothesis">
        <div className="flex gap-2">
          <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
            placeholder="e.g. Low-volatility stocks outperform on a risk-adjusted basis"
            value={statement} onChange={(e) => setStatement(e.target.value)} />
          <Button size="sm" variant="gold" onClick={create} disabled={!statement.trim()}>Add</Button>
        </div>
      </Panel>
      <Panel title="Research Hypotheses">
        {hypotheses.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No hypotheses tracked yet." />
        ) : (
          <div className="grid gap-2">
            {list.map((h: any) => (
              <div key={h.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                <span className="text-sm">{h.statement}</span>
                <span className="mono text-[10px] text-gold">{h.status}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function fmtPct(v: any): string {
  return typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—';
}
