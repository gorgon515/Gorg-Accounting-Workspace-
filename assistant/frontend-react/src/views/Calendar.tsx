import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Timeline, StatusBadge, EmptyState, Loading } from '../components';

export function Calendar() {
  const status = useAsync(() => helios.google.status(), []);
  const agenda = useAsync(() => helios.google.agenda(), []);
  const connected = status.data?.connected;

  return (
    <Page title="Calendar" subtitle="Google Calendar · daily agenda"
      actions={<StatusBadge status={connected ? 'ready' : 'idle'} label={connected ? 'connected' : 'not connected'} />}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Today" subtitle="agenda">
          {agenda.loading ? <Loading /> : (
            <Timeline
              empty={connected ? 'No events today.' : 'Connect Google in the desktop app (Connections).'}
              items={(agenda.data?.events ?? []).map((e: any) => ({
                title: e.summary || e.title || 'Event',
                time: e.time || e.start || '',
                desc: e.location,
                accent: true,
              }))}
            />
          )}
        </Panel>
        <Panel title="Planning" subtitle="time-blocking · conflict detection">
          <p className="text-[12px] text-warmgray leading-relaxed">
            The Calendar Agent surfaces your day, detects conflicts, protects focus time, and prepares
            you for meetings. Scheduling and time-blocking write-actions are proposed for your approval.
            {!connected && ' Connect Google to populate your agenda.'}
          </p>
        </Panel>
      </div>
    </Page>
  );
}
