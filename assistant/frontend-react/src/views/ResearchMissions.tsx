import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';

const TABS = ['Missions', 'Reports', 'Teams'] as const;
type Tab = typeof TABS[number];

export function ResearchMissions() {
  const [tab, setTab] = useState<Tab>('Missions');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for Research Missions." />;
  return (
    <Page
      title="Research Missions"
      subtitle="autonomous research teams · continuous collection"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      <StatsRow />
      {tab === 'Missions' && <MissionsTab />}
      {tab === 'Reports' && <ReportsTab />}
      {tab === 'Teams' && <TeamsTab />}
    </Page>
  );
}

function StatsRow() {
  const stats = useAsync(() => helios.researchMissions.stats(), []);
  const s = stats.data ?? {};
  return (
    <div className="grid grid-cols-4 gap-3 mb-3">
      <MetricCard label="Active Missions" value={s.active_missions ?? 0} accent />
      <MetricCard label="Reports" value={s.total_reports ?? 0} />
      <MetricCard label="Teams" value={s.teams ?? 0} />
      <MetricCard label="Items Collected" value={s.total_items_collected ?? 0} />
    </div>
  );
}

function MissionsTab() {
  const teams = useAsync(() => helios.researchMissions.teams(), []);
  const missions = useAsync(() => helios.researchMissions.list(), []);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [team, setTeam] = useState('market');
  const [topics, setTopics] = useState('');
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const list: any[] = Array.isArray(missions.data) ? missions.data : [];
  const teamList: any[] = Array.isArray(teams.data) ? teams.data : [];

  async function create() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await helios.researchMissions.create({
        name, team, topics: topics.split(',').map((t) => t.trim()).filter(Boolean), schedule: 'daily',
      });
      setName(''); setTopics('');
      missions.reload();
    } finally {
      setCreating(false);
    }
  }

  async function run(id: string) {
    setRunning((r) => ({ ...r, [id]: true }));
    try { await helios.researchMissions.run(id); missions.reload(); }
    finally { setRunning((r) => ({ ...r, [id]: false })); }
  }

  return (
    <div className="grid gap-3">
      <Panel title="New Research Mission">
        <div className="grid gap-2">
          <input className="w-full bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
            placeholder="Mission name — e.g. Monitor AI companies"
            value={name} onChange={(e) => setName(e.target.value)} />
          <div className="flex gap-2">
            <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
              value={team} onChange={(e) => setTeam(e.target.value)}>
              {teamList.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-1 text-sm"
              placeholder="topics, comma-separated"
              value={topics} onChange={(e) => setTopics(e.target.value)} />
            <Button size="sm" variant="gold" onClick={create} disabled={creating || !name.trim()}>
              {creating ? 'Creating…' : 'Create'}
            </Button>
          </div>
        </div>
      </Panel>

      <Panel title="Active Missions">
        {missions.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No missions yet. Create one above to begin continuous collection." />
        ) : (
          <div className="grid gap-2">
            {list.map((m: any) => (
              <div key={m.id} className="rounded-lg border border-hairline px-3 py-2 flex items-center justify-between">
                <div className="min-w-0">
                  <span className="text-sm">{m.name}</span>
                  <p className="mono text-[10px] text-warmgray">
                    {m.team} · {m.domain} · runs {m.run_count ?? 0} · {m.schedule}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button size="sm" onClick={() => run(m.id)} disabled={running[m.id]}>
                    {running[m.id] ? 'Running…' : 'Run Now'}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => helios.researchMissions.pause(m.id).then(() => missions.reload())}>
                    Pause
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function ReportsTab() {
  const reports = useAsync(() => helios.researchMissions.reports({ limit: 20 }), []);
  const list: any[] = Array.isArray(reports.data) ? reports.data : [];
  return (
    <Panel title="Research Reports">
      {reports.loading ? <Loading /> : list.length === 0 ? (
        <EmptyState message="No reports yet. Run a mission to generate one." />
      ) : (
        <div className="grid gap-2">
          {list.map((r: any) => (
            <div key={r.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{r.title}</span>
                <span className="mono text-[10px] text-warmgray">{r.item_count ?? 0} items</span>
              </div>
              {r.summary && <p className="text-[11px] text-warmgray mt-1 line-clamp-3">{r.summary}</p>}
              <span className="mono text-[10px] text-gold">{r.team} · {String(r.created_at).slice(0, 10)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function TeamsTab() {
  const teams = useAsync(() => helios.researchMissions.teams(), []);
  const list: any[] = Array.isArray(teams.data) ? teams.data : [];
  return (
    <Panel title="Research Teams" subtitle="dedicated autonomous research units">
      {teams.loading ? <Loading /> : (
        <div className="grid gap-2">
          {list.map((t: any) => (
            <div key={t.id} className="rounded-lg border border-hairline px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">{t.name}</span>
                <span className="mono text-[10px] text-warmgray">{t.total_reports ?? 0} reports</span>
              </div>
              {t.description && <p className="text-[11px] text-warmgray mt-0.5">{t.description}</p>}
              <span className="mono text-[10px] text-gold">{(t.connectors ?? []).join(', ')}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
