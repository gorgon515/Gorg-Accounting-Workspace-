import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const MODES = ['work', 'study', 'market', 'accounting', 'personal', 'break', 'meeting', 'away'];
const MODE_ICON: Record<string, string> = {
  work: '⊛', study: '∞', market: '▤', accounting: '§',
  personal: '◉', break: '◇', meeting: '◷', away: '◌',
};
const MODE_COLOR: Record<string, string> = {
  work: 'text-helgreen', study: 'text-blue-400', market: 'text-gold',
  accounting: 'text-gold', personal: 'text-ivory', break: 'text-warmgray',
  meeting: 'text-helred', away: 'text-warmgray',
};

export function PresenceCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Presence Center." />;
  const state = useAsync(() => helios.presence.state(), [], 5000);
  const adaptive = useAsync(() => helios.presence.adaptive(), [], 5000);
  const history = useAsync(() => helios.presence.history(), [], 10000);

  const [busy, setBusy] = useState(false);
  const [focusGoal, setFocusGoal] = useState('');
  const [focusDuration, setFocusDuration] = useState('60');
  const [contextApp, setContextApp] = useState('');
  const [contextTask, setContextTask] = useState('');

  const s = state.data ?? {};
  const a = adaptive.data ?? {};
  const mode = (s as any).mode || 'unknown';
  const focus = (s as any).focus || {};
  const calendar = (s as any).calendar || {};

  async function setMode(m: string) {
    setBusy(true);
    try {
      await helios.presence.setMode({ mode: m });
      state.reload(); adaptive.reload(); history.reload();
    } finally { setBusy(false); }
  }

  async function setFocus(enabled: boolean) {
    setBusy(true);
    try {
      await helios.presence.setFocus({ enabled, duration_min: Number(focusDuration), goal: focusGoal });
      state.reload(); adaptive.reload();
    } finally { setBusy(false); }
  }

  async function updateContext() {
    await helios.presence.updateContext({ app: contextApp, task: contextTask });
    state.reload();
  }

  return (
    <Page title="Presence Center" subtitle="mode awareness · focus · context · adaptive behavior"
      actions={<Button size="sm" onClick={() => { state.reload(); adaptive.reload(); history.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Mode" value={mode.charAt(0).toUpperCase() + mode.slice(1)} accent />
          <MetricCard label="Focus Active" value={focus.enabled ? 'YES' : 'NO'} />
          <MetricCard label="Calendar" value={(calendar.status || 'free').toUpperCase()} />
          <MetricCard label="Notif. Level" value={(a.notification_level || '—').toUpperCase()} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Current Mode">
            <div className="flex flex-col gap-3">
              <div className={cls('text-4xl text-center py-2', MODE_COLOR[mode] || 'text-ivory')}>
                {MODE_ICON[mode] || '○'}
              </div>
              <div className="text-center mono text-[11px] text-warmgray uppercase tracking-wider">{mode}</div>
              <div className="grid grid-cols-4 gap-1.5">
                {MODES.map((m) => (
                  <button key={m}
                    onClick={() => setMode(m)}
                    disabled={busy}
                    className={cls('flex flex-col items-center gap-0.5 px-1 py-2 rounded border text-[11px] transition-colors',
                      mode === m ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:text-ivory hover:bg-ivory/5')}>
                    <span>{MODE_ICON[m]}</span>
                    <span className="mono text-[9px]">{m}</span>
                  </button>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="Adaptive Configuration">
            {adaptive.loading ? <Loading /> : (
              <div className="flex flex-col gap-3">
                <div className="grid gap-1.5">
                  {Object.entries(a).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-[12px]">
                      <span className="text-warmgray">{k.replace(/_/g, ' ')}</span>
                      <span className={cls('mono text-[11px]',
                        String(v) === 'high' ? 'text-helred' :
                        String(v) === 'low' ? 'text-warmgray' : 'text-gold')}>
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="border-t border-hairline pt-2">
                  <div className="mono text-[9px] text-warmgray uppercase mb-1.5">Context Update</div>
                  <div className="flex gap-1.5 mb-1.5">
                    <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      placeholder="Current app" value={contextApp}
                      onChange={(e) => setContextApp(e.target.value)} />
                    <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      placeholder="Current task" value={contextTask}
                      onChange={(e) => setContextTask(e.target.value)} />
                  </div>
                  <Button size="sm" variant="ghost" onClick={updateContext} className="w-full">Update Context</Button>
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Focus Mode">
            <div className="flex flex-col gap-3">
              <div className={cls('flex items-center justify-between px-3 py-2 rounded border',
                focus.enabled ? 'border-gold/40 bg-gold/5' : 'border-hairline')}>
                <div>
                  <div className="text-[12px]">{focus.enabled ? 'Focus Active' : 'Focus Inactive'}</div>
                  {focus.goal && <div className="text-[11px] text-warmgray">Goal: {focus.goal}</div>}
                  {focus.enabled && focus.ends_at && (
                    <div className="mono text-[10px] text-gold">
                      Ends: {new Date(focus.ends_at * 1000).toLocaleTimeString()}
                    </div>
                  )}
                </div>
                <Button size="sm" variant={focus.enabled ? 'ghost' : 'gold'}
                  onClick={() => setFocus(!focus.enabled)} disabled={busy}>
                  {focus.enabled ? 'End Focus' : 'Start Focus'}
                </Button>
              </div>
              {!focus.enabled && (
                <div className="flex flex-col gap-1.5">
                  <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                    placeholder="Focus goal (optional)" value={focusGoal}
                    onChange={(e) => setFocusGoal(e.target.value)} />
                  <div className="flex gap-1.5 items-center">
                    <input className="w-20 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      type="number" min="5" max="480" value={focusDuration}
                      onChange={(e) => setFocusDuration(e.target.value)} />
                    <span className="text-[11px] text-warmgray">minutes</span>
                  </div>
                </div>
              )}
            </div>
          </Panel>

          <Panel title="Mode History">
            {history.loading ? <Loading /> : (history.data as any[] ?? []).length === 0 ? (
              <EmptyState message="No mode history yet." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {(history.data as any[]).slice(0, 8).map((h: any, i) => (
                  <div key={i} className="flex items-center gap-2 text-[12px]">
                    <span className={cls('mono text-[10px] w-20', MODE_COLOR[h.mode] || 'text-warmgray')}>
                      {h.mode}
                    </span>
                    <span className="text-warmgray text-[10px]">
                      {new Date((h.started_at || 0) * 1000).toLocaleString()}
                    </span>
                    {h.duration_sec && (
                      <span className="mono text-[10px] text-warmgray ml-auto">
                        {Math.round(h.duration_sec / 60)}m
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </Page>
  );
}
