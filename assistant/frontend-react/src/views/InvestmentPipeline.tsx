import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

// Investment Pipeline — the ranked idea funnel with anti-MAG7 diversification
// controls, plus a full generated investment memo for any candidate.
export function InvestmentPipeline() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Investment Pipeline." />;
  const [excludeMega, setExcludeMega] = useState(true);
  const [penalizeCoverage, setPenalizeCoverage] = useState(true);
  const [overlap, setOverlap] = useState('');
  const [limit, setLimit] = useState(25);

  const params = {
    limit,
    exclude_mega_cap: excludeMega,
    penalize_coverage: penalizeCoverage,
    portfolio_overlap: overlap.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
  };
  const ranked = useAsync(() => helios.discovery.rank(params), [excludeMega, penalizeCoverage, overlap, limit]);
  const [memoSym, setMemoSym] = useState<string | null>(null);
  const memo = useAsync(() => (memoSym ? helios.discovery.memo(memoSym) : Promise.resolve(null)), [memoSym]);

  const list: any[] = Array.isArray(ranked.data) ? ranked.data : (ranked.data?.ideas ?? []);

  return (
    <Page title="Investment Pipeline" subtitle="multi-factor ranking · diversification penalties · memos">
      <div className="grid gap-3">
        <Panel title="Ranking Controls">
          <div className="flex flex-wrap items-center gap-2">
            <Toggle label="Exclude mega-cap" on={excludeMega} onClick={() => setExcludeMega(!excludeMega)} />
            <Toggle label="Penalize over-coverage" on={penalizeCoverage} onClick={() => setPenalizeCoverage(!penalizeCoverage)} />
            <div className="flex items-center gap-1.5">
              {[10, 25, 50, 100].map((n) => (
                <button key={n} onClick={() => setLimit(n)}
                  className={cls('px-2 py-0.5 rounded border text-[10px] mono',
                    limit === n ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>top{n}</button>
              ))}
            </div>
          </div>
          <input className="w-full mt-2 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
            placeholder="Exclude portfolio overlap — tickers, comma-separated"
            value={overlap} onChange={(e) => setOverlap(e.target.value)} />
        </Panel>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="Ranked Ideas" subtitle={`${list.length} candidates`}>
            {ranked.loading ? <Loading /> : list.length === 0 ? (
              <EmptyState message="No ranked ideas — refresh the universe in the Discovery Center." />
            ) : (
              <div className="grid gap-1.5 max-h-[520px] overflow-y-auto scroll-thin">
                {list.map((i: any, n: number) => (
                  <div key={i.symbol}
                    className={cls('flex items-center gap-2 px-2 py-1.5 rounded border cursor-pointer hover:bg-ivory/5',
                      memoSym === i.symbol ? 'border-gold/40 bg-gold/5' : 'border-hairline')}
                    onClick={() => setMemoSym(i.symbol)}>
                    <span className="mono text-[10px] text-warmgray w-5">{n + 1}</span>
                    <span className="mono text-[12px] w-16">{i.symbol}</span>
                    <span className="flex-1 text-[12px] truncate text-warmgray">{i.name}</span>
                    <span className="mono text-[9px] text-ivory/50">{i.sector}</span>
                    <span className="mono text-[11px] text-gold w-10 text-right">{fmtNum(i.composite)}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title={memoSym ? `Investment Memo — ${memoSym}` : 'Investment Memo'}
            subtitle="select an idea to generate">
            {!memoSym ? (
              <EmptyState message="Select a ranked idea to generate its memo." />
            ) : memo.loading ? <Loading /> : !memo.data ? (
              <EmptyState message="No memo available." />
            ) : <Memo m={memo.data} />}
          </Panel>
        </div>
      </div>
    </Page>
  );
}

function Memo({ m }: { m: any }) {
  return (
    <div className="grid gap-3 max-h-[520px] overflow-y-auto scroll-thin">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Confidence" value={`${fmtNum(m.confidence_score)}`} accent />
        <MetricCard label="Valuation" value={String(m.valuation?.read ?? m.valuation?.verdict ?? '—')} />
      </div>
      <Section title="Business overview"><p className="text-[12px] text-ivory/80">{m.business_overview}</p></Section>
      <BulletSection title="Bull case" items={m.bull_case} accent="text-helgreen" />
      <BulletSection title="Bear case" items={m.bear_case} accent="text-helred" />
      <BulletSection title="Risks" items={m.risks} accent="text-gold" />
      <BulletSection title="Catalysts" items={m.catalysts} accent="text-helgreen" />
      {m.competitive_position && (
        <Section title="Competitive position"><p className="text-[12px] text-ivory/80">{m.competitive_position}</p></Section>
      )}
      {m.valuation && (
        <Section title="Valuation detail">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
            {Object.entries(m.valuation).filter(([k]) => !['read', 'verdict'].includes(k)).map(([k, v]: any) => (
              <KV key={k} k={k} v={v} />
            ))}
          </div>
        </Section>
      )}
      {m.quality_analysis && (
        <Section title="Quality analysis">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
            {Object.entries(m.quality_analysis).map(([k, v]: any) => <KV key={k} k={k} v={v} />)}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: any }) {
  return (
    <div>
      <p className="mono text-[10px] uppercase tracking-wider text-warmgray mb-1">{title}</p>
      {children}
    </div>
  );
}

function BulletSection({ title, items, accent }: { title: string; items: any[]; accent: string }) {
  const list = Array.isArray(items) ? items : [];
  if (list.length === 0) return null;
  return (
    <Section title={title}>
      <ul className="grid gap-1">
        {list.map((it: any, n: number) => (
          <li key={n} className="flex gap-1.5 text-[12px] text-ivory/80">
            <span className={cls('mono', accent)}>•</span><span>{typeof it === 'string' ? it : it.text ?? JSON.stringify(it)}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function KV({ k, v }: { k: string; v: any }) {
  return (
    <div className="flex items-center justify-between text-[10px] px-1.5 py-1 rounded bg-ivory/5">
      <span className="text-warmgray capitalize">{k.replace(/_/g, ' ')}</span>
      <span className="mono text-gold">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
    </div>
  );
}

function Toggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={cls('flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-[11px] transition-colors',
        on ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray hover:bg-ivory/5')}>
      <span className={cls('w-2 h-2 rounded-full', on ? 'bg-gold' : 'bg-warmgray')} />{label}
    </button>
  );
}

function fmtNum(v: any): string {
  return typeof v === 'number' ? v.toFixed(1) : '—';
}
