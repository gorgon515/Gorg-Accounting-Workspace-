import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Updates', 'Advisories', 'Compliance'] as const;
type Tab = typeof TABS[number];

export function CPAOperations() {
  const [tab, setTab] = useState<Tab>('Updates');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for CPA Operations." />;
  return (
    <Page
      title="CPA Operations"
      subtitle="tax law · accounting standards · regulatory monitor"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      <StatsRow />
      {tab === 'Updates' && <UpdatesTab />}
      {tab === 'Advisories' && <AdvisoriesTab />}
      {tab === 'Compliance' && <ComplianceTab />}
    </Page>
  );
}

function StatsRow() {
  const stats = useAsync(() => helios.cpaOps.stats(), []);
  const s = stats.data ?? {};
  return (
    <div className="grid grid-cols-4 gap-3 mb-3">
      <MetricCard label="Reg. Updates" value={s.total_updates ?? 0} accent />
      <MetricCard label="High Priority" value={s.high_priority_updates ?? 0} />
      <MetricCard label="Draft Advisories" value={s.draft_advisories ?? 0} />
      <MetricCard label="Open Compliance" value={s.open_compliance_items ?? 0} />
    </div>
  );
}

function UpdatesTab() {
  const updates = useAsync(() => helios.cpaOps.updates({ limit: 40 }), []);
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(updates.data) ? updates.data : [];

  async function runDigest() {
    setBusy(true);
    try { await helios.cpaOps.digest(); updates.reload(); }
    finally { setBusy(false); }
  }

  return (
    <Panel title="Regulatory Updates"
      subtitle="tax & accounting changes from live intelligence"
      actions={<Button size="sm" variant="gold" onClick={runDigest} disabled={busy}>{busy ? 'Running…' : 'Run Digest'}</Button>}
    >
      {updates.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No regulatory updates yet. Run the digest to ingest from live intelligence." />
      ) : (
        <div className="grid gap-2">
          {list.map((u: any) => (
            <div key={u.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm truncate">{u.title}</span>
                <PriorityTag priority={u.priority} />
              </div>
              {u.summary && <p className="text-[11px] text-warmgray line-clamp-2 mt-0.5">{u.summary}</p>}
              <div className="mono text-[10px] text-warmgray mt-1 flex gap-3">
                <span>{u.category}</span>
                <span>{u.source}</span>
                {u.action_required ? <span className="text-gold">action required</span> : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function AdvisoriesTab() {
  const advisories = useAsync(() => helios.cpaOps.advisories({}), []);
  const list: any[] = Array.isArray(advisories.data) ? advisories.data : [];
  return (
    <Panel title="Client Advisories" subtitle="drafts require human review before sending">
      {advisories.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No advisories yet. High-priority updates auto-generate draft advisories." />
      ) : (
        <div className="grid gap-2">
          {list.map((a: any) => (
            <div key={a.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{a.title}</span>
                <span className={cls('mono text-[9px] uppercase',
                  a.status === 'draft' ? 'text-gold' : 'text-helgreen')}>{a.status}</span>
              </div>
              <p className="text-[11px] text-warmgray mt-1 whitespace-pre-wrap line-clamp-4">{a.body}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function ComplianceTab() {
  const items = useAsync(() => helios.cpaOps.compliance({ status: 'open' }), []);
  const [title, setTitle] = useState('');
  const [due, setDue] = useState('');
  const list: any[] = Array.isArray(items.data) ? items.data : [];

  async function add() {
    if (!title.trim()) return;
    await helios.cpaOps.addCompliance({ title, due_date: due, category: 'tax' });
    setTitle(''); setDue('');
    items.reload();
  }

  return (
    <Panel title="Compliance Items"
      actions={
        <div className="flex gap-1">
          <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
            placeholder="title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs w-32"
            type="date" value={due} onChange={(e) => setDue(e.target.value)} />
          <Button size="sm" onClick={add}>Add</Button>
        </div>
      }
    >
      {items.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No open compliance items." />
      ) : (
        <div className="grid gap-2">
          {list.map((c: any) => (
            <div key={c.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div>
                <span className="text-sm">{c.title}</span>
                {c.description && <p className="text-[11px] text-warmgray">{c.description}</p>}
              </div>
              <div className="flex items-center gap-3 mono text-[10px]">
                <span className="text-warmgray">{c.category}</span>
                {c.due_date && <span className="text-gold">{c.due_date}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function PriorityTag({ priority }: { priority: string }) {
  const color = priority === 'high' ? 'text-helred' : priority === 'normal' ? 'text-warmgray' : 'text-gold';
  return <span className={cls('mono text-[9px] uppercase shrink-0', color)}>{priority}</span>;
}
