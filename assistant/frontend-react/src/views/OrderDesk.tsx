import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Order Desk — agentic trade desk connecting Discovery Engine ideas → TradingView
// live data → Robinhood execution with mandatory human approval gate.
//
// SECURITY: No order is placed without explicit user confirmation. The approval
// gate is enforced on both client and server side (approval_confirmed flag).
export function OrderDesk() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Order Desk." />;
  const [selected, setSelected] = useState<string | null>(null);
  const [review, setReview] = useState<any>(null);
  const [approved, setApproved] = useState(false);
  const [placing, setPlacing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('limit');
  const [qty, setQty] = useState('');
  const [limitPrice, setLimitPrice] = useState('');

  const ideas = useAsync(() => helios.discovery.ideas('top25'), []);
  const enrich = useAsync(
    () => (selected ? helios.tradingview.enrich(selected) : Promise.resolve(null)),
    [selected]
  );
  const rhPos = useAsync(() => helios.robinhood.positions().catch(() => ({ results: [] })), []);

  const ideaList: any[] = Array.isArray(ideas.data) ? ideas.data : (ideas.data?.ideas ?? []);
  const enrichData: any = enrich.data ?? {};
  const quote: any = enrichData.quote ?? {};
  const ta: any = enrichData.ta ?? {};
  const news: any[] = enrichData.news ?? [];
  const posList: any[] = Array.isArray(rhPos.data) ? rhPos.data : (rhPos.data?.results ?? []);

  const currentPos = posList.find((p: any) =>
    (p.symbol ?? p.ticker ?? '').toUpperCase() === (selected ?? '').toUpperCase()
  );

  async function doReview() {
    if (!selected || !qty) return;
    setReview(null); setApproved(false); setResult(null);
    const params: any = { symbol: selected, side: orderSide, order_type: orderType, quantity: Number(qty) };
    if (orderType === 'limit' && limitPrice) params.limit_price = Number(limitPrice);
    try {
      const r = await helios.robinhood.reviewOrder(params);
      setReview(r);
    } catch (e: any) {
      setReview({ error: e?.message ?? 'Review failed' });
    }
  }

  async function doPlace() {
    if (!selected || !qty || !approved) return;
    setPlacing(true);
    try {
      const params: any = {
        symbol: selected, side: orderSide, order_type: orderType,
        quantity: Number(qty), approval_confirmed: true,
      };
      if (orderType === 'limit' && limitPrice) params.limit_price = Number(limitPrice);
      const r = await helios.robinhood.placeOrder(params);
      setResult(r);
      setReview(null); setApproved(false);
    } catch (e: any) {
      setResult({ error: e?.message ?? 'Order failed' });
    } finally { setPlacing(false); }
  }

  function select(sym: string) {
    setSelected(sym); setReview(null); setApproved(false); setResult(null);
    const idea = ideaList.find((i: any) => i.symbol === sym);
    if (idea && !limitPrice) {
      const q: any = {};
      const lp = q.price ?? '';
      if (lp) setLimitPrice(String(lp));
    }
  }

  return (
    <Page title="Order Desk" subtitle="Discovery Engine → TradingView → Robinhood · human approval required">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Idea list */}
        <Panel title="Discovery Ideas" subtitle="top25 ranked candidates" className="lg:col-span-1">
          {ideas.loading ? <Loading /> : ideaList.length === 0 ? (
            <EmptyState message="Run the Discovery Engine first to populate ideas." />
          ) : (
            <div className="grid gap-1.5 max-h-[600px] overflow-y-auto scroll-thin">
              {ideaList.map((idea: any, n: number) => {
                const sym = idea.symbol;
                const inPos = posList.some((p: any) => (p.symbol ?? '').toUpperCase() === sym.toUpperCase());
                return (
                  <button key={n} onClick={() => select(sym)}
                    className={cls('text-left px-2.5 py-2 rounded border',
                      selected === sym ? 'border-gold/40 bg-gold/5' : 'border-hairline hover:bg-ivory/5')}>
                    <div className="flex items-center gap-2">
                      <span className="mono text-[11px] text-gold w-14">{sym}</span>
                      <span className="text-[11px] flex-1 truncate text-ivory/80">{idea.name}</span>
                      {inPos && <span className="mono text-[8px] text-helgreen bg-helgreen/10 rounded px-1">HELD</span>}
                      <span className="mono text-[10px] text-warmgray">
                        {idea.composite != null ? `${Math.round(idea.composite)}` : ''}
                      </span>
                    </div>
                    <div className="flex gap-1 mt-1">
                      <span className="mono text-[8px] text-warmgray">{idea.sector}</span>
                      <span className="mono text-[8px] text-warmgray">·</span>
                      <span className="mono text-[8px] text-warmgray">{idea.cap_tier}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </Panel>

        {/* Right column: enrichment + order form */}
        <div className="lg:col-span-2 grid gap-3">
          {!selected ? (
            <Panel title="Select an Idea">
              <EmptyState message="Choose a Discovery idea on the left to see live data and place an order." />
            </Panel>
          ) : (
            <>
              {/* Live enrichment */}
              <div className="grid grid-cols-3 gap-3">
                {enrich.loading ? <Loading /> : <>
                  <MetricCard label="Price" value={quote.price ?? quote.last_price ?? quote.close ?? '—'} accent />
                  <MetricCard label="Change"
                    value={quote.change_pct != null ? `${quote.change_pct >= 0 ? '+' : ''}${Number(quote.change_pct).toFixed(2)}%` : '—'}
                    sub={quote.change_abs != null ? `$${quote.change_abs}` : ''} />
                  <MetricCard label="TA Signal"
                    value={taSignal(ta)}
                    sub={`vol ${fmtNum(quote.volume)}`} />
                </>}
              </div>

              {/* Current position */}
              {currentPos && (
                <Panel title="Current Position" subtitle={selected}>
                  <div className="grid grid-cols-3 gap-3">
                    <MetricCard label="Qty" value={Number(currentPos.quantity ?? 0).toFixed(2)} />
                    <MetricCard label="Avg Cost" value={`$${Number(currentPos.average_buy_price ?? 0).toFixed(2)}`} />
                    <MetricCard label="Market Value" value={currentPos.equity ?? currentPos.market_value ?? '—'} />
                  </div>
                </Panel>
              )}

              {/* Recent news */}
              {news.length > 0 && (
                <Panel title="Recent News" subtitle={selected}>
                  <div className="grid gap-1">
                    {news.slice(0, 3).map((n: any, i: number) => (
                      <div key={i} className="px-2 py-1.5 rounded border border-hairline">
                        <p className="text-[11px] truncate">{n.title ?? n.headline ?? ''}</p>
                        <p className="mono text-[9px] text-warmgray mt-0.5">
                          {n.source ?? ''} · {fmtTime(n.published ?? n.date)}
                        </p>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}

              {/* Order Form */}
              <Panel title="Order Form" subtitle={`${selected} · human approval required`}>
                <div className="grid gap-3">
                  <div className="px-3 py-2 rounded border border-gold/30 bg-gold/5">
                    <p className="text-[11px] text-gold">
                      ADVISORY ONLY — All orders require your explicit confirmation before execution.
                      Review the order details carefully before approving.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="mono text-[9px] uppercase text-warmgray mb-1">Side</p>
                      <div className="flex gap-1">
                        {(['buy', 'sell'] as const).map((s) => (
                          <button key={s} onClick={() => setOrderSide(s)}
                            className={cls('flex-1 py-1.5 rounded border text-[11px] mono capitalize',
                              orderSide === s ? (s === 'buy' ? 'border-helgreen/40 bg-helgreen/10 text-helgreen' : 'border-helred/40 bg-helred/10 text-helred') : 'border-hairline text-warmgray')}>
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="mono text-[9px] uppercase text-warmgray mb-1">Order Type</p>
                      <div className="flex gap-1">
                        {(['market', 'limit'] as const).map((t) => (
                          <button key={t} onClick={() => setOrderType(t)}
                            className={cls('flex-1 py-1.5 rounded border text-[11px] mono capitalize',
                              orderType === t ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray')}>
                            {t}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="mono text-[9px] uppercase text-warmgray mb-1">Quantity (shares)</p>
                      <input className="w-full bg-obsidian border border-hairline rounded px-2 py-1.5 text-[12px] mono"
                        type="number" min="0" step="0.01" placeholder="0"
                        value={qty} onChange={(e) => setQty(e.target.value)} />
                    </div>
                    {orderType === 'limit' && (
                      <div>
                        <p className="mono text-[9px] uppercase text-warmgray mb-1">Limit Price ($)</p>
                        <input className="w-full bg-obsidian border border-hairline rounded px-2 py-1.5 text-[12px] mono"
                          type="number" min="0" step="0.01" placeholder="0.00"
                          value={limitPrice} onChange={(e) => setLimitPrice(e.target.value)} />
                      </div>
                    )}
                  </div>

                  <Button size="sm" variant="gold" onClick={doReview}
                    disabled={!qty || Number(qty) <= 0}>
                    Preview Order
                  </Button>

                  {/* Review result */}
                  {review && (
                    <div className={cls('rounded border p-3 grid gap-2',
                      review.error ? 'border-helred/40 bg-helred/5' : 'border-gold/40 bg-gold/5')}>
                      {review.error ? (
                        <p className="text-[12px] text-helred">{review.error}</p>
                      ) : (
                        <>
                          <div className="grid grid-cols-2 gap-2">
                            {[
                              ['Symbol', review.symbol],
                              ['Side', review.side],
                              ['Type', review.type ?? review.order_type],
                              ['Quantity', review.quantity],
                              ['Limit Price', review.limit_price ? `$${review.limit_price}` : 'Market'],
                              ['Est. Total', review.estimated_total ? `$${Number(review.estimated_total).toFixed(2)}` : '—'],
                            ].map(([k, v]) => (
                              <div key={k as string} className="flex gap-2">
                                <span className="mono text-[9px] uppercase text-warmgray">{k}:</span>
                                <span className="text-[11px] mono font-medium">{v ?? '—'}</span>
                              </div>
                            ))}
                          </div>

                          {!result && (
                            <>
                              <label className="flex items-center gap-2 cursor-pointer mt-1">
                                <input type="checkbox" checked={approved}
                                  onChange={(e) => setApproved(e.target.checked)}
                                  className="accent-gold" />
                                <span className="text-[11px]">
                                  I confirm this order and accept responsibility for its execution
                                </span>
                              </label>
                              <Button size="sm"
                                variant={approved ? 'gold' : undefined}
                                onClick={doPlace}
                                disabled={!approved || placing}>
                                {placing ? 'Placing…' : `PLACE ${orderSide.toUpperCase()} ORDER`}
                              </Button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}

                  {/* Execution result */}
                  {result && (
                    <div className={cls('rounded border p-3',
                      result.error ? 'border-helred/40 bg-helred/5 text-helred' : 'border-helgreen/40 bg-helgreen/5 text-helgreen')}>
                      <p className="text-[12px] font-medium">
                        {result.error ? `Order failed: ${result.error}` : `Order submitted: ${result.id ?? result.order_id ?? 'see Robinhood app'}`}
                      </p>
                      {!result.error && (
                        <p className="mono text-[10px] mt-1 text-warmgray">
                          State: {result.state ?? 'queued'} · Check Robinhood app for status.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </Panel>
            </>
          )}
        </div>
      </div>
    </Page>
  );
}

function taSignal(ta: any): string {
  const sum = ta?.summary ?? ta?.ta_summary;
  if (!sum) return '—';
  const sig = sum['1D'] ?? sum.daily ?? sum['1d'];
  if (!sig) return '—';
  return typeof sig === 'string' ? sig : (sig.summary ?? sig.signal ?? '—');
}

function fmtNum(v: any): string {
  const n = Number(v);
  if (isNaN(n) || v == null) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toFixed(0);
}

function fmtTime(v: any): string {
  if (!v) return '';
  try {
    const d = new Date(typeof v === 'number' ? v * 1000 : v);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch { return String(v); }
}
