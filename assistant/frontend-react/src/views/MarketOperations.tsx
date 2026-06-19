import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Daily Brief', 'Macro', 'Filings', 'Watchlist'] as const;
type Tab = typeof TABS[number];

export function MarketOperations() {
  const [tab, setTab] = useState<Tab>('Daily Brief');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for Market Operations." />;
  return (
    <Page
      title="Market Operations"
      subtitle="market intelligence center · daily briefs · macro monitor"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Daily Brief' && <BriefTab />}
      {tab === 'Macro' && <MacroTab />}
      {tab === 'Filings' && <FilingsTab />}
      {tab === 'Watchlist' && <WatchlistTab />}
    </Page>
  );
}

function BriefTab() {
  const brief = useAsync(() => helios.marketIntel.latestBrief(), []);
  const [busy, setBusy] = useState(false);
  const b: any = brief.data ?? {};

  async function generate() {
    setBusy(true);
    try { await helios.marketIntel.generateBrief(); brief.reload(); }
    finally { setBusy(false); }
  }

  const hasBrief = b && b.headline;
  return (
    <div className="grid gap-3">
      <div className="flex justify-end">
        <Button size="sm" variant="gold" onClick={generate} disabled={busy}>
          {busy ? 'Generating…' : 'Generate Today’s Brief'}
        </Button>
      </div>
      {brief.loading ? <Loading /> : !hasBrief ? (
        <EmptyState message="No market brief yet. Generate one to assemble the daily intelligence digest." />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Sentiment" value={b.sentiment ?? 'neutral'} accent />
            <MetricCard label="Risk Score" value={`${Math.round((b.risk_score ?? 0.5) * 100)}%`} />
            <MetricCard label="Date" value={String(b.date ?? '').slice(0, 10)} />
          </div>
          <Panel title={b.headline}>
            <p className="text-sm text-ivory/90 whitespace-pre-wrap">{b.executive_summary}</p>
          </Panel>
          {Array.isArray(b.key_events) && b.key_events.length > 0 && (
            <Panel title="Key Events">
              <ul className="grid gap-1">
                {b.key_events.map((e: string, i: number) => (
                  <li key={i} className="text-[12px] text-warmgray">• {e}</li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}

function MacroTab() {
  const series = ['GDP', 'CPIAUCSL', 'UNRATE', 'FEDFUNDS', 'GS10'];
  const data = useAsync(async () => {
    const out: Record<string, any[]> = {};
    for (const s of series) {
      try { out[s] = await helios.financialHub.economic(s, 2); } catch { out[s] = []; }
    }
    return out;
  }, []);
  const d = data.data ?? {};
  const labels: Record<string, string> = {
    GDP: 'GDP', CPIAUCSL: 'CPI', UNRATE: 'Unemployment', FEDFUNDS: 'Fed Funds', GS10: '10Y Treasury',
  };
  return (
    <Panel title="Macro Monitor" subtitle="latest economic indicators from the Financial Data Hub">
      {data.loading ? <Loading /> : (
        <div className="grid grid-cols-5 gap-3">
          {series.map((s) => {
            const rows = d[s] ?? [];
            const cur = rows[0]?.value;
            const prev = rows[1]?.value;
            const up = cur != null && prev != null && cur >= prev;
            return (
              <MetricCard key={s} label={labels[s]}
                value={cur != null ? Number(cur).toFixed(2) : '—'}
                delta={cur != null && prev != null ? { text: up ? '▲' : '▼', up } : undefined} />
            );
          })}
        </div>
      )}
      {!data.loading && Object.values(d).every((r: any) => !r.length) && (
        <EmptyState message="No economic data yet. Poll FRED/BLS connectors to populate the hub." />
      )}
    </Panel>
  );
}

function FilingsTab() {
  const filings = useAsync(() => helios.financialHub.filings({ limit: 30 }), []);
  const list: any[] = Array.isArray(filings.data) ? filings.data : [];
  return (
    <Panel title="SEC Filings" subtitle="material filings from the Financial Data Hub">
      {filings.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No filings ingested yet. Poll the SEC EDGAR connector." />
      ) : (
        <div className="grid gap-2">
          {list.map((f: any) => (
            <div key={f.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div>
                <span className="text-sm">{f.entity}</span>
                <p className="mono text-[10px] text-warmgray">CIK {f.cik}</p>
              </div>
              <div className="flex items-center gap-3 mono text-[10px] text-warmgray">
                <span className="text-gold">{f.form}</span>
                <span>{f.filing_date}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function WatchlistTab() {
  const wl = useAsync(() => helios.financialHub.watchlist(), []);
  const [symbol, setSymbol] = useState('');
  const list: any[] = Array.isArray(wl.data) ? wl.data : [];

  async function add() {
    if (!symbol.trim()) return;
    await helios.financialHub.addWatchlist({ symbol: symbol.toUpperCase() });
    setSymbol('');
    wl.reload();
  }

  return (
    <Panel title="Watchlist"
      actions={
        <div className="flex gap-1">
          <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs w-20"
            placeholder="TICKER" value={symbol} onChange={(e) => setSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()} />
          <Button size="sm" onClick={add}>Add</Button>
        </div>
      }
    >
      {wl.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="Watchlist is empty. Add a ticker to track it." />
      ) : (
        <div className="grid gap-2">
          {list.map((w: any) => (
            <div key={w.symbol} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div>
                <span className={cls('text-sm font-medium')}>{w.symbol}</span>
                {w.name && <span className="text-[11px] text-warmgray ml-2">{w.name}</span>}
              </div>
              <div className="flex items-center gap-3">
                {w.sector && <span className="mono text-[10px] text-warmgray">{w.sector}</span>}
                <Button size="sm" variant="ghost" onClick={() => helios.financialHub.removeWatchlist(w.symbol).then(() => wl.reload())}>
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
