import type { ReactNode } from 'react';
import { EmptyState } from './Empty';

export interface TimelineItem {
  title: ReactNode;
  time?: string;
  desc?: ReactNode;
  accent?: boolean;
}

export function Timeline({ items, empty = 'Nothing scheduled.' }: { items: TimelineItem[]; empty?: string }) {
  if (!items.length) return <EmptyState message={empty} />;
  return (
    <ul className="relative pl-4">
      <span className="absolute left-1 top-1 bottom-1 w-px bg-hairline" />
      {items.map((it, i) => (
        <li key={i} className="relative pb-3 last:pb-0">
          <span
            className={`absolute -left-3 top-1 w-2 h-2 rounded-full ${it.accent ? 'bg-gold' : 'bg-warmgray'}`}
          />
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[12px] text-ivory">{it.title}</span>
            {it.time && <span className="mono text-[10px] text-gold shrink-0">{it.time}</span>}
          </div>
          {it.desc && <p className="text-[11px] text-warmgray mt-0.5">{it.desc}</p>}
        </li>
      ))}
    </ul>
  );
}
