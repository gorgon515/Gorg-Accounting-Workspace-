import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Table, MetricCard, EmptyState } from '../components';
import type { Column } from '../components';
import { fmtMoney, fmtPct, dirColor } from '../lib/format';

interface Position { symbol: string; qty?: number; avgPrice?: number; price?: number; value?: number; plPercent?: number; pl?: number }

export function Portfolio() {
  const pf = useAsync(() => helios.trading.portfolio(), [], 15000);
  const positions: Position[] = pf.data?.positions ?? [];

  // Build a portfolio risk view from the held positions (sidecar HHI/sector).
  const risk = useAsync(
    () => (positions.length
      ? helios.sidecar.portfolio({ holdings: positions.map((p) => ({ symbol: p.symbol, value: p.value ?? 0 })) })
      : Promise.resolve(null)),
    [positions.length],
  );

  const cols: Column<Position>[] = [
    { key: 's', header: 'Symbol', render: (p) => <span className="text-ivory">{p.symbol}</span> },
    { key: 'q', header: 'Qty', align: 'right', render: (p) => p.qty ?? '—' },
    { key: 'v', header: 'Value', align: 'right', render: (p) => fmtMoney(p.value) },
    { key: 'pl', header: 'P/L%', align: 'right', render: (p) => <span className={dirColor(p.plPercent)}>{fmtPct(p.plPercent)}</span> },
  ];

  return (
    <Page title="Portfolio" subtitle="holdings · allocation · risk">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Account value" accent value={fmtMoney(pf.data?.value ?? pf.data?.equity)} sub={pf.data?.mode || 'paper'} />
        <MetricCard label="Cash" value={fmtMoney(pf.data?.cash)} />
        <MetricCard label="Positions" value={positions.length} />
        <MetricCard label="Concentration" value={risk.data ? risk.data.concentration_hhi : '—'}
          sub={risk.data?.effective_positions ? `${risk.data.effective_positions} effective` : 'HHI'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Holdings" scroll className="max-h-[420px]">
          <Table columns={cols} rows={positions}
            empty={pf.error ? 'Portfolio lives in the desktop app.' : 'No positions yet.'} />
        </Panel>
        <Panel title="Risk & exposure" subtitle="Intelligence Sidecar">
          {!positions.length ? <EmptyState message="Add positions to see risk analytics." />
            : risk.error ? <EmptyState message="Sidecar offline." />
            : risk.data ? (
              <div className="text-[12px] flex flex-col gap-2">
                <Row k="Largest position" v={`${risk.data.largest_position?.symbol} (${(risk.data.largest_position?.weight * 100).toFixed(1)}%)`} />
                <Row k="Effective positions" v={risk.data.effective_positions} />
                <div>
                  <div className="mono text-[10px] uppercase text-warmgray mb-1">Sector exposure</div>
                  {Object.entries(risk.data.sector_exposure ?? {}).map(([s, w]: any) => (
                    <div key={s} className="flex items-center gap-2 mb-1">
                      <span className="w-24 truncate">{s}</span>
                      <div className="flex-1 h-1.5 rounded bg-obsidian overflow-hidden">
                        <div className="h-full bg-gold" style={{ width: `${(w * 100).toFixed(0)}%` }} />
                      </div>
                      <span className="mono text-[10px] text-warmgray w-10 text-right">{(w * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <EmptyState message="No risk data." />}
        </Panel>
      </div>
    </Page>
  );
}

function Row({ k, v }: { k: string; v: any }) {
  return (
    <div className="flex items-center justify-between border-b border-hairline pb-1.5">
      <span className="text-warmgray">{k}</span>
      <span className="text-ivory">{v ?? '—'}</span>
    </div>
  );
}
