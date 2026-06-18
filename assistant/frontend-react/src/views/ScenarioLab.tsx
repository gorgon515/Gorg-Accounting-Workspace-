import { useState } from 'react';
import { Page } from './_page';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, fmtMoney } from '../lib/format';

interface Levers {
  revenue_change_pct: number;
  expense_change_pct: number;
  headcount_delta: number;
  avg_salary: number;
  tax_rate_delta: number;
}

const PRESETS: Array<{ name: string; levers: Partial<Levers> }> = [
  { name: 'Revenue drops 15%', levers: { revenue_change_pct: -15 } },
  { name: 'Hire two staff', levers: { headcount_delta: 2, avg_salary: 90000 } },
  { name: 'Cut expenses 10%', levers: { expense_change_pct: -10 } },
  { name: 'Grow revenue 25%', levers: { revenue_change_pct: 25 } },
];

export function ScenarioLab() {
  const [levers, setLevers] = useState<Levers>({
    revenue_change_pct: 0, expense_change_pct: 0, headcount_delta: 0,
    avg_salary: 90000, tax_rate_delta: 0,
  });
  const [result, setResult] = useState<any>(null);
  const [sensitivity, setSensitivity] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Scenario Lab." />;

  function set(key: keyof Levers, value: number) {
    setLevers((l) => ({ ...l, [key]: value }));
  }

  async function run() {
    setBusy(true);
    try {
      setResult(await helios.forecasting.scenario({ levers, label: 'custom' }));
      setSensitivity(await helios.forecasting.sensitivity({ levers }));
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(p: Partial<Levers>) {
    setLevers((l) => ({ ...l, revenue_change_pct: 0, expense_change_pct: 0, headcount_delta: 0, tax_rate_delta: 0, ...p }));
  }

  return (
    <Page
      title="Scenario Lab"
      subtitle="what-if analysis · sensitivity"
      actions={<Button size="sm" variant="gold" onClick={run} disabled={busy}>{busy ? 'Running…' : 'Run Scenario'}</Button>}
    >
      <div className="grid gap-3">
        <Panel title="Presets">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Button key={p.name} size="sm" onClick={() => applyPreset(p.levers)}>{p.name}</Button>
            ))}
          </div>
        </Panel>

        <Panel title="Levers">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Slider label="Revenue change (%)" value={levers.revenue_change_pct} min={-50} max={50}
              onChange={(v) => set('revenue_change_pct', v)} />
            <Slider label="Expense change (%)" value={levers.expense_change_pct} min={-50} max={50}
              onChange={(v) => set('expense_change_pct', v)} />
            <Slider label="Headcount change (FTE)" value={levers.headcount_delta} min={-5} max={10}
              onChange={(v) => set('headcount_delta', v)} />
            <Slider label="Tax-rate change (pp)" value={levers.tax_rate_delta} min={-10} max={10}
              onChange={(v) => set('tax_rate_delta', v)} />
          </div>
        </Panel>

        {busy && <Loading />}

        {result && !result.error && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard label="Baseline Net" value={fmtMoney(result.baseline?.net)} />
              <MetricCard label="Projected Net" value={fmtMoney(result.projected?.net)} accent />
              <MetricCard label="Δ Net" value={fmtMoney(result.delta_net)} />
              <MetricCard label="Δ Net %" value={`${result.delta_net_pct ?? 0}%`} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Panel title="Risks">
                {(result.risks ?? []).length === 0 ? (
                  <EmptyState message="No scenario risks." />
                ) : (
                  <ul className="grid gap-1">
                    {result.risks.map((r: string, i: number) => (
                      <li key={i} className="text-[12px] text-helred">⚠ {r}</li>
                    ))}
                  </ul>
                )}
              </Panel>
              <Panel title="Opportunities">
                {(result.opportunities ?? []).length === 0 ? (
                  <EmptyState message="No scenario opportunities." />
                ) : (
                  <ul className="grid gap-1">
                    {result.opportunities.map((o: string, i: number) => (
                      <li key={i} className="text-[12px] text-helgreen">↗ {o}</li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </>
        )}

        {sensitivity && !sensitivity.error && (
          <Panel title="Sensitivity Analysis" subtitle={`±${sensitivity.step_pct}% per lever`}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left mono text-[10px] uppercase text-warmgray">
                  <th className="py-1">Lever</th><th>Net (up)</th><th>Net (down)</th><th>Swing</th>
                </tr>
              </thead>
              <tbody>
                {(sensitivity.sensitivity ?? []).map((s: any) => (
                  <tr key={s.lever} className="border-t border-hairline">
                    <td className="py-1.5">{s.label}</td>
                    <td className="tabular-nums">{fmtMoney(s.net_up)}</td>
                    <td className="tabular-nums">{fmtMoney(s.net_down)}</td>
                    <td className={cls('tabular-nums text-gold')}>{fmtMoney(s.swing)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}
      </div>
    </Page>
  );
}

function Slider({ label, value, min, max, onChange }: {
  label: string; value: number; min: number; max: number; onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="mono text-[11px] text-warmgray">{label}</span>
        <span className="mono text-[11px] text-gold">{value}</span>
      </div>
      <input type="range" min={min} max={max} value={value}
        onChange={(e) => onChange(parseInt(e.target.value))} className="w-full accent-gold" />
    </div>
  );
}
