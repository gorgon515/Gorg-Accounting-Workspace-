import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function MacroCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Macro Center." />;
  const indicators = useAsync(() => helios.macro.indicators(), []);
  const curve = useAsync(() => helios.macro.yieldCurve(), []);
  const [regime, setRegime] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function classify() {
    setBusy(true);
    try { setRegime(await helios.macro.classifyRegime()); }
    finally { setBusy(false); }
  }

  const ind = indicators.data ?? {};
  const yc = curve.data ?? {};
  const indKeys = Object.keys(ind);

  return (
    <Page title="Macro Center" subtitle="regime classification · risk-on/off · yield curve · outlook"
      actions={<Button size="sm" variant="gold" onClick={classify} disabled={busy}>{busy ? 'Classifying…' : 'Classify Regime'}</Button>}
    >
      <div className="grid gap-3">
        {regime && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <MetricCard label="Regime" value={cap(regime.regime)} accent />
              <MetricCard label="Stance" value={cap(regime.stance?.replace('_', '-'))} />
              <MetricCard label="Risk Score" value={`${Math.round((regime.risk_score ?? 0.5) * 100)}/100`} />
            </div>
            <Panel title="Economic Outlook">
              <p className="text-sm text-ivory/90">{regime.outlook}</p>
              {Array.isArray(regime.signals) && regime.signals.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {regime.signals.map((s: string, i: number) => (
                    <span key={i} className="mono text-[10px] px-2 py-0.5 rounded-full bg-ivory/5 text-warmgray">{s}</span>
                  ))}
                </div>
              )}
            </Panel>
          </>
        )}

        <Panel title="Macro Indicators">
          {indicators.loading ? <Loading /> : indKeys.length === 0 ? (
            <EmptyState message="No economic data yet. Poll FRED/BLS connectors to populate macro indicators." />
          ) : (
            <div className="grid grid-cols-4 gap-3">
              {indKeys.map((k) => (
                <MetricCard key={k} label={cap(k.replace('_', ' '))}
                  value={ind[k].value}
                  delta={ind[k].direction !== 'flat' ? { text: ind[k].direction === 'up' ? '▲' : '▼', up: ind[k].direction === 'up' } : undefined} />
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Yield Curve">
          {curve.loading ? <Loading /> : !yc.available ? (
            <EmptyState message="Yield curve data unavailable (needs GS10/GS2 series in the Financial Hub)." />
          ) : (
            <div className="grid grid-cols-3 gap-3">
              <MetricCard label="10Y–2Y Spread" value={yc.spread_10y_2y} />
              <MetricCard label="10Y–3M Spread" value={yc.spread_10y_3m ?? '—'} />
              <div className="glass p-3.5 rounded">
                <div className="mono text-[10px] uppercase tracking-wider text-warmgray">Signal</div>
                <div className={cls('mt-1 text-sm font-light',
                  yc.signal === 'recession_warning' ? 'text-helred' : 'text-helgreen')}>
                  {yc.signal === 'recession_warning' ? '⚠ Recession Warning (inverted)' : 'Normal'}
                </div>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function cap(s: any): string {
  return typeof s === 'string' && s ? s.charAt(0).toUpperCase() + s.slice(1) : '—';
}
