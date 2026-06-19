import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Library', 'Gaps', 'Conflicts', 'Memory'] as const;
type Tab = typeof TABS[number];

const DOMAIN_COLORS: Record<string, string> = {
  accounting: 'text-gold', tax: 'text-helred', finance: 'text-helgreen',
  markets: 'text-helgreen', strategy: 'text-ivory', general: 'text-warmgray',
};

export function KnowledgeCenter() {
  const [tab, setTab] = useState<Tab>('Library');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Knowledge Center." />;
  return (
    <Page
      title="Knowledge Center"
      subtitle="institutional memory · knowledge graph · quality"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Library' && <LibraryTab />}
      {tab === 'Gaps' && <GapsTab />}
      {tab === 'Conflicts' && <ConflictsTab />}
      {tab === 'Memory' && <MemoryTab />}
    </Page>
  );
}

function LibraryTab() {
  const health = useAsync(() => helios.knowledge.health(), []);
  const items = useAsync(() => helios.knowledge.list(), []);
  const [domain, setDomain] = useState('');
  const filtered = useAsync(() => helios.knowledge.list(domain ? { domain } : {}), [domain]);

  const h = health.data ?? {};
  const list: any[] = (domain ? filtered.data?.items : items.data?.items) ?? [];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Items" value={h.total_items ?? 0} accent />
        <MetricCard label="Avg Quality" value={`${Math.round((h.avg_quality ?? 0) * 100)}%`} />
        <MetricCard label="Open Conflicts" value={h.open_conflicts ?? 0} />
        <MetricCard label="Knowledge Gaps" value={h.open_gaps ?? 0} />
      </div>
      {h.by_domain && (
        <Panel title="Coverage by Domain">
          <div className="flex flex-wrap gap-2">
            {Object.entries(h.by_domain).map(([d, cnt]) => (
              <span key={d}
                className={cls('mono text-[10px] px-2 py-0.5 rounded border border-hairline cursor-pointer',
                  domain === d ? 'border-gold' : '',
                  DOMAIN_COLORS[d] ?? 'text-warmgray')}
                onClick={() => setDomain(domain === d ? '' : d)}>
                {d} · {cnt as number}
              </span>
            ))}
          </div>
        </Panel>
      )}
      <Panel title="Knowledge Items" subtitle={domain ? `filtered: ${domain}` : 'all domains'}>
        {(domain ? filtered.loading : items.loading) ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No knowledge items. Ingest documents to build the knowledge base." />
        ) : (
          <div className="grid gap-2">
            {list.map((item: any) => (
              <div key={item.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-sm">{item.title}</span>
                    <div className="flex gap-2 mt-0.5">
                      <span className={cls('mono text-[10px]', DOMAIN_COLORS[item.domain] ?? 'text-warmgray')}>
                        {item.domain}
                      </span>
                      <span className="mono text-[10px] text-warmgray">{item.kind}</span>
                      <span className="mono text-[10px] text-warmgray">v{item.version}</span>
                    </div>
                  </div>
                  <QualityBadge score={item.quality_score} />
                </div>
                <p className="text-[11px] text-warmgray mt-1 line-clamp-2">{item.content}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function QualityBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <span className={cls('mono text-[10px] shrink-0',
      pct >= 70 ? 'text-helgreen' : pct >= 40 ? 'text-gold' : 'text-warmgray')}>
      Q {pct}%
    </span>
  );
}

function GapsTab() {
  const gaps = useAsync(() => helios.knowledge.gaps('open'), []);
  const list: any[] = gaps.data?.gaps ?? [];
  return (
    <Panel title="Knowledge Gaps" subtitle="domains where knowledge is missing or insufficient">
      {gaps.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No open knowledge gaps identified." />
      ) : (
        <div className="grid gap-2">
          {list.map((g: any) => (
            <div key={g.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{g.description}</span>
                <span className={cls('mono text-[10px]',
                  g.priority >= 0.7 ? 'text-helred' : g.priority >= 0.4 ? 'text-gold' : 'text-warmgray')}>
                  {g.domain} · p{Math.round(g.priority * 100)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function ConflictsTab() {
  const conflicts = useAsync(() => helios.knowledge.conflicts(false), []);
  const list: any[] = conflicts.data?.conflicts ?? [];
  return (
    <Panel title="Knowledge Conflicts" subtitle="contradictions and duplicates requiring resolution">
      {conflicts.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No open knowledge conflicts. Knowledge base is consistent." />
      ) : (
        <div className="grid gap-2">
          {list.map((c: any) => (
            <div key={c.id} className="rounded-lg border border-hairline border-helred/30 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="mono text-[10px] text-helred uppercase">{c.conflict_type}</span>
                <span className="mono text-[10px] text-warmgray">{c.created_at?.slice(0, 10)}</span>
              </div>
              <p className="text-[12px] text-warmgray mt-1">{c.description}</p>
              <div className="mono text-[10px] text-warmgray mt-1">
                items: {c.item_a?.slice(0, 8)}… · {c.item_b?.slice(0, 8)}…
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function MemoryTab() {
  const stats = useAsync(() => helios.institutionalMemory.stats(), []);
  const events = useAsync(() => helios.institutionalMemory.list(), []);
  const list: any[] = events.data?.events ?? [];
  const s = stats.data ?? {};

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Events" value={s.total_events ?? 0} accent />
        <MetricCard label="Decisions" value={s.by_type?.decision ?? 0} />
        <MetricCard label="Lessons" value={s.by_type?.lesson_learned ?? 0} />
        <MetricCard label="Avg Confidence" value={`${Math.round((s.avg_confidence ?? 0) * 100)}%`} />
      </div>
      <Panel title="Institutional Memory">
        {events.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No institutional memory recorded yet." />
        ) : (
          <div className="grid gap-2">
            {list.map((e: any) => (
              <div key={e.id} className="rounded-lg border border-hairline px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">{e.title}</span>
                  <div className="flex items-center gap-2">
                    <span className="mono text-[10px] text-warmgray uppercase">{e.event_type}</span>
                    <span className="mono text-[10px] text-warmgray">{e.created_at?.slice(0, 10)}</span>
                  </div>
                </div>
                {e.decision && <p className="text-[11px] text-gold mt-0.5">→ {e.decision}</p>}
                {e.outcome && <p className="text-[11px] text-helgreen mt-0.5">✓ {e.outcome}</p>}
                {e.description && <p className="text-[11px] text-warmgray mt-0.5">{e.description}</p>}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
