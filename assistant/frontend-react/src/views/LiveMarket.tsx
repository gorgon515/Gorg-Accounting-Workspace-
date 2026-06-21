import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Live Market — TradingView real-time quotes, TA signals, and screener.
export function LiveMarket() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Live Market." />;
  const [symbol, setSymbol] = useState('NASDAQ:AAPL');
  const [input, setInput] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [interval, setInterval] = useState('1D');

  const quote = useAsync(() => helios.tradingview.quote(symbol), [symbol]);
  const ta = useAsync(() => helios.tradingview.ta(symbol, interval, true), [symbol, interval]);

  const q: any = quote.data ?? {};
  const taData: any = ta.data ?? {};
  const configured = q.configured !== false && !q.error;

  async function search() {
    if (!input.trim()) return;
    setSearching(true);
    try {
      const r = await helios.tradingview.search(input.trim());
      const list = Array.isArray(r) ? r : (r?.data ?? r?.results ?? []);
      setSearchResults(list.slice(0, 8));
    } finally { setSearching(false); }
  }

  function selectResult(sym: any) {
    const s = typeof sym === 'string' ? sym : (sym.symbol ?? sym.ticker ?? sym.id);
    const ex = typeof sym === 'string' ? '' : (sym.exchange ?? '');
    setSymbol(ex ? `${ex}:${s}` : s);
    setSearchResults([]);
    setInput('');
  }

  const intervals = ['1', '5', '15', '60', '240', '1D', '1W', '1M'];
  const taSum: any = taData.summary ?? taData.ta_summary ?? taData;
  const indicators: any = taData.indicators ?? taData.detailed_indicators ?? {};

  return (
    <Page title="Live Market" subtitle="TradingView · real-time quotes · technical analysis">
      <div className="grid gap-3">
        {/* Search */}
        <Panel title="Symbol Search">
          <div className="flex gap-2">
            <input
              className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
              placeholder="Search symbol or company… (e.g. AAPL, Tesla)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
            />
            <Button size="sm" variant="gold" onClick={search} disabled={searching}>
              {searching ? '…' : 'Search'}
            </Button>
          </div>
          {searchResults.length > 0 && (
            <div className="grid gap-1 mt-2 max-h-40 overflow-y-auto scroll-thin">
              {searchResults.map((r: any, n: number) => (
                <button key={n} onClick={() => selectResult(r)}
                  className="text-left px-2.5 py-1.5 rounded border border-hairline hover:bg-ivory/5 flex items-center gap-3">
                  <span className="mono text-[11px] text-gold w-20 truncate">
                    {typeof r === 'string' ? r : (r.symbol ?? r.ticker ?? r.id)}
                  </span>
                  <span className="text-[11px] text-ivory/70 truncate flex-1">
                    {r.description ?? r.name ?? r.full_name ?? ''}
                  </span>
                  <span className="mono text-[9px] text-warmgray">
                    {r.exchange ?? r.type ?? ''}
                  </span>
                </button>
              ))}
            </div>
          )}
        </Panel>

        {!configured && (
          <Panel title="Configuration Required">
            <p className="text-[12px] text-warmgray">
              Set <span className="mono text-gold">TRADINGVIEW_RAPIDAPI_KEY</span> environment variable to enable live market data.
            </p>
          </Panel>
        )}

        {/* Quote panel */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quote.loading ? <Loading /> : <>
            <MetricCard label="Price" value={q.price ?? q.last_price ?? q.close ?? '—'} accent
              sub={`${symbol.split(':').pop()}`} />
            <MetricCard label="Change" value={q.change_abs != null ? (q.change_abs > 0 ? '+' : '') + q.change_abs : '—'}
              sub={q.change_pct != null ? `${q.change_pct > 0 ? '+' : ''}${(q.change_pct ?? 0).toFixed(2)}%` : ''} />
            <MetricCard label="Volume" value={fmtNum(q.volume ?? q.vol)} />
            <MetricCard label="Market Cap" value={fmtNum(q.market_cap ?? q.marketcap)} />
          </>}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* TA Panel */}
          <Panel title="Technical Analysis"
            subtitle={`${symbol} · ${interval}`}
            actions={
              <div className="flex gap-1">
                {intervals.map((iv) => (
                  <button key={iv} onClick={() => setInterval(iv)}
                    className={cls('px-1.5 py-0.5 rounded border text-[9px] mono',
                      interval === iv ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>
                    {iv}
                  </button>
                ))}
              </div>
            }>
            {ta.loading ? <Loading /> : (
              <div className="grid gap-2">
                {taSum && (
                  <div className="grid grid-cols-3 gap-2">
                    {(['1m', '5m', '15m', '1h', '4h', '1D', '1W'] as const).map((tf) => {
                      const sig = taSum[tf] ?? taSum[tf.toLowerCase()];
                      if (!sig) return null;
                      const sigStr = typeof sig === 'string' ? sig : (sig.summary ?? sig.signal ?? '');
                      return (
                        <div key={tf} className="text-center px-2 py-1.5 rounded border border-hairline">
                          <p className="mono text-[9px] text-warmgray">{tf}</p>
                          <p className={cls('text-[11px] font-medium mt-0.5', signalColor(sigStr))}>
                            {sigStr || '—'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
                {Object.keys(indicators).length > 0 && (
                  <div className="grid gap-1 max-h-[300px] overflow-y-auto scroll-thin">
                    {Object.entries(indicators).slice(0, 20).map(([k, v]: any) => (
                      <div key={k} className="flex items-center gap-2 px-2 py-1 rounded border border-hairline">
                        <span className="mono text-[10px] text-warmgray w-24 truncate">{k}</span>
                        <span className="text-[11px] flex-1">{typeof v === 'object' ? JSON.stringify(v) : String(v ?? '—')}</span>
                      </div>
                    ))}
                  </div>
                )}
                {Object.keys(taSum ?? {}).length === 0 && Object.keys(indicators).length === 0 && (
                  <EmptyState message="TA data unavailable for this symbol." />
                )}
              </div>
            )}
          </Panel>

          {/* Quote details */}
          <Panel title="Quote Details" subtitle={q.name ?? q.description ?? ''}>
            {quote.loading ? <Loading /> : (
              <div className="grid gap-1.5">
                {[
                  ['Open', q.open],
                  ['High', q.high ?? q.high_price],
                  ['Low', q.low ?? q.low_price],
                  ['52W High', q['52_week_high'] ?? q.week_52_high],
                  ['52W Low', q['52_week_low'] ?? q.week_52_low],
                  ['Avg Vol', fmtNum(q.average_volume ?? q.avg_volume)],
                  ['P/E', q.pe_ratio ?? q.price_earnings_ratio],
                  ['EPS', q.eps ?? q.earnings_per_share],
                  ['Beta', q.beta],
                  ['Dividend', q.dividend_yield != null ? `${(q.dividend_yield * 100).toFixed(2)}%` : null],
                  ['Sector', q.sector],
                  ['Exchange', q.exchange ?? q.listed_exchange],
                  ['Currency', q.currency],
                  ['Session', q.market_status ?? q.session],
                ].filter(([, v]) => v != null && v !== '').map(([label, val]) => (
                  <div key={label as string} className="flex items-center gap-2 px-2 py-1 rounded border border-hairline">
                    <span className="mono text-[10px] text-warmgray w-24">{label}</span>
                    <span className="text-[12px]">{String(val)}</span>
                  </div>
                ))}
                {Object.keys(q).length === 0 && !quote.loading && (
                  <EmptyState message="Enter a symbol above to load quote data." />
                )}
              </div>
            )}
          </Panel>
        </div>

        {/* Quick screener */}
        <QuickScreener />
      </div>
    </Page>
  );
}

function QuickScreener() {
  const [preset, setPreset] = useState<'gainers' | 'losers' | 'volume' | 'value'>('gainers');
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  const presets = [
    { id: 'gainers', label: 'Top Gainers', sortBy: 'change|1D', order: 'desc' },
    { id: 'losers', label: 'Top Losers', sortBy: 'change|1D', order: 'asc' },
    { id: 'volume', label: 'High Volume', sortBy: 'volume|1D', order: 'desc' },
    { id: 'value', label: 'Value Screen', sortBy: 'PE', order: 'asc' },
  ] as const;

  async function run() {
    setBusy(true);
    const p = presets.find((x) => x.id === preset)!;
    try {
      const r = await helios.tradingview.screen({
        asset_type: 'stock', market: 'america',
        sort_by: p.sortBy, sort_order: p.order as any, limit: 20,
      });
      const rows = Array.isArray(r) ? r : (r?.data ?? r?.rows ?? []);
      setResults(rows);
    } finally { setBusy(false); }
  }

  return (
    <Panel title="Quick Screener" subtitle="TradingView stock screener"
      actions={
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {presets.map((p) => (
              <button key={p.id} onClick={() => setPreset(p.id)}
                className={cls('px-2 py-0.5 rounded border text-[10px] mono',
                  preset === p.id ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>
                {p.label}
              </button>
            ))}
          </div>
          <Button size="sm" variant="gold" onClick={run} disabled={busy}>{busy ? '…' : 'Run'}</Button>
        </div>
      }>
      {results.length === 0 ? (
        <EmptyState message="Run a screener preset to see results." />
      ) : (
        <div className="grid gap-1 max-h-[400px] overflow-y-auto scroll-thin">
          <div className="grid grid-cols-5 gap-2 px-2.5 py-1 mono text-[9px] uppercase text-warmgray">
            <span>Symbol</span><span>Name</span><span>Price</span><span>Change</span><span>Volume</span>
          </div>
          {results.map((row: any, n: number) => {
            const sym = row.s ?? row.symbol ?? row.ticker ?? '';
            const name = row.n ?? row.name ?? row.description ?? '';
            const price = row.d?.[0] ?? row.price ?? row.close ?? '—';
            const chg = row.d?.[1] ?? row.change ?? row.change_pct ?? '';
            const vol = row.d?.[2] ?? row.volume ?? '';
            return (
              <div key={n} className="grid grid-cols-5 gap-2 px-2.5 py-1.5 rounded border border-hairline text-[11px]">
                <span className="mono text-gold">{sym}</span>
                <span className="truncate text-ivory/80">{name}</span>
                <span className="mono">{price}</span>
                <span className={cls('mono', chg > 0 ? 'text-helgreen' : chg < 0 ? 'text-helred' : '')}>{chg}</span>
                <span className="mono text-warmgray">{fmtNum(vol)}</span>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function signalColor(sig: string): string {
  const s = (sig ?? '').toUpperCase();
  if (s.includes('STRONG_BUY') || s.includes('STRONG BUY')) return 'text-helgreen';
  if (s.includes('BUY')) return 'text-helgreen/80';
  if (s.includes('STRONG_SELL') || s.includes('STRONG SELL')) return 'text-helred';
  if (s.includes('SELL')) return 'text-helred/80';
  return 'text-warmgray';
}

function fmtNum(v: any): string {
  const n = Number(v);
  if (isNaN(n) || v == null) return '—';
  if (n >= 1e12) return `${(n / 1e12).toFixed(1)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toFixed(2);
}
