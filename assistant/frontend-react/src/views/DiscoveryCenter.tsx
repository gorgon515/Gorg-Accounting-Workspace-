import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Investment Discovery — overview of the opportunity-discovery engine: the
// market universe, the day's surfaced ideas, and the daily discovery scan.
export function DiscoveryCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Discovery Center." />;
  const stats = useAsync(() => helios.discovery.universeStats(), []);
  const ideas = useAsync(() => helios.discovery.ideas('top10'), []);
  const daily = useAsync(() => helios.discovery.dailyLatest(), []);
  const [busy, setBusy] = useState(false);

  const s = stats.data ?? ({} as any);
  const ideaList: any[] = Array.isArray(ideas.data) ? ideas.data : (ideas.data?.ideas ?? []);
  const run = daily.data ?? ({} as any);

  async function runDaily() {
    setBusy(true);
    try { await helios.discovery.daily(); daily.reload(); ideas.reload(); }
    finally { setBusy(false); }
  }
  async function seed() {
    setBusy(true);
    try { await helios.discovery.seed(); stats.reload(); ideas.reload(); }
    finally { setBusy(false); }
  }

  const sectors: Array<[string, number]> = Object.entries(s.by_sector ?? {}) as any;
  const tiers: Array<[string, number]> = Object.entries(s.by_cap_tier ?? {}) as any;

  return (
    <Page title="Discovery Center" subtitle="opportunity discovery · anti-crowd · overlooked names"
      actions={
        <div className="flex gap-1.5">
          <Button size="sm" variant="ghost" onClick={seed} disabled={busy}>Refresh Universe</Button>
          <Button size="sm" variant="gold" onClick={runDaily} disabled={busy}>{busy ? 'Scanning…' : 'Run Daily Scan'}</Button>
        </div>
      }>
      <div className="grid gap-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Universe" value={s.total ?? '—'} sub="securities tracked" accent />
          <MetricCard label="Sectors" value={sectors.length || '—'} />
          <MetricCard label="Exchanges" value={s.exchanges ?? (s.by_exchange ? Object.keys(s.by_exchange).length : '—')} />
          <MetricCard label="Micro + Small" value={(s.by_cap_tier?.micro ?? 0) + (s.by_cap_tier?.small ?? 0)} sub="overlooked tiers" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="Top 10 Ideas" subtitle="ranked · MAG7-penalized">
            {ideas.loading ? <Loading /> : ideaList.length === 0 ? (
              <EmptyState message="No ideas yet — run a daily scan or refresh the universe." />
            ) : (
              <div className="grid gap-1.5">
                {ideaList.slice(0, 10).map((i: any, n: number) => (
                  <div key={i.symbol} className="flex items-center gap-2 px-2 py-1.5 rounded border border-hairline">
                    <span className="mono text-[10px] text-warmgray w-5">{n + 1}</span>
                    <span className="mono text-[12px] w-16">{i.symbol}</span>
                    <span className="flex-1 text-[12px] truncate text-warmgray">{i.name}</span>
                    <span className="mono text-[10px] text-ivory/60">{i.sector}</span>
                    <span className="mono text-[11px] text-gold w-10 text-right">{fmtNum(i.composite)}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Universe Composition">
            {stats.loading ? <Loading /> : (
              <div className="grid gap-3">
                <div>
                  <p className="mono text-[10px] uppercase text-warmgray mb-1.5">By cap tier</p>
                  <div className="grid gap-1">
                    {tiers.map(([tier, n]) => (
                      <Bar key={tier} label={tier} value={n} total={s.total || 1} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mono text-[10px] uppercase text-warmgray mb-1.5">By sector</p>
                  <div className="grid gap-1 max-h-[180px] overflow-y-auto scroll-thin">
                    {sectors.sort((a, b) => b[1] - a[1]).map(([sec, n]) => (
                      <Bar key={sec} label={sec} value={n} total={s.total || 1} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </Panel>
        </div>

        <Panel title="Daily Discovery" subtitle={run.run_date ? `last run ${run.run_date}` : 'not run yet'}>
          {daily.loading ? <Loading /> : !run.run_date ? (
            <EmptyState message="Run the daily scan to surface new, improving and deteriorating opportunities." />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <Bucket title="New opportunities" items={run.new_opportunities} accent="text-helgreen" />
              <Bucket title="Improving" items={run.improving} accent="text-helgreen" />
              <Bucket title="Deteriorating" items={run.deteriorating} accent="text-helred" />
              <Bucket title="Insider activity" items={run.insider_activity} accent="text-gold" />
              <Bucket title="Earnings surprises" items={run.earnings_surprises} accent="text-gold" />
              <Bucket title="Valuation dislocations" items={run.valuation_dislocations} accent="text-ivory" />
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function Bar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = Math.round((value / total) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] w-24 truncate capitalize">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
        <div className="h-full rounded-full bg-gold/70" style={{ width: `${pct}%` }} />
      </div>
      <span className="mono text-[10px] text-warmgray w-8 text-right">{value}</span>
    </div>
  );
}

function Bucket({ title, items, accent }: { title: string; items: any[]; accent: string }) {
  const list = Array.isArray(items) ? items : [];
  return (
    <div className="rounded-lg border border-hairline p-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] text-warmgray">{title}</span>
        <span className={cls('mono text-[11px]', accent)}>{list.length}</span>
      </div>
      <div className="grid gap-0.5">
        {list.slice(0, 6).map((it: any, n: number) => (
          <div key={n} className="flex items-center gap-1.5 text-[11px]">
            <span className="mono w-14">{it.symbol ?? it}</span>
            <span className="text-warmgray truncate flex-1">{it.note ?? it.name ?? ''}</span>
          </div>
        ))}
        {list.length === 0 && <span className="text-[10px] text-warmgray">—</span>}
      </div>
    </div>
  );
}

function fmtNum(v: any): string {
  return typeof v === 'number' ? v.toFixed(1) : '—';
}
