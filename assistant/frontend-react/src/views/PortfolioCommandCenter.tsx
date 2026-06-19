import { Page } from './_page';
import { useState } from 'react';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const AGENTS = [
  { id: 'portfolio_manager', name: 'Portfolio Manager' },
  { id: 'quant_research', name: 'Quant Research' },
  { id: 'risk_officer', name: 'Risk Officer' },
  { id: 'macro_strategist', name: 'Macro Strategist' },
  { id: 'earnings_analyst', name: 'Earnings Analyst' },
  { id: 'factor_research', name: 'Factor Research' },
];

export function PortfolioCommandCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Portfolio Command Center." />;
  const overview = useAsync(() => helios.portfolioCommand.overview(), [], 60000);
  const [running, setRunning] = useState<Record<string, boolean>>({});

  async function runAgent(id: string) {
    setRunning((r) => ({ ...r, [id]: true }));
    try { await helios.quantAgents.run(id); overview.reload(); }
    finally { setRunning((r) => ({ ...r, [id]: false })); }
  }

  if (overview.loading) return <Page title="Portfolio Command Center"><Loading /></Page>;
  const o = overview.data ?? {};
  const macro = o.macro ?? {};
  const portfolios = o.portfolios ?? {};
  const risk = o.risk ?? {};
  const theses = o.theses ?? {};
  const signals = o.signals ?? {};
  const warnings: any[] = o.warnings ?? [];

  return (
    <Page title="Portfolio Command Center" subtitle="unified investment operations dashboard"
      actions={<Button size="sm" onClick={() => overview.reload()}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Portfolios" value={portfolios.count ?? 0} accent />
          <MetricCard label="Macro Regime" value={cap(macro.regime)} />
          <MetricCard label="Stance" value={cap(macro.stance?.replace?.('_', '-'))} />
          <MetricCard label="Active Theses" value={theses.stats?.active_theses ?? 0} />
        </div>

        {warnings.length > 0 && (
          <Panel title="⚠ Warnings">
            <div className="grid gap-1.5">
              {warnings.map((w, i) => (
                <div key={i} className="flex items-center gap-2 text-[12px]">
                  <span className={cls('mono text-[9px] uppercase', w.severity === 'high' ? 'text-helred' : 'text-gold')}>{w.type}</span>
                  <span>{w.message}</span>
                </div>
              ))}
            </div>
          </Panel>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Portfolios">
            {(portfolios.portfolios ?? []).length === 0 ? (
              <EmptyState message="No portfolios. Build one in the Portfolio Lab." />
            ) : (
              <div className="grid gap-1.5">
                {(portfolios.portfolios ?? []).map((p: any) => (
                  <div key={p.id} className="flex items-center justify-between text-[12px]">
                    <span>{p.name}</span>
                    <span className="mono text-[10px] text-warmgray">
                      {p.method} · Sharpe {p.stats?.sharpe?.toFixed?.(2) ?? '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Macro Snapshot">
            {macro.outlook ? (
              <>
                <p className="text-[12px] text-ivory/90">{macro.outlook}</p>
                <div className="mono text-[10px] text-warmgray mt-2">
                  Risk score {Math.round((macro.risk_score ?? 0.5) * 100)}/100
                  {macro.yield_curve?.signal === 'recession_warning' && <span className="text-helred"> · yield curve inverted</span>}
                </div>
              </>
            ) : <EmptyState message="Run the Macro Strategist agent to classify the regime." />}
          </Panel>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Investment Theses">
            {(theses.active ?? []).length === 0 ? (
              <EmptyState message="No active theses." />
            ) : (
              <div className="grid gap-1.5">
                {(theses.active ?? []).map((t: any) => (
                  <div key={t.id} className="flex items-center justify-between text-[12px]">
                    <span className="truncate">{t.title}</span>
                    <span className="mono text-[10px] text-gold">{Math.round((t.confidence ?? 0) * 100)}%</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Signals">
            <div className="grid gap-1.5">
              {[...(signals.market ?? []).slice(0, 4), ...(signals.alternative ?? []).slice(0, 4)].length === 0 ? (
                <EmptyState message="No active signals." />
              ) : (
                <>
                  {(signals.market ?? []).slice(0, 4).map((s: any) => (
                    <div key={s.id} className="flex items-center justify-between text-[12px]">
                      <span className="truncate">{s.title}</span>
                      <span className="mono text-[10px] text-warmgray">{s.direction}</span>
                    </div>
                  ))}
                  {(signals.alternative ?? []).slice(0, 4).map((s: any) => (
                    <div key={s.id} className="flex items-center justify-between text-[12px]">
                      <span className="truncate">{s.title}</span>
                      <span className="mono text-[10px] text-warmgray">{s.direction}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </Panel>
        </div>

        <Panel title="Investment Agents" subtitle="run advisory agents — proposals enter the approval queue">
          <div className="grid grid-cols-3 gap-2">
            {AGENTS.map((a) => (
              <Button key={a.id} size="sm" variant="ghost" onClick={() => runAgent(a.id)} disabled={running[a.id]}>
                {running[a.id] ? '…' : a.name}
              </Button>
            ))}
          </div>
        </Panel>
      </div>
    </Page>
  );
}

function cap(s: any): string {
  return typeof s === 'string' && s ? s.charAt(0).toUpperCase() + s.slice(1) : '—';
}
