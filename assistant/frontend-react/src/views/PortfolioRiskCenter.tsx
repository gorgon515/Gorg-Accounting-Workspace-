import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function PortfolioRiskCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Risk Center." />;
  const portfolios = useAsync(() => helios.portfolioLab.list(), []);
  const [report, setReport] = useState<any>(null);
  const [stress, setStress] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(portfolios.data) ? portfolios.data : [];

  async function analyze(pf: any) {
    setBusy(true);
    try {
      const holdings = Object.entries(pf.weights ?? {}).map(([symbol, weight]) => ({ symbol, weight }));
      const r = await helios.riskAnalytics.analyze({ holdings, name: pf.name, portfolio_id: pf.id });
      setReport(r);
      const st = await helios.riskAnalytics.stressTest({ holdings });
      setStress(st);
    } finally { setBusy(false); }
  }

  return (
    <Page title="Risk Center" subtitle="VaR · stress testing · concentration · tail risk · health scoring">
      <div className="grid gap-3">
        <Panel title="Portfolios">
          {portfolios.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No portfolios to analyze. Build one in the Portfolio Lab first." />
          ) : (
            <div className="grid gap-2">
              {list.map((p: any) => (
                <div key={p.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                  <span className="text-sm">{p.name}</span>
                  <Button size="sm" onClick={() => analyze(p)} disabled={busy}>Analyze Risk</Button>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {report && !report.error && (
          <>
            <div className="grid grid-cols-4 gap-3">
              <HealthCard score={report.health_score} />
              <MetricCard label="VaR 95 (1d)" value={`${report.var?.historical_pct ?? '—'}%`} />
              <MetricCard label="Exp. Shortfall" value={`${report.expected_shortfall?.value_pct ?? '—'}%`} />
              <MetricCard label="Volatility (ann)" value={fmtPct(report.volatility_annual)} />
            </div>
            <Panel title="Concentration & Correlation">
              <div className="grid grid-cols-2 gap-4 text-[12px]">
                <div className="grid gap-1">
                  <Row label="Herfindahl" value={report.concentration?.herfindahl} />
                  <Row label="Effective positions" value={report.concentration?.effective_positions} />
                  <Row label="Top-3 weight" value={fmtPct(report.concentration?.top3_weight)} />
                  <Row label="Largest position" value={`${report.concentration?.max_position?.symbol ?? '—'} (${fmtPct(report.concentration?.max_position?.weight)})`} />
                </div>
                <div className="grid gap-1">
                  <Row label="Avg correlation" value={report.correlation?.avg_correlation} />
                  <Row label="Max correlation" value={report.correlation?.max_correlation} />
                  <Row label="Diversification" value={report.correlation?.diversification_ratio} />
                  <Row label="Fat tails" value={report.tail_risk?.fat_tails ? 'yes' : 'no'} />
                </div>
              </div>
            </Panel>
            {stress && stress.scenarios && (
              <Panel title="Stress Testing" subtitle="historical scenario shocks">
                <div className="grid gap-1.5">
                  {stress.scenarios.map((s: any) => (
                    <div key={s.scenario_id} className="flex items-center justify-between text-[12px]">
                      <span>{s.name}</span>
                      <span className={cls('mono', s.portfolio_pnl < 0 ? 'text-helred' : 'text-helgreen')}>
                        {s.portfolio_pnl_pct}% · vol ×{s.vol_multiplier}
                      </span>
                    </div>
                  ))}
                </div>
              </Panel>
            )}
          </>
        )}
        {report?.error && <EmptyState message={`Risk analysis needs price history: ${report.error}`} />}
      </div>
    </Page>
  );
}

function HealthCard({ score }: { score: number | null }) {
  const color = score == null ? 'text-warmgray' : score >= 70 ? 'text-helgreen' : score >= 50 ? 'text-gold' : 'text-helred';
  return (
    <div className="glass p-3.5 rounded">
      <div className="mono text-[10px] uppercase tracking-wider text-warmgray">Portfolio Health</div>
      <div className={cls('mt-1 text-xl font-light tabular-nums', color)}>{score ?? '—'}<span className="text-sm text-warmgray">/100</span></div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-warmgray">{label}</span>
      <span className="mono">{value ?? '—'}</span>
    </div>
  );
}

function fmtPct(v: any): string {
  return typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—';
}
