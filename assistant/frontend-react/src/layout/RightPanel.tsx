import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, ActivityFeed, NotificationPanel, StatusBadge } from '../components';

// Live intelligence rail: agent activity, notifications, and system status.
export function RightPanel() {
  const activity = useAsync(() => helios.agents.activity(), [], 4000);
  const roster = useAsync(() => helios.agents.roster(), [], 15000);
  const cfg = useAsync(() => helios.config(), []);
  const side = useAsync(() => helios.sidecar.status(), [], 15000);

  const online = roster.data?.filter((a) => a.status === 'online').length ?? 0;

  return (
    <aside className="w-[320px] shrink-0 h-full flex-col gap-3 p-3 hidden xl:flex overflow-y-auto scroll-thin">
      <Panel title="Agent activity" subtitle="live" className="min-h-[180px]" bodyClass="max-h-[240px] overflow-y-auto scroll-thin">
        <ActivityFeed items={(activity.data ?? []).slice(0, 12)} />
      </Panel>

      <Panel title="Notifications">
        <NotificationPanel />
      </Panel>

      <Panel title="System status">
        <div className="flex flex-col gap-2">
          <Row label="Brain" badge={<StatusBadge status={cfg.data?.brain?.ready ? 'online' : 'offline'} label={cfg.data?.brain?.model || '—'} />} />
          <Row label="Sidecar" badge={<StatusBadge status={side.data?.ready ? 'online' : 'idle'} label={side.data?.ready ? 'ready' : 'idle'} />} />
          <Row label="Voice" badge={<StatusBadge status={cfg.data?.stt?.ready ? 'ready' : 'idle'} label={cfg.data?.stt?.engine || 'local'} />} />
          <Row label="Agents" badge={<StatusBadge status="online" label={`${online}/${roster.data?.length ?? 0}`} />} />
        </div>
      </Panel>
    </aside>
  );
}

function Row({ label, badge }: { label: string; badge: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[12px] text-warmgray">{label}</span>
      {badge}
    </div>
  );
}
