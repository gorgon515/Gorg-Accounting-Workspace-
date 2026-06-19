import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Events', 'Deadlines', 'Rules'] as const;
type Tab = typeof TABS[number];

export function EventMonitor() {
  const [tab, setTab] = useState<Tab>('Events');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Event Monitor." />;
  return (
    <Page
      title="Event Monitor"
      subtitle="event monitoring engine · deadlines · system health"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      <StatsRow />
      {tab === 'Events' && <EventsTab />}
      {tab === 'Deadlines' && <DeadlinesTab />}
      {tab === 'Rules' && <RulesTab />}
    </Page>
  );
}

function StatsRow() {
  const stats = useAsync(() => helios.eventMonitor.stats(), [], 30000);
  const s = stats.data ?? {};
  return (
    <div className="grid grid-cols-4 gap-3 mb-3">
      <MetricCard label="Active Events" value={s.active_events ?? 0} accent />
      <MetricCard label="Critical" value={s.critical_events ?? 0} />
      <MetricCard label="Pending Deadlines" value={s.pending_deadlines ?? 0} />
      <MetricCard label="Active Rules" value={s.active_rules ?? 0} />
    </div>
  );
}

function EventsTab() {
  const events = useAsync(() => helios.eventMonitor.events({ status: 'active' }), []);
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(events.data) ? events.data : [];

  async function scan() {
    setBusy(true);
    try {
      await helios.eventMonitor.scan();
      await helios.eventMonitor.checkDeadlines();
      events.reload();
    } finally { setBusy(false); }
  }

  return (
    <Panel title="Monitored Events"
      actions={<Button size="sm" variant="gold" onClick={scan} disabled={busy}>{busy ? 'Scanning…' : 'Scan Now'}</Button>}
    >
      {events.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No active events. Scan to detect events across intelligence streams." />
      ) : (
        <div className="grid gap-2">
          {list.map((e: any) => (
            <div key={e.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <SeverityTag severity={e.severity} />
                  <span className="text-sm truncate">{e.title}</span>
                </div>
                <p className="mono text-[10px] text-warmgray mt-0.5">{e.category} · {e.event_type}</p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <Button size="sm" onClick={() => helios.eventMonitor.acknowledgeEvent(e.id).then(() => events.reload())}>Ack</Button>
                <Button size="sm" variant="ghost" onClick={() => helios.eventMonitor.resolveEvent(e.id).then(() => events.reload())}>Resolve</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function DeadlinesTab() {
  const deadlines = useAsync(() => helios.eventMonitor.deadlines({ status: 'pending' }), []);
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const list: any[] = Array.isArray(deadlines.data) ? deadlines.data : [];

  async function add() {
    if (!title.trim() || !date) return;
    await helios.eventMonitor.addDeadline({ title, deadline_date: date, category: 'tax' });
    setTitle(''); setDate('');
    deadlines.reload();
  }

  return (
    <Panel title="Deadlines"
      actions={
        <div className="flex gap-1">
          <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
            placeholder="deadline" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs w-32"
            type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <Button size="sm" onClick={add}>Add</Button>
        </div>
      }
    >
      {deadlines.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No pending deadlines." />
      ) : (
        <div className="grid gap-2">
          {list.map((d: any) => (
            <div key={d.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
              <div>
                <span className="text-sm">{d.title}</span>
                {d.description && <p className="text-[11px] text-warmgray">{d.description}</p>}
              </div>
              <div className="flex items-center gap-3 mono text-[10px]">
                <span className="text-warmgray">{d.category}</span>
                <span className="text-gold">{d.deadline_date}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function RulesTab() {
  const rules = useAsync(() => helios.eventMonitor.rules(), []);
  const list: any[] = Array.isArray(rules.data) ? rules.data : [];
  return (
    <Panel title="Event Rules" subtitle="continuous monitoring rules">
      {rules.loading ? <Loading /> : (
        <div className="grid gap-2">
          {list.map((r: any) => (
            <div key={r.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{r.name}</span>
                <div className="flex items-center gap-2">
                  <SeverityTag severity={r.severity} />
                  <span className="mono text-[10px] text-warmgray">×{r.trigger_count ?? 0}</span>
                </div>
              </div>
              {r.description && <p className="text-[11px] text-warmgray mt-0.5">{r.description}</p>}
              <span className="mono text-[10px] text-gold">{r.category} · every {r.check_interval_hours}h</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function SeverityTag({ severity }: { severity: string }) {
  const color = severity === 'critical' ? 'text-helred' : severity === 'high' ? 'text-helred'
    : severity === 'medium' ? 'text-gold' : 'text-warmgray';
  return <span className={cls('mono text-[9px] uppercase', color)}>{severity}</span>;
}
