import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Table, MetricCard, EmptyState, Loading } from '../components';
import type { Column } from '../components';
import { fmtMoney, fmtPct, dirColor } from '../lib/format';

interface Position {
  symbol: string;
  quantity?: number;
  average_buy_price?: number;
  last_trade_price?: number;
  current_price?: number;
  equity?: number;
  percent_change?: number;
  intraday_quantity?: number;
  name?: string;
}

interface Order {
  id?: string;
  symbol?: string;
  side?: string;
  type?: string;
  quantity?: string | number;
  price?: string | number;
  state?: string;
  created_at?: string;
}

export function Portfolio() {
  const pf = useAsync(() => helios.robinhood.portfolio(), [], 30000);
  const pos = useAsync(() => helios.robinhood.positions(), [], 30000);
  const orders = useAsync(() => helios.robinhood.orders(), [], 60000);

  const positions: Position[] = (pos.data ?? []).filter((p: any) => parseFloat(p.quantity ?? p.intraday_quantity ?? '0') > 0);
  const recentOrders: Order[] = (orders.data ?? []).slice(0, 10);

  const pfData = pf.data ?? {};
  const equity = parseFloat(pfData.equity ?? pfData.market_value ?? '0') || null;
  const cash = parseFloat(pfData.withdrawable_amount ?? pfData.cash ?? '0') || null;
  const dayPL = parseFloat(pfData.equity_previous_close ?? '0') || null;
  const dayPLPct = equity && dayPL ? ((equity - dayPL) / dayPL) * 100 : null;

  const posCols: Column<Position>[] = [
    { key: 's', header: 'Symbol', render: (p) => <span className="text-ivory font-medium">{p.symbol ?? '—'}</span> },
    { key: 'q', header: 'Qty', align: 'right', render: (p) => {
      const q = parseFloat(String(p.quantity ?? p.intraday_quantity ?? '0'));
      return <span className="mono text-[11px]">{q % 1 === 0 ? q.toFixed(0) : q.toFixed(4)}</span>;
    }},
    { key: 'avg', header: 'Avg Cost', align: 'right', render: (p) => {
      const v = parseFloat(String(p.average_buy_price ?? ''));
      return isNaN(v) ? '—' : fmtMoney(v);
    }},
    { key: 'cur', header: 'Price', align: 'right', render: (p) => {
      const v = parseFloat(String(p.last_trade_price ?? p.current_price ?? ''));
      return isNaN(v) ? '—' : fmtMoney(v);
    }},
    { key: 'eq', header: 'Value', align: 'right', render: (p) => {
      const v = parseFloat(String(p.equity ?? ''));
      return isNaN(v) ? '—' : fmtMoney(v);
    }},
    { key: 'pl', header: 'P/L%', align: 'right', render: (p) => {
      const pct = p.percent_change != null ? parseFloat(String(p.percent_change)) : null;
      if (pct == null || isNaN(pct)) return '—';
      return <span className={dirColor(pct)}>{fmtPct(pct)}</span>;
    }},
  ];

  const orderCols: Column<Order>[] = [
    { key: 's', header: 'Symbol', render: (o) => <span className="text-ivory">{o.symbol ?? '—'}</span> },
    { key: 'sd', header: 'Side', render: (o) => (
      <span className={o.side === 'buy' ? 'text-helgreen' : 'text-red-400'}>{o.side ?? '—'}</span>
    )},
    { key: 'q', header: 'Qty', align: 'right', render: (o) => o.quantity ?? '—' },
    { key: 'p', header: 'Price', align: 'right', render: (o) => {
      const v = parseFloat(String(o.price ?? ''));
      return isNaN(v) ? 'mkt' : fmtMoney(v);
    }},
    { key: 'st', header: 'Status', render: (o) => (
      <span className="mono text-[10px] text-warmgray">{o.state ?? '—'}</span>
    )},
  ];

  const needsConfig = pf.error?.includes('not configured') ||
    pos.error?.includes('not configured');

  return (
    <Page title="Portfolio" subtitle="Robinhood live positions · orders · P&L">
      {needsConfig ? (
        <Panel title="Robinhood not configured">
          <p className="text-[12px] text-ivory/80">
            Go to <span className="mono text-gold">Settings → Integrations</span> and enter your Robinhood
            credentials to connect your live portfolio.
          </p>
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <MetricCard label="Portfolio value" accent
              value={equity != null ? fmtMoney(equity) : pf.loading ? '…' : '—'}
              sub="Robinhood equity" />
            <MetricCard label="Cash"
              value={cash != null ? fmtMoney(cash) : pf.loading ? '…' : '—'} />
            <MetricCard label="Day P/L"
              value={dayPLPct != null
                ? <span className={dirColor(dayPLPct)}>{fmtPct(dayPLPct)}</span>
                : pf.loading ? '…' : '—'} />
            <MetricCard label="Positions"
              value={pf.loading ? '…' : positions.length} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <Panel title="Holdings" subtitle="live Robinhood positions" scroll className="max-h-[460px]">
              {pos.loading ? <Loading /> : (
                <Table columns={posCols} rows={positions}
                  empty={pos.error ? `Robinhood error: ${pos.error}` : 'No open positions.'} />
              )}
            </Panel>

            <div className="flex flex-col gap-3">
              <Panel title="Recent orders" subtitle="last 10" scroll className="max-h-[220px]">
                {orders.loading ? <Loading /> : (
                  <Table columns={orderCols} rows={recentOrders}
                    empty={orders.error ?? 'No recent orders.'} />
                )}
              </Panel>

              <Panel title="Account summary">
                {pf.loading ? <Loading /> : !pfData || Object.keys(pfData).length === 0
                  ? <EmptyState message={pf.error ?? 'No portfolio data.'} />
                  : (
                    <div className="grid grid-cols-2 gap-1 text-[11px]">
                      {[
                        ['Equity', equity != null ? fmtMoney(equity) : null],
                        ['Prev close', pfData.equity_previous_close != null ? fmtMoney(parseFloat(pfData.equity_previous_close)) : null],
                        ['Withdrawable', cash != null ? fmtMoney(cash) : null],
                        ['Uncleared deposits', pfData.uncleared_deposits != null ? fmtMoney(parseFloat(pfData.uncleared_deposits)) : null],
                        ['Market value', pfData.market_value != null ? fmtMoney(parseFloat(pfData.market_value)) : null],
                        ['Extended hours value', pfData.extended_hours_equity != null ? fmtMoney(parseFloat(pfData.extended_hours_equity)) : null],
                      ].filter(([, v]) => v != null).map(([k, v]) => (
                        <div key={String(k)} className="flex justify-between border-b border-hairline pb-1">
                          <span className="text-warmgray">{k}</span>
                          <span className="mono text-ivory">{v}</span>
                        </div>
                      ))}
                    </div>
                  )}
              </Panel>
            </div>
          </div>
        </>
      )}
    </Page>
  );
}
