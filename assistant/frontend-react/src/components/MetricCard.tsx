import type { ReactNode } from 'react';
import { Card } from './Card';
import { cls } from '../lib/format';

export function MetricCard({
  label, value, sub, delta, accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  delta?: { text: string; up: boolean };
  accent?: boolean;
}) {
  return (
    <Card className="p-3.5" hover>
      <div className="mono text-[10px] uppercase tracking-wider text-warmgray">{label}</div>
      <div className={cls('mt-1 text-xl font-light tabular-nums', accent ? 'text-gold' : 'text-ivory')}>{value}</div>
      <div className="mt-0.5 flex items-center gap-2">
        {sub && <span className="text-[11px] text-warmgray">{sub}</span>}
        {delta && (
          <span className={cls('mono text-[11px]', delta.up ? 'text-helgreen' : 'text-helred')}>{delta.text}</span>
        )}
      </div>
    </Card>
  );
}
