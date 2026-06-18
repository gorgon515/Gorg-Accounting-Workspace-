import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Synthesize', 'Reports'] as const;
type Tab = typeof TABS[number];

export function ResearchCenter() {
  const [tab, setTab] = useState<Tab>('Synthesize');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for research synthesis." />;
  return (
    <Page
      title="Research Center"
      subtitle="multi-source synthesis · citation generation · gap analysis"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Synthesize' && <SynthesizeTab />}
      {tab === 'Reports' && <ReportsTab />}
    </Page>
  );
}

function SynthesizeTab() {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function synthesize() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await helios.synthesis.synthesize({
        query, n_sources: 8, domain: domain || undefined,
      });
      setResult(res);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-3">
      <Panel title="Research Query">
        <div className="grid gap-2">
          <textarea
            className="w-full bg-obsidian border border-hairline rounded px-3 py-2 text-sm resize-none"
            rows={3}
            placeholder="Enter a research question to synthesize across all knowledge sources…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs flex-1"
              value={domain} onChange={(e) => setDomain(e.target.value)}>
              <option value="">all domains</option>
              {['accounting', 'tax', 'finance', 'markets', 'strategy', 'general'].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <Button size="sm" variant="gold" onClick={synthesize} disabled={busy || !query.trim()}>
              {busy ? 'Synthesizing…' : 'Synthesize'}
            </Button>
          </div>
        </div>
      </Panel>

      {busy && <Loading />}

      {result && (
        <div className="grid gap-3">
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Sources Used" value={result.source_count ?? 0} accent />
            <MetricCard label="Confidence" value={`${Math.round((result.confidence ?? 0) * 100)}%`} />
            <MetricCard label="Halluc. Risk" value={`${Math.round((result.hallucination_risk ?? 0) * 100)}%`} />
          </div>

          <Panel title="Synthesis">
            <p className="text-[12px] text-ivory/90 leading-relaxed">{result.summary}</p>
          </Panel>

          {(result.consensus ?? []).length > 0 && (
            <Panel title="Consensus">
              <ul className="grid gap-1">
                {result.consensus.map((c: string, i: number) => (
                  <li key={i} className="text-[12px] text-helgreen">✓ {c}</li>
                ))}
              </ul>
            </Panel>
          )}

          {(result.conflicts ?? []).length > 0 && (
            <Panel title="Conflicts Detected">
              <ul className="grid gap-1">
                {result.conflicts.map((c: string, i: number) => (
                  <li key={i} className="text-[12px] text-helred">⚠ {c}</li>
                ))}
              </ul>
            </Panel>
          )}

          {(result.gaps ?? []).length > 0 && (
            <Panel title="Knowledge Gaps">
              <ul className="grid gap-1">
                {result.gaps.map((g: string, i: number) => (
                  <li key={i} className="text-[12px] text-gold">? {g}</li>
                ))}
              </ul>
            </Panel>
          )}

          {(result.citations ?? []).length > 0 && (
            <Panel title="Citations">
              <div className="grid gap-1">
                {result.citations.map((c: any) => (
                  <div key={c.ref} className="flex items-center gap-2 mono text-[10px]">
                    <span className="text-gold">[{c.ref}]</span>
                    <span className="text-warmgray">{c.domain}</span>
                    <span className="text-ivory/60">{c.source || '—'}</span>
                    <span className="text-helgreen">{(c.score * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}

function ReportsTab() {
  const stats = useAsync(() => helios.synthesis.stats(), []);
  const reports = useAsync(() => helios.synthesis.reports(), []);
  const list: any[] = reports.data?.reports ?? [];
  const s = stats.data ?? {};

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Total Reports" value={s.total_reports ?? 0} accent />
        <MetricCard label="Avg Confidence" value={`${Math.round((s.avg_confidence ?? 0) * 100)}%`} />
      </div>
      <Panel title="Research Reports">
        {reports.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No synthesis reports yet. Use the Synthesize tab to create one." />
        ) : (
          <div className="grid gap-2">
            {list.map((r: any) => (
              <div key={r.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{r.query}</p>
                    <p className="text-[11px] text-warmgray mt-0.5 line-clamp-2">{r.summary}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="mono text-[10px] text-gold">{(r.confidence * 100).toFixed(0)}% conf</span>
                    <span className="mono text-[10px] text-warmgray">{r.created_at?.slice(0, 10)}</span>
                  </div>
                </div>
                <div className="flex gap-3 mt-1 mono text-[10px] text-warmgray">
                  <span>{r.source_count ?? 0} sources</span>
                  {(r.conflicts ?? []).length > 0 && (
                    <span className="text-helred">{r.conflicts.length} conflict{r.conflicts.length > 1 ? 's' : ''}</span>
                  )}
                  {(r.gaps ?? []).length > 0 && (
                    <span className="text-gold">{r.gaps.length} gap{r.gaps.length > 1 ? 's' : ''}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
