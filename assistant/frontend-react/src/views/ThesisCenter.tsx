import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function ThesisCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Thesis Center." />;
  const stats = useAsync(() => helios.thesis.stats(), []);
  const theses = useAsync(() => helios.thesis.list({ status: 'active' }), []);
  const [form, setForm] = useState({ title: '', symbol: '', direction: 'long', summary: '', expected_return: '', confidence: '0.6' });
  const [busy, setBusy] = useState(false);
  const list: any[] = Array.isArray(theses.data) ? theses.data : [];
  const s = stats.data ?? {};

  async function create() {
    if (!form.title.trim()) return;
    setBusy(true);
    try {
      await helios.thesis.create({
        title: form.title, symbol: form.symbol.toUpperCase(), direction: form.direction,
        summary: form.summary, expected_return: form.expected_return ? Number(form.expected_return) : undefined,
        confidence: Number(form.confidence),
      });
      setForm({ title: '', symbol: '', direction: 'long', summary: '', expected_return: '', confidence: '0.6' });
      theses.reload(); stats.reload();
    } finally { setBusy(false); }
  }

  async function close(t: any) {
    const realized = prompt(`Realized return for "${t.title}" (e.g. 0.15)?`);
    const outcome = realized != null && Number(realized) >= 0 ? 'correct' : 'incorrect';
    await helios.thesis.close(t.id, { outcome, realized_return: realized != null ? Number(realized) : undefined });
    theses.reload(); stats.reload();
  }

  return (
    <Page title="Thesis Center" subtitle="investment theses · evidence · catalysts · outcome tracking">
      <div className="grid grid-cols-4 gap-3 mb-3">
        <MetricCard label="Active Theses" value={s.active_theses ?? 0} accent />
        <MetricCard label="Closed" value={s.closed_theses ?? 0} />
        <MetricCard label="Avg Confidence" value={s.avg_confidence != null ? `${Math.round(s.avg_confidence * 100)}%` : '—'} />
        <MetricCard label="Tracking" value={(s.active_theses ?? 0) + (s.closed_theses ?? 0)} />
      </div>

      <div className="grid gap-3">
        <Panel title="New Thesis">
          <div className="grid gap-2">
            <div className="flex gap-2">
              <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
                placeholder="Thesis title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              <input className="w-24 bg-obsidian border border-hairline rounded px-2 py-2 text-sm"
                placeholder="SYMBOL" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} />
              <select className="border border-hairline bg-obsidian rounded px-2 text-xs"
                value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                <option value="long">long</option>
                <option value="short">short</option>
              </select>
            </div>
            <textarea className="bg-obsidian border border-hairline rounded px-3 py-2 text-sm" rows={2}
              placeholder="Summary of the investment case" value={form.summary}
              onChange={(e) => setForm({ ...form, summary: e.target.value })} />
            <div className="flex gap-2 items-center">
              <input className="w-36 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                placeholder="exp. return e.g. 0.2" value={form.expected_return}
                onChange={(e) => setForm({ ...form, expected_return: e.target.value })} />
              <input className="w-32 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                placeholder="confidence 0-1" value={form.confidence}
                onChange={(e) => setForm({ ...form, confidence: e.target.value })} />
              <Button size="sm" variant="gold" onClick={create} disabled={busy || !form.title.trim()}>Create</Button>
            </div>
          </div>
        </Panel>

        <Panel title="Active Theses">
          {theses.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No active theses. Document your first investment case above." />
          ) : (
            <div className="grid gap-2">
              {list.map((t: any) => (
                <div key={t.id} className="rounded-lg border border-hairline px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={cls('mono text-[9px] uppercase px-1.5 py-0.5 rounded',
                        t.direction === 'long' ? 'bg-helgreen/15 text-helgreen' : 'bg-helred/15 text-helred')}>
                        {t.direction}
                      </span>
                      <span className="text-sm truncate">{t.title}</span>
                      {t.symbol && <span className="mono text-[10px] text-warmgray">{t.symbol}</span>}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="mono text-[10px] text-gold">{Math.round((t.confidence ?? 0) * 100)}%</span>
                      <Button size="sm" variant="ghost" onClick={() => close(t)}>Close</Button>
                    </div>
                  </div>
                  {t.summary && <p className="text-[11px] text-warmgray mt-1">{t.summary}</p>}
                  <div className="mono text-[10px] text-warmgray mt-1 flex gap-3">
                    {t.expected_return != null && <span>target {(t.expected_return * 100).toFixed(0)}%</span>}
                    <span>{t.time_horizon}</span>
                    {(t.catalysts ?? []).length > 0 && <span>{t.catalysts.length} catalyst(s)</span>}
                    {(t.risks ?? []).length > 0 && <span>{t.risks.length} risk(s)</span>}
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
