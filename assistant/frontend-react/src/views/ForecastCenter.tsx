import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { fmtMoney } from '../lib/format';

const METRICS = ['revenue', 'expenses', 'cash_flow', 'savings'] as const;

export function ForecastCenter() {
  const [metric, setMetric] = useState<string>('cash_flow');
  const [months, setMonths] = useState(12);
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for forecasts." />;

  const forecast = useAsync(() => helios.forecasting.metric(metric, months), [metric, months]);

  return (
    <Page
      title="Forecast Center"
      subtitle="revenue · expenses · cash flow · savings"
      actions={
        <div className="flex items-center gap-2">
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={months} onChange={(e) => setMonths(parseInt(e.target.value))}>
            {[6, 12, 24, 36].map((m) => <option key={m} value={m}>{m}mo</option>)}
          </select>
        </div>
      }
    >
      {forecast.loading ? <Loading /> : <ForecastBody data={forecast.data} />}
    </Page>
  );
}

function ForecastBody({ data }: { data: any }) {
  if (!data || data.error) return <EmptyState message={data?.error ?? 'No forecast.'} />;
  const sc = data.scenarios ?? {};
  const bands = ['conservative', 'expected', 'aggressive'];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Base Value" value={fmtMoney(data.base_value)} />
        <MetricCard label="Expected (end)" value={fmtMoney(sc.expected?.ending_value)} accent />
        <MetricCard label="Confidence" value={`${Math.round((data.confidence ?? 0) * 100)}%`} />
        <MetricCard label="Horizon" value={`${data.months} mo`} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {bands.map((b) => (
          <Panel key={b} title={<span className="capitalize">{b}</span>}
            subtitle={`growth ${((sc[b]?.monthly_growth ?? 0) * 100).toFixed(1)}%/mo`}>
            <div className="text-xl font-light text-gold">{fmtMoney(sc[b]?.ending_value)}</div>
            <div className="mono text-[11px] text-warmgray mt-1">total {fmtMoney(sc[b]?.total)}</div>
            <Sparkline series={sc[b]?.series ?? []} />
          </Panel>
        ))}
      </div>
      <Panel title="Projected Series (expected)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Month</th>
                {bands.map((b) => <th key={b} className="capitalize">{b}</th>)}
              </tr>
            </thead>
            <tbody>
              {(sc.expected?.series ?? []).map((_: number, i: number) => (
                <tr key={i} className="border-t border-hairline">
                  <td className="py-1">{i + 1}</td>
                  {bands.map((b) => <td key={b} className="tabular-nums">{fmtMoney(sc[b]?.series?.[i])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function Sparkline({ series }: { series: number[] }) {
  if (!series.length) return null;
  const max = Math.max(...series);
  const min = Math.min(...series);
  const range = max - min || 1;
  return (
    <div className="flex items-end gap-0.5 h-10 mt-2">
      {series.map((v, i) => (
        <div key={i} className="flex-1 bg-gold/40 rounded-sm"
          style={{ height: `${((v - min) / range) * 100}%`, minHeight: '2px' }} />
      ))}
    </div>
  );
}
