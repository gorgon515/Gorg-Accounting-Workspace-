import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Robinhood Hub — portfolio overview, positions, orders, and watchlists.
export function RobinhoodHub() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Robinhood Hub." />;
  const [tab, setTab] = useState<'portfolio' | 'positions' | 'orders' | 'watchlists'>('portfolio');

  const portfolio = useAsync(() => helios.robinhood.portfolio(), []);
  const positions = useAsync(() => helios.robinhood.positions(), []);
  const orders = useAsync(() => helios.robinhood.orders(), []);
  const watchlists = useAsync(() => helios.robinhood.watchlists(), []);

  const p: any = portfolio.data ?? {};
  const posList: any[] = Array.isArray(positions.data) ? positions.data : (positions.data?.results ?? []);
  const orderList: any[] = Array.isArray(orders.data) ? orders.data : (orders.data?.results ?? orders.data?.orders ?? []);
  const wlList: any[] = Array.isArray(watchlists.data) ? watchlists.data : (watchlists.data?.results ?? []);

  const equity = p.equity ?? p.market_value ?? p.total_equity ?? null;
  const buyingPower = p.buying_power ?? p.cash ?? null;
  const pnl = p.equity_previous_close != null && equity != null
    ? (Number(equity) - Number(p.equity_previous_close))
    : (p.total_return ?? p.unrealized_pnl ?? null);
  const pnlPct = p.percent_change ?? (equity && p.equity_previous_close
    ? ((Number(equity) - Number(p.equity_previous_close)) / Number(p.equity_previous_close)) * 100
    : null);

  const notConfigured = p.error || portfolio.error;

  return (
    <Page title="Robinhood Hub" subtitle="portfolio · positions · orders · watchlists">
      {notConfigured && (
        <div className="mb-3 px-3 py-2.5 rounded border border-helred/40 bg-helred/5 text-[12px] text-helred/90">
          Set <span className="mono">ROBINHOOD_USERNAME</span> and <span className="mono">ROBINHOOD_PASSWORD</span> env vars to connect your account.
        </div>
      )}
      <div className="grid gap-3">
        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {portfolio.loading ? <Loading /> : <>
            <MetricCard label="Portfolio Value" value={fmt$(equity)} accent />
            <MetricCard label="Buying Power" value={fmt$(buyingPower)} />
            <MetricCard label="Day P&L"
              value={(pnl != null ? (Number(pnl) >= 0 ? '+' : '') + fmt$(pnl) : '—')}
              sub={pnlPct != null ? `${pnlPct >= 0 ? '+' : ''}${Number(pnlPct).toFixed(2)}%` : ''} />
            <MetricCard label="Positions" value={posList.length || (positions.loading ? '…' : '—')} />
          </>}
        </div>

        {/* Tab bar */}
        <div className="flex gap-1.5">
          {(['portfolio', 'positions', 'orders', 'watchlists'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={cls('px-3 py-1.5 rounded border text-[11px] mono capitalize',
                tab === t ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'portfolio' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <Panel title="Account Details">
              {portfolio.loading ? <Loading /> : (
                <div className="grid gap-1.5">
                  {[
                    ['Total Equity', fmt$(p.equity ?? p.total_equity)],
                    ['Extended Hours', fmt$(p.extended_hours_equity)],
                    ['Buying Power', fmt$(p.buying_power ?? p.cash)],
                    ['Withdrawable', fmt$(p.withdrawable_amount)],
                    ['Margin', fmt$(p.margin_balance ?? p.uncleared_deposits)],
                    ['Portfolio Type', p.portfolio_type ?? p.account_type ?? '—'],
                    ['Account #', p.account_number ?? p.url?.split('/').filter(Boolean).pop() ?? '—'],
                  ].filter(([, v]) => v !== '—' && v != null).map(([label, val]) => (
                    <div key={label as string} className="flex items-center gap-2 px-2 py-1.5 rounded border border-hairline">
                      <span className="mono text-[10px] text-warmgray w-32">{label}</span>
                      <span className="text-[12px] mono">{String(val)}</span>
                    </div>
                  ))}
                  {Object.keys(p).length === 0 && !portfolio.loading && (
                    <EmptyState message="Connect Robinhood account to view portfolio." />
                  )}
                </div>
              )}
            </Panel>
            <Panel title="Portfolio Breakdown">
              {portfolio.loading ? <Loading /> : (
                <div className="grid gap-1.5">
                  {(['stocks', 'options', 'crypto', 'cash'] as const).map((asset) => {
                    const val = p[asset] ?? p[`${asset}_equity`] ?? p[`${asset}_market_value`];
                    if (val == null) return null;
                    const pct = equity ? (Number(val) / Number(equity)) * 100 : 0;
                    return (
                      <div key={asset} className="flex items-center gap-2">
                        <span className="mono text-[10px] uppercase text-warmgray w-16">{asset}</span>
                        <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                          <div className="h-full rounded-full bg-gold" style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                        <span className="mono text-[10px] text-warmgray w-20 text-right">{fmt$(val)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </Panel>
          </div>
        )}

        {tab === 'positions' && (
          <Panel title="Open Positions" subtitle={`${posList.length} holdings`}>
            {positions.loading ? <Loading /> : posList.length === 0 ? (
              <EmptyState message="No open positions." />
            ) : (
              <div className="grid gap-1.5 max-h-[560px] overflow-y-auto scroll-thin">
                <div className="grid grid-cols-6 gap-2 px-2.5 py-1 mono text-[9px] uppercase text-warmgray">
                  <span>Symbol</span><span>Qty</span><span>Avg Cost</span><span>Mkt Value</span><span>P&L</span><span>%</span>
                </div>
                {posList.map((pos: any, n: number) => {
                  const sym = pos.symbol ?? pos.ticker ?? pos.instrument_data?.symbol ?? '?';
                  const qty = Number(pos.quantity ?? pos.shares ?? 0);
                  const avg = Number(pos.average_buy_price ?? pos.avg_cost ?? 0);
                  const price = Number(pos.last_trade_price ?? pos.current_price ?? pos.market_price ?? 0);
                  const mktVal = qty * price || Number(pos.market_value ?? 0);
                  const cost = qty * avg || Number(pos.cost_basis ?? 0);
                  const pnlVal = mktVal - cost;
                  const pnlP = cost ? (pnlVal / cost) * 100 : 0;
                  return (
                    <div key={n} className="grid grid-cols-6 gap-2 px-2.5 py-2 rounded border border-hairline text-[11px]">
                      <span className="mono text-gold font-medium">{sym}</span>
                      <span className="mono">{qty.toFixed(qty % 1 === 0 ? 0 : 4)}</span>
                      <span className="mono">{fmt$(avg)}</span>
                      <span className="mono">{fmt$(mktVal || null)}</span>
                      <span className={cls('mono', pnlVal >= 0 ? 'text-helgreen' : 'text-helred')}>
                        {pnlVal !== 0 ? `${pnlVal >= 0 ? '+' : ''}${fmt$(pnlVal)}` : '—'}
                      </span>
                      <span className={cls('mono', pnlP >= 0 ? 'text-helgreen' : 'text-helred')}>
                        {cost ? `${pnlP >= 0 ? '+' : ''}${pnlP.toFixed(2)}%` : '—'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        )}

        {tab === 'orders' && (
          <Panel title="Order History" subtitle="recent equity orders"
            actions={<OrderStateFilter orders={orderList} />}>
            {orders.loading ? <Loading /> : orderList.length === 0 ? (
              <EmptyState message="No orders found." />
            ) : (
              <div className="grid gap-1.5 max-h-[560px] overflow-y-auto scroll-thin">
                <div className="grid grid-cols-6 gap-2 px-2.5 py-1 mono text-[9px] uppercase text-warmgray">
                  <span>Symbol</span><span>Side</span><span>Type</span><span>Qty/Amt</span><span>Price</span><span>Status</span>
                </div>
                {orderList.slice(0, 50).map((ord: any, n: number) => {
                  const sym = ord.symbol ?? ord.ticker ?? '?';
                  const side = ord.side ?? '';
                  const type = ord.type ?? ord.order_type ?? '';
                  const qty = ord.quantity ?? ord.filled_quantity ?? '';
                  const price = ord.average_price ?? ord.limit_price ?? ord.price ?? '';
                  const state = ord.state ?? ord.status ?? '';
                  return (
                    <div key={n} className="grid grid-cols-6 gap-2 px-2.5 py-2 rounded border border-hairline text-[11px]">
                      <span className="mono text-gold">{sym}</span>
                      <span className={cls('mono capitalize', side === 'buy' ? 'text-helgreen' : 'text-helred')}>{side}</span>
                      <span className="mono capitalize">{type}</span>
                      <span className="mono">{qty}</span>
                      <span className="mono">{price ? fmt$(price) : '—'}</span>
                      <span className={cls('mono text-[10px] capitalize', stateColor(state))}>{state}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        )}

        {tab === 'watchlists' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {watchlists.loading ? <Loading /> : wlList.length === 0 ? (
              <EmptyState message="No watchlists found." />
            ) : wlList.map((wl: any, n: number) => (
              <WatchlistPanel key={n} watchlist={wl} />
            ))}
          </div>
        )}
      </div>
    </Page>
  );
}

function WatchlistPanel({ watchlist }: { watchlist: any }) {
  const name = watchlist.display_name ?? watchlist.name ?? watchlist.id ?? 'Watchlist';
  const items: any[] = watchlist.items ?? watchlist.results ?? [];
  return (
    <Panel title={name} subtitle={`${items.length} symbols`}>
      {items.length === 0 ? (
        <EmptyState message="Empty watchlist." />
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((item: any, n: number) => {
            const sym = item.symbol ?? item.ticker ?? item;
            return (
              <span key={n} className="mono text-[11px] text-gold bg-gold/10 rounded px-2 py-0.5">
                {typeof sym === 'string' ? sym : sym?.symbol ?? '?'}
              </span>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function OrderStateFilter({ orders }: { orders: any[] }) {
  const states = Array.from(new Set(orders.map((o: any) => o.state ?? o.status ?? '').filter(Boolean)));
  if (states.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {states.map((s) => (
        <span key={s} className={cls('mono text-[9px] px-1.5 py-0.5 rounded border', stateColor(s), 'border-current/30')}>
          {s}
        </span>
      ))}
    </div>
  );
}

function stateColor(s: string): string {
  const st = (s ?? '').toLowerCase();
  if (st === 'filled') return 'text-helgreen';
  if (st === 'cancelled' || st === 'rejected' || st === 'failed') return 'text-helred';
  if (st === 'confirmed' || st === 'queued' || st === 'new') return 'text-gold';
  return 'text-warmgray';
}

function fmt$(v: any): string {
  const n = Number(v);
  if (isNaN(n) || v == null) return '—';
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
