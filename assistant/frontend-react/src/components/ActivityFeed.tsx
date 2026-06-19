import { AnimatePresence, motion } from 'framer-motion';
import type { AgentActivity } from '../ipc/types';
import { timeAgo, cls } from '../lib/format';
import { EmptyState } from './Empty';

export function ActivityFeed({ items, empty = 'No agent activity yet.' }: { items: AgentActivity[]; empty?: string }) {
  if (!items.length) return <EmptyState message={empty} />;
  return (
    <ul className="flex flex-col gap-1.5">
      <AnimatePresence initial={false}>
        {items.map((a, i) => (
          <motion.li
            key={`${a.ts}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2.5 rounded-lg border border-hairline bg-obsidian/40 px-2.5 py-1.5"
          >
            <span className={cls('w-1.5 h-1.5 rounded-full shrink-0', a.ok ? 'bg-helgreen' : 'bg-helred')} />
            <span className="text-[12px] truncate flex-1">
              <span className="text-ivory">{a.name}</span>
              {a.tool && <span className="text-warmgray"> · {a.tool}</span>}
            </span>
            <span className="mono text-[10px] text-warmgray shrink-0">{timeAgo(a.ts)}</span>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}
