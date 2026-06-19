import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const PRIORITIES = ['', 'critical', 'urgent', 'high', 'medium', 'low'];
const PRIORITY_COLOR: Record<string, string> = {
  critical: 'text-helred', urgent: 'text-helred', high: 'text-gold',
  medium: 'text-ivory', low: 'text-warmgray',
};

export function NotificationCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Notification Center." />;
  const stats = useAsync(() => helios.notifications.stats(), [], 5000);
  const notifications = useAsync(() => helios.notifications.list({ status: 'unread' }), [], 10000);
  const quietHours = useAsync(() => helios.notifications.quietHours(), []);
  const focusMode = useAsync(() => helios.notifications.focusMode(), []);
  const channels = useAsync(() => helios.notifications.channels(), []);

  const [filter, setFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [compose, setCompose] = useState({ title: '', body: '', priority: 'medium', category: 'general' });

  const s = stats.data ?? {};
  const items: any[] = Array.isArray(notifications.data) ? notifications.data : [];

  async function send() {
    if (!compose.title.trim()) return;
    setBusy(true);
    try {
      await helios.notifications.send(compose);
      setCompose({ title: '', body: '', priority: 'medium', category: 'general' });
      notifications.reload(); stats.reload();
    } finally { setBusy(false); }
  }

  async function markRead(id: string) {
    await helios.notifications.markRead(id);
    notifications.reload(); stats.reload();
  }

  async function markAllRead() {
    await helios.notifications.markAllRead();
    notifications.reload(); stats.reload();
  }

  async function toggleFocus() {
    const fm = focusMode.data ?? {};
    await helios.notifications.setFocusMode({ enabled: !fm.enabled, duration_minutes: 60 });
    focusMode.reload();
  }

  const filtered = filter ? items.filter((n) => n.priority === filter) : items;

  return (
    <Page title="Notification Center" subtitle="priority scoring · quiet hours · focus mode · channels"
      actions={
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={markAllRead}>Mark All Read</Button>
          <Button size="sm" onClick={() => { notifications.reload(); stats.reload(); }}>Refresh</Button>
        </div>
      }
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Unread" value={s.unread ?? 0} accent />
          <MetricCard label="Total" value={s.total ?? 0} />
          <MetricCard label="Focus Mode" value={(focusMode.data as any)?.enabled ? 'ON' : 'OFF'} />
          <MetricCard label="Quiet Hours" value={(quietHours.data as any)?.enabled ? 'ON' : 'OFF'} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <Panel title="Controls">
            <div className="flex flex-col gap-3">
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-2">Focus Mode</div>
                <div className="flex items-center justify-between">
                  <div className="text-[12px]">
                    {(focusMode.data as any)?.enabled
                      ? `Active · ends ${new Date(((focusMode.data as any)?.ends_at || 0) * 1000).toLocaleTimeString()}`
                      : 'Inactive'}
                  </div>
                  <Button size="sm" variant={(focusMode.data as any)?.enabled ? 'gold' : 'ghost'}
                    onClick={toggleFocus}>
                    {(focusMode.data as any)?.enabled ? 'Disable' : 'Enable'}
                  </Button>
                </div>
              </div>
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-2">Quiet Hours</div>
                {quietHours.loading ? <Loading /> : (
                  <div className="text-[12px] text-ivory/70">
                    {(quietHours.data as any)?.enabled
                      ? `${(quietHours.data as any)?.start_hour}:00 – ${(quietHours.data as any)?.end_hour}:00`
                      : 'Disabled'}
                  </div>
                )}
              </div>
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-2">Channels</div>
                {channels.loading ? <Loading /> : (
                  <div className="flex flex-wrap gap-1.5">
                    {(channels.data as any[] ?? []).map((ch: any) => (
                      <span key={ch.id || ch} className="mono text-[10px] px-2 py-0.5 rounded bg-ivory/5 text-warmgray">
                        {ch.name || ch}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Panel>

          <Panel title="Send Notification">
            <div className="flex flex-col gap-2">
              <input className="bg-obsidian border border-hairline rounded px-2 py-1.5 text-xs"
                placeholder="Title" value={compose.title}
                onChange={(e) => setCompose({ ...compose, title: e.target.value })} />
              <textarea className="bg-obsidian border border-hairline rounded px-2 py-1.5 text-xs resize-none"
                rows={2} placeholder="Body (optional)" value={compose.body}
                onChange={(e) => setCompose({ ...compose, body: e.target.value })} />
              <div className="flex gap-1.5">
                <select className="flex-1 border border-hairline bg-obsidian rounded px-2 text-[11px]"
                  value={compose.priority}
                  onChange={(e) => setCompose({ ...compose, priority: e.target.value })}>
                  {['low','medium','high','urgent','critical'].map((p) => <option key={p}>{p}</option>)}
                </select>
                <select className="flex-1 border border-hairline bg-obsidian rounded px-2 text-[11px]"
                  value={compose.category}
                  onChange={(e) => setCompose({ ...compose, category: e.target.value })}>
                  {['general','market','portfolio','accounting','tax','research','system','approval','calendar','voice'].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <Button size="sm" variant="gold" onClick={send} disabled={busy || !compose.title.trim()}>
                {busy ? 'Sending…' : 'Send'}
              </Button>
            </div>
          </Panel>

          <Panel title="Priority Filter">
            <div className="flex flex-col gap-1.5">
              {PRIORITIES.map((p) => (
                <button key={p}
                  onClick={() => setFilter(p)}
                  className={cls('text-left px-2.5 py-1.5 rounded text-[12px] transition-colors',
                    filter === p ? 'bg-gold/10 text-gold' : 'text-ivory/70 hover:text-ivory hover:bg-ivory/5')}>
                  {p || 'All'} {p && `(${items.filter((n) => n.priority === p).length})`}
                </button>
              ))}
            </div>
          </Panel>
        </div>

        <Panel title="Notifications" subtitle={`${filtered.length} shown`}>
          {notifications.loading ? <Loading /> : filtered.length === 0 ? (
            <EmptyState message="No notifications." />
          ) : (
            <div className="flex flex-col gap-1.5">
              {filtered.map((n: any) => (
                <div key={n.id}
                  className={cls('flex items-start gap-3 px-3 py-2 rounded border transition-colors',
                    n.status === 'unread' ? 'border-gold/20 bg-gold/5' : 'border-hairline')}>
                  <span className={cls('mono text-[10px] uppercase mt-0.5 shrink-0 w-14',
                    PRIORITY_COLOR[n.priority] || 'text-warmgray')}>
                    {n.priority}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-medium">{n.title}</div>
                    {n.body && <div className="text-[11px] text-warmgray">{n.body}</div>}
                    <div className="mono text-[10px] text-warmgray mt-0.5">
                      {n.category} · {new Date((n.created_at || 0) * 1000).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    {n.status === 'unread' && (
                      <Button size="sm" variant="ghost" onClick={() => markRead(n.id)}>✓</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}
