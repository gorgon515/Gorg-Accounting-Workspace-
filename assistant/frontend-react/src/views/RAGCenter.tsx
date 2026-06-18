import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Search', 'Models', 'Collections'] as const;
type Tab = typeof TABS[number];

export function RAGCenter() {
  const [tab, setTab] = useState<Tab>('Search');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for RAG search." />;
  return (
    <Page
      title="RAG Center"
      subtitle="hybrid semantic search · retrieval · embeddings"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Search' && <SearchTab />}
      {tab === 'Models' && <ModelsTab />}
      {tab === 'Collections' && <CollectionsTab />}
    </Page>
  );
}

function SearchTab() {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('');
  const [results, setResults] = useState<any[] | null>(null);
  const [context, setContext] = useState<string | null>(null);
  const [meta, setMeta] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await helios.rag.query({ question: query, n_results: 8, domain: domain || undefined });
      setResults(res.citations ?? []);
      setContext(res.context ?? null);
      setMeta({ confidence: res.confidence, hallucination_risk: res.hallucination_risk, n_docs: res.n_docs });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-3">
      <Panel title="Semantic Search">
        <div className="grid gap-2">
          <input
            className="w-full bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
            placeholder="Ask a question or search across your knowledge base…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
          <div className="flex items-center gap-2">
            <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs flex-1"
              value={domain} onChange={(e) => setDomain(e.target.value)}>
              <option value="">all domains</option>
              {['accounting', 'tax', 'finance', 'markets', 'strategy', 'general'].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <Button size="sm" variant="gold" onClick={search} disabled={busy || !query.trim()}>
              {busy ? 'Searching…' : 'Search'}
            </Button>
          </div>
        </div>
      </Panel>

      {meta && (
        <div className="grid grid-cols-3 gap-3">
          <MetricCard label="Confidence" value={`${Math.round((meta.confidence ?? 0) * 100)}%`} accent />
          <MetricCard label="Sources Found" value={meta.n_docs ?? 0} />
          <MetricCard label="Hallucination Risk"
            value={`${Math.round((meta.hallucination_risk ?? 0) * 100)}%`} />
        </div>
      )}

      {results !== null && (
        <Panel title="Retrieved Sources" subtitle="ranked by hybrid semantic + keyword score">
          {results.length === 0 ? (
            <EmptyState message="No relevant documents found. Ingest knowledge to enable search." />
          ) : (
            <div className="grid gap-2">
              {results.map((r: any) => (
                <div key={r.ref} className="rounded-lg border border-hairline px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="mono text-[10px] text-gold">[{r.ref}]</span>
                    <div className="flex items-center gap-2">
                      <span className="mono text-[10px] text-warmgray">{r.domain}</span>
                      <ScoreBar score={r.score} />
                      <span className="mono text-[10px] text-helgreen">{(r.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  {r.title && <p className="text-sm mt-0.5">{r.title}</p>}
                  {r.source && <p className="mono text-[10px] text-warmgray">{r.source}</p>}
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}

      {context && (
        <Panel title="Context Window" subtitle="assembled for generation">
          <pre className="mono text-[10px] text-warmgray whitespace-pre-wrap max-h-64 overflow-y-auto">{context}</pre>
        </Panel>
      )}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(score * 100, 100);
  return (
    <div className="w-16 h-1.5 rounded-full bg-ivory/10 overflow-hidden">
      <div className={cls('h-full rounded-full', pct >= 60 ? 'bg-helgreen' : pct >= 30 ? 'bg-gold' : 'bg-warmgray')}
        style={{ width: `${pct}%` }} />
    </div>
  );
}

function ModelsTab() {
  const models = useAsync(() => helios.rag.models(), []);
  const metrics = useAsync(() => helios.rag.metrics(), []);
  const [benchResult, setBenchResult] = useState<Record<string, any>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});

  async function bench(model: string) {
    setRunning((r) => ({ ...r, [model]: true }));
    try {
      const res = await helios.rag.benchmark(model, 10);
      setBenchResult((b) => ({ ...b, [model]: res }));
    } finally {
      setRunning((r) => ({ ...r, [model]: false }));
    }
  }

  const mods: any[] = models.data?.models ?? [];
  const m = metrics.data ?? {};

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Total Retrievals" value={m.total_retrievals ?? 0} accent />
        <MetricCard label="Avg Retrieval" value={`${m.avg_elapsed_ms ?? 0}ms`} />
      </div>
      <Panel title="Embedding Models">
        {models.loading ? <Loading /> : (
          <div className="grid gap-2">
            {mods.map((mod: any) => (
              <div key={mod.key} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm">{mod.key}</span>
                    <p className="mono text-[10px] text-warmgray">{mod.model_id}</p>
                    {mod.description && <p className="text-[11px] text-warmgray">{mod.description}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    {benchResult[mod.key] && (
                      <span className="mono text-[10px] text-gold">
                        {benchResult[mod.key].avg_ms_per_doc?.toFixed(1)}ms · d{benchResult[mod.key].dim}
                      </span>
                    )}
                    <Button size="sm" onClick={() => bench(mod.key)} disabled={running[mod.key]}>
                      {running[mod.key] ? '…' : 'Benchmark'}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function CollectionsTab() {
  const cols = useAsync(() => helios.rag.collections(), []);
  const list: any[] = cols.data?.collections ?? [];
  return (
    <Panel title="Vector Collections">
      {cols.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No vector collections yet. Ingest knowledge to create them." />
      ) : (
        <div className="grid gap-2">
          {list.map((c: any) => (
            <div key={c.name} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{c.name}</span>
                <div className="flex items-center gap-3 mono text-[10px] text-warmgray">
                  <span>{c.doc_count ?? 0} docs</span>
                  <span>{c.namespace}</span>
                  <span>{c.updated_at?.slice(0, 10)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
