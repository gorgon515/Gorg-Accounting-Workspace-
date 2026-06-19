import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading, Chart } from '../components';

export function BacktestingCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Backtesting Center." />;
  const runs = useAsync(() => helios.backtesting.runs(), []);
  const [selected, setSelected] = useState<any>(null);
  const list: any[] = Array.isArray(runs.data) ? runs.data : [];

  return (
    <Page title="Backtesting Center" subtitle="historical simulation · walk-forward · Monte Carlo">
      <div className="grid gap-3">
        <SyntheticRunner onRun={(r) => { setSelected(r); runs.reload(); }} />
        {selected && <RunDetail run={selected} />}
        <Panel title="Backtest History">
          {runs.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No backtests yet. Run experiments from the Quant Lab or use the demo runner above." />
          ) : (
            <div className="grid gap-2">
              {list.map((r: any) => (
                <div key={r.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-ivory/5"
                  onClick={() => helios.backtesting.getRun(r.id).then(setSelected)}>
                  <div>
                    <span className="text-sm">{r.name}</span>
                    <p className="mono text-[10px] text-warmgray">{r.symbol || 'portfolio'} · {r.n_periods} periods</p>
                  </div>
                  <span className="mono text-[10px] text-gold">Sharpe {r.metrics?.sharpe ?? '—'}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function SyntheticRunner({ onRun }: { onRun: (r: any) => void }) {
  const [busy, setBusy] = useState(false);
  const [mc, setMc] = useState<any>(null);

  async function demo() {
    setBusy(true);
    try {
      // Generate a synthetic signal/return series client-side to exercise the engine.
      const n = 252;
      const rets: number[] = [];
      const sig: number[] = [];
      let seed = 12345;
      const rand = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
      for (let i = 0; i < n; i++) {
        const z = (rand() - 0.5) * 2;
        rets.push(0.0006 + z * 0.012);
        sig.push(rand() > 0.4 ? 1 : 0);
      }
      const run = await helios.backtesting.run({ name: 'Demo Backtest', signals: sig, asset_returns: rets, benchmark_returns: rets });
      onRun(run);
      const m = await helios.backtesting.monteCarlo({ strategy_returns: rets, n_sims: 500 });
      setMc(m);
    } finally { setBusy(false); }
  }

  return (
    <Panel title="Engine Demo" subtitle="run a synthetic backtest + Monte Carlo to validate the engine"
      actions={<Button size="sm" variant="gold" onClick={demo} disabled={busy}>{busy ? 'Running…' : 'Run Demo'}</Button>}
    >
      {mc ? (
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="MC Mean Return" value={fmtPct(mc.terminal_return?.mean)} accent />
          <MetricCard label="P05 Return" value={fmtPct(mc.terminal_return?.p05)} />
          <MetricCard label="P95 Return" value={fmtPct(mc.terminal_return?.p95)} />
          <MetricCard label="Prob. Loss" value={fmtPct(mc.terminal_return?.prob_loss)} />
        </div>
      ) : (
        <p className="text-[12px] text-warmgray">Runs a 252-day simulation with transaction costs, then bootstraps 500 Monte Carlo paths.</p>
      )}
    </Panel>
  );
}

function RunDetail({ run }: { run: any }) {
  const m = run.metrics ?? {};
  const equity: number[] = run.equity_curve ?? [];
  return (
    <Panel title={`${run.name} — Results`}>
      <div className="grid grid-cols-6 gap-2 mb-3">
        <MetricCard label="Total Return" value={fmtPct(m.total_return)} accent />
        <MetricCard label="CAGR" value={fmtPct(m.cagr)} />
        <MetricCard label="Sharpe" value={m.sharpe ?? '—'} />
        <MetricCard label="Sortino" value={m.sortino ?? '—'} />
        <MetricCard label="Max DD" value={fmtPct(m.max_drawdown)} />
        <MetricCard label="Calmar" value={m.calmar ?? '—'} />
      </div>
      {equity.length > 1 && (
        <Chart data={equity} height={140} stroke="auto" />
      )}
      <div className="grid grid-cols-4 gap-2 mt-3">
        <MetricCard label="Volatility" value={fmtPct(m.volatility)} />
        <MetricCard label="Hit Rate" value={fmtPct(m.hit_rate)} />
        <MetricCard label="Profit Factor" value={m.profit_factor ?? '—'} />
        <MetricCard label="VaR 95" value={fmtPct(m.var_95)} />
      </div>
    </Panel>
  );
}

function fmtPct(v: any): string {
  return typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—';
}
