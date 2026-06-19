import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, AgentCard, ActivityFeed, Button, EmptyState, Loading } from '../components';

export function AgentActivity() {
  const [filter, setFilter] = useState<string | null>(null);
  const roster = useAsync(() => helios.agents.roster(), [], 10000);
  const activity = useAsync(() => helios.agents.activity(), [], 4000);

  const items = (activity.data ?? []).filter((a) => !filter || a.agent === filter);

  return (
    <Page title="Agent Activity" subtitle="live monitoring · routing · tool calls"
      actions={filter && <Button size="sm" onClick={() => setFilter(null)}>clear filter</Button>}>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-3">
        <Panel title="Team" subtitle="click to filter the feed" scroll className="max-h-[560px]">
          {roster.loading ? <Loading /> : roster.error ? <EmptyState message="Roster lives in the desktop app." /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {(roster.data ?? []).map((a) => (
                <AgentCard key={a.key} agent={a} active={filter === a.key}
                  onClick={() => setFilter((f) => (f === a.key ? null : a.key))} />
              ))}
            </div>
          )}
        </Panel>

        <Panel title={filter ? `Activity · ${filter}` : 'Live activity'} subtitle="auto-refreshing" scroll className="max-h-[560px]">
          {activity.loading && !activity.data ? <Loading /> : <ActivityFeed items={items} />}
        </Panel>
      </div>
    </Page>
  );
}
