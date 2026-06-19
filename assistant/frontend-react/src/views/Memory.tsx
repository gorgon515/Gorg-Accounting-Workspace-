import { useMemo, useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import type { MemoryItem } from '../ipc/types';

export function Memory() {
  const [q, setQ] = useState('');
  const [cat, setCat] = useState<string | null>(null);
  const mem = useAsync(() => helios.memory.list(q || undefined), [q]);
  const items = mem.data ?? [];

  const categories = useMemo(() => {
    const c = new Map<string, number>();
    items.forEach((m) => c.set(m.category, (c.get(m.category) ?? 0) + 1));
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const shown = cat ? items.filter((m) => m.category === cat) : items;

  async function forget(m: MemoryItem) {
    try { await helios.memory.forget({ id: m.id }); mem.reload(); } catch { /* offline */ }
  }

  return (
    <Page title="Memory Center" subtitle="searchable · editable · relationship view"
      actions={
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search memories…"
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-1.5 text-[12px] outline-none focus:border-gold/40 w-56" />
      }>
      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-3">
        <Panel title="Categories" subtitle="relationship map">
          {mem.loading ? <Loading /> : !categories.length ? <EmptyState message="No memories yet." /> : (
            <div className="flex flex-col gap-1.5">
              <button onClick={() => setCat(null)}
                className={cls('flex items-center justify-between px-2 py-1.5 rounded-lg text-[12px]', !cat ? 'bg-gold/15 text-gold' : 'hover:bg-ivory/5')}>
                <span>All</span><span className="mono text-[10px]">{items.length}</span>
              </button>
              {categories.map(([c, n]) => (
                <button key={c} onClick={() => setCat(c)}
                  className={cls('flex items-center justify-between px-2 py-1.5 rounded-lg text-[12px]', cat === c ? 'bg-gold/15 text-gold' : 'hover:bg-ivory/5')}>
                  <span className="capitalize truncate">{c}</span><span className="mono text-[10px] text-warmgray">{n}</span>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title={cat ? `Memories · ${cat}` : 'All memories'} scroll className="max-h-[520px]">
          {mem.loading ? <Loading /> : mem.error ? <EmptyState message="Memory lives in the desktop app." />
            : !shown.length ? <EmptyState message="No memories match." />
            : (
              <ul className="flex flex-col gap-1.5">
                {shown.map((m) => (
                  <li key={m.id} className="group flex items-start gap-2 rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
                    <span className="mono text-[9px] uppercase text-gold shrink-0 mt-0.5 w-16 truncate">{m.category}</span>
                    <span className="text-[12px] flex-1">{m.fact}</span>
                    <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100" onClick={() => forget(m)}>forget</Button>
                  </li>
                ))}
              </ul>
            )}
        </Panel>
      </div>
    </Page>
  );
}
