import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Table, MetricCard, EmptyState, Loading, Button } from '../components';
import type { Column } from '../components';
import { fmtMoney, fmtPct, dirColor, cls } from '../lib/format';

const DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'META', 'SPY', 'QQQ', 'BTC'];

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1D', '1W'] as const;
type Interval = typeof INTERVALS[number];

interface QuoteRow { symbol: string; price?: number; change?: number; changePercent?: number; volume?: number; marketCap?: number }

function sigLabel(rec: string | undefined) {
  if (!rec) return null;
  const r = rec.toUpperCase();
  if (r.includes('STRONG_BUY') || r.includes('STRONG BUY')) return { label: 'Strong Buy', color: 'text-helgreen' };
  if (r.includes('BUY')) return { label: 'Buy', color: 'text-helgreen/80' };
  if (r.includes('STRONG_SELL') || r.includes('STRONG SELL')) return { label: 'Strong Sell', color: 'text-red-400' };
  if (r.includes('SELL')) return { label: 'Sell', color: 'text-red-400/80' };
  return { label: 'Neutral', color: 'text-warmgray' };
}

export function Markets() {
  const [sym, setSym] = useState<string>('AAPL');
  const [interval, setInterval] = useState<Interval>('1D');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const quotes = useAsync(async () => {
    const results: QuoteRow[] = [];
    for (const s of DEFAULT_SYMBOLS) {
      try {
        const q = await helios.tradingview.quote(s, 'regular');
        results.push({
          symbol: s,
          price: q.price ?? q.last_price,
          change: q.change ?? q.price_change,
          changePercent: q.change_percent ?? q.price_change_percent,
          volume: q.volume,
          marketCap: q.market_cap,
        });
      } catch {
        results.push({ symbol: s });
      }
    }
    return results;
  }, [], 30000);

  const detail = useAsync(() => helios.tradingview.quote(sym, 'regular'), [sym], 15000);
  const ta = useAsync(() => helios.tradingview.ta(sym, interval, false), [sym, interval]);
  const news = useAsync(() => helios.tradingview.news({ symbol: sym, market: 'stock', limit: 5, offset: 0 }), [sym]);

  async function search() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const r = await helios.tradingview.search(query.trim(), 'stock');
      setSearchResults((r?.results ?? r ?? []).slice(0, 8));
    } catch {
      setSearchResults([]);
    } finally { setSearching(false); }
  }

  const cols: Column<QuoteRow>[] = [
    { key: 's', header: 'Symbol', render: (q) => <span className="text-ivory font-medium">{q.symbol}</span> },
    { key: 'p', header: 'Price', align: 'right', render: (q) => q.price != null ? fmtMoney(q.price) : '—' },
    { key: 'c', header: 'Chg%', align: 'right', render: (q) => q.changePercent != null
      ? <span className={dirColor(q.changePercent)}>{fmtPct(q.changePercent)}</span> : '—' },
    { key: 'v', header: 'Vol', align: 'right', render: (q) => q.volume != null
      ? <span className="mono text-[10px] text-warmgray">{(q.volume / 1e6).toFixed(1)}M</span> : '—' },
  ];

  const q = detail.data;
  const sig = sigLabel(ta.data?.recommendation ?? ta.data?.signal);

  return (
    <Page title="Markets" subtitle="TradingView live data · technical analysis · news">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Last price" accent value={q?.price != null ? fmtMoney(q.price) : '—'} sub={sym} />
        <MetricCard label="Change" value={q?.change_percent != null
          ? <span className={dirColor(q.change_percent)}>{fmtPct(q.change_percent)}</span> : '—'} />
        <MetricCard label="Volume" value={q?.volume != null ? `${(q.volume / 1e6).toFixed(1)}M` : '—'} />
        <MetricCard label="TA Signal" value={sig ? <span className={sig.color}>{sig.label}</span> : '—'} sub={interval} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Left: watchlist + search */}
        <div className="flex flex-col gap-3">
          <Panel title="Symbol search">
            <div className="flex gap-2">
              <input
                className="flex-1 bg-obsidian border border-hairline rounded px-2.5 py-1.5 text-[12px] mono focus:border-gold/40 outline-none"
                placeholder="e.g. TSLA, Apple…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && search()}
              />
              <Button size="sm" variant="ghost" onClick={search} disabled={searching}>
                {searching ? '…' : 'Go'}
              </Button>
            </div>
            {searchResults.length > 0 && (
              <div className="mt-2 flex flex-col gap-1">
                {searchResults.map((r) => (
                  <button key={r.symbol ?? r.ticker}
                    className="text-left px-2 py-1 rounded hover:bg-ivory/5 text-[12px]"
                    onClick={() => { setSym(r.symbol ?? r.ticker); setSearchResults([]); setQuery(''); }}>
                    <span className="text-ivory font-medium">{r.symbol ?? r.ticker}</span>
                    <span className="text-warmgray ml-2">{r.description ?? r.name ?? ''}</span>
                  </button>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Watchlist" subtitle="TradingView live" scroll className="max-h-[400px]">
            {quotes.loading ? <Loading /> : (
              <Table columns={cols} rows={quotes.data ?? []}
                empty="Fetching quotes…"
                onRow={(q) => setSym(q.symbol)} />
            )}
          </Panel>
        </div>

        {/* Center: TA + intervals */}
        <div className="flex flex-col gap-3">
          <Panel title={`Technical Analysis · ${sym}`}
            actions={
              <div className="flex gap-1">
                {INTERVALS.map((i) => (
                  <button key={i}
                    className={cls('mono text-[9px] px-1.5 py-0.5 rounded',
                      i === interval ? 'bg-gold text-obsidian' : 'text-warmgray hover:text-ivory')}
                    onClick={() => setInterval(i)}>{i}</button>
                ))}
              </div>
            }>
            {ta.loading ? <Loading /> : !ta.data ? <EmptyState message="No TA data." /> : (
              <div className="flex flex-col gap-2 text-[12px]">
                {sig && (
                  <div className={cls('font-medium text-[14px]', sig.color)}>{sig.label}</div>
                )}
                {['oscillators', 'moving_averages', 'summary'].map((section) => {
                  const d = ta.data?.[section];
                  if (!d) return null;
                  return (
                    <div key={section}>
                      <div className="mono text-[10px] uppercase text-warmgray mb-1">{section.replace('_', ' ')}</div>
                      <div className="flex gap-3 text-[11px]">
                        {d.buy != null && <span className="text-helgreen">Buy {d.buy}</span>}
                        {d.neutral != null && <span className="text-warmgray">Neutral {d.neutral}</span>}
                        {d.sell != null && <span className="text-red-400">Sell {d.sell}</span>}
                      </div>
                    </div>
                  );
                })}
                {ta.data?.indicators && (
                  <div>
                    <div className="mono text-[10px] uppercase text-warmgray mb-1">Key indicators</div>
                    <div className="grid grid-cols-2 gap-1">
                      {Object.entries(ta.data.indicators).slice(0, 8).map(([k, v]: any) => (
                        <div key={k} className="flex justify-between text-[11px]">
                          <span className="text-warmgray uppercase">{k}</span>
                          <span className="mono text-ivory">{typeof v === 'number' ? v.toFixed(2) : v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Panel>

          <Panel title="Quote detail" subtitle={sym}>
            {detail.loading ? <Loading /> : !q ? <EmptyState message="No quote data." /> : (
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                {[
                  ['Open', q.open], ['High', q.high], ['Low', q.low],
                  ['52W High', q.week_52_high ?? q['52_week_high']],
                  ['52W Low', q.week_52_low ?? q['52_week_low']],
                  ['Mkt Cap', q.market_cap != null ? `$${(q.market_cap / 1e9).toFixed(1)}B` : null],
                  ['P/E', q.pe_ratio ?? q.price_earnings_ttm],
                  ['EPS', q.earnings_per_share ?? q.eps_ttm],
                ].filter(([, v]) => v != null).map(([k, v]: any) => (
                  <div key={k} className="flex justify-between border-b border-hairline pb-1">
                    <span className="text-warmgray">{k}</span>
                    <span className="mono text-ivory">{typeof v === 'number' ? v.toLocaleString() : v}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        {/* Right: news */}
        <Panel title={`News · ${sym}`} scroll className="max-h-[560px]">
          {news.loading ? <Loading /> : !(news.data?.items ?? news.data)?.length
            ? <EmptyState message="No news." />
            : (news.data?.items ?? news.data ?? []).map((n: any, i: number) => (
              <div key={i} className="border-b border-hairline pb-2 mb-2 last:border-0 last:mb-0">
                <div className="text-[12px] text-ivory leading-snug">{n.title ?? n.headline}</div>
                <div className="mono text-[9px] text-warmgray mt-0.5">
                  {n.source ?? n.provider} · {n.published_at ?? n.date ?? ''}
                </div>
              </div>
            ))}
        </Panel>
      </div>
    </Page>
  );
}
