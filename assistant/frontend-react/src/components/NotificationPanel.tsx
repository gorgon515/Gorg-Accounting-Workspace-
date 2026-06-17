import { useState } from 'react';
import { getNotifications, type Notification } from '../lib/eventBus';
import { useEventBus } from '../hooks/useEventBus';
import { timeAgo } from '../lib/format';
import { EmptyState } from './Empty';

const ICON: Record<Notification['kind'], string> = {
  alert: '🔔',
  info: 'ℹ',
  agent: '◆',
  accounting: '§',
};

export function NotificationPanel() {
  const [items, setItems] = useState<Notification[]>(getNotifications());
  useEventBus('notification', () => setItems(getNotifications()));

  if (!items.length) return <EmptyState message="No notifications." />;
  return (
    <ul className="flex flex-col gap-1.5">
      {items.slice(0, 8).map((n) => (
        <li key={n.id} className="flex items-start gap-2 rounded-lg border border-hairline bg-obsidian/40 px-2.5 py-1.5">
          <span className="text-[12px] leading-5">{ICON[n.kind]}</span>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[12px] truncate">{n.title}</span>
              <span className="mono text-[10px] text-warmgray shrink-0">{timeAgo(n.ts)}</span>
            </div>
            {n.body && <p className="text-[11px] text-warmgray truncate">{n.body}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}
