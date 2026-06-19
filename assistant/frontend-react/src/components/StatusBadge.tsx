import { cls } from '../lib/format';

type Status =
  | 'online' | 'idle' | 'planned' | 'offline' | 'ready' | 'error'
  | 'ok' | 'warn' | 'degraded';

const DOT: Record<Status, string> = {
  online: 'bg-helgreen animate-pulseDot',
  ready: 'bg-helgreen',
  ok: 'bg-helgreen',
  idle: 'bg-warmgray',
  planned: 'bg-transparent border border-warmgray',
  offline: 'bg-helred',
  error: 'bg-helred',
  warn: 'bg-gold',
  degraded: 'bg-gold',
};

export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 mono text-[10px] uppercase tracking-wider text-warmgray">
      <span className={cls('w-2 h-2 rounded-full inline-block', DOT[status])} />
      {label ?? status}
    </span>
  );
}
