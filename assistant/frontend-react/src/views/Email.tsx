import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, StatusBadge, EmptyState, Loading } from '../components';

export function Email() {
  const status = useAsync(() => helios.google.status(), []);
  const inbox = useAsync(() => helios.google.inbox(), []);
  const connected = status.data?.connected;
  const items = inbox.data?.items ?? [];

  return (
    <Page title="Email" subtitle="Gmail · summaries · task extraction"
      actions={<StatusBadge status={connected ? 'ready' : 'idle'} label={connected ? `${inbox.data?.unread ?? items.length} unread` : 'not connected'} />}>
      <Panel title="Unread" subtitle="read-only; drafting is proposed for approval" scroll className="max-h-[520px]">
        {inbox.loading ? <Loading /> : !items.length ? (
          <EmptyState message={connected ? 'Inbox zero — nothing unread.' : 'Connect Google in the desktop app to read mail.'} />
        ) : (
          <ul className="flex flex-col gap-1.5">
            {items.map((m: any, i: number) => (
              <li key={i} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-ivory truncate">{m.from || m.sender || 'Unknown'}</span>
                  <span className="mono text-[10px] text-warmgray shrink-0">{m.date || ''}</span>
                </div>
                <div className="text-[12px] text-warmgray truncate">{m.subject || '(no subject)'}</div>
                {m.snippet && <div className="text-[11px] text-warmgray/70 truncate mt-0.5">{m.snippet}</div>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </Page>
  );
}
