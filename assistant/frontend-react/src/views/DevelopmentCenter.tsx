import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const RUNTIME_MODES = ['production', 'sandbox', 'development', 'daily_driver'];
const CHANNELS = ['stable', 'beta', 'experimental', 'development'];

function channelColor(c: string): string {
  return c === 'stable' ? 'text-helgreen'
    : c === 'beta' ? 'text-gold'
    : c === 'experimental' ? 'text-helred'
    : 'text-blue-400';
}

export function DevelopmentCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Development Center." />;
  const mode = useAsync(() => helios.runtime.mode(), [], 6000);
  const diag = useAsync(() => helios.runtime.diagnostics(), []);
  const flags = useAsync(() => helios.featureFlags.list(), []);
  const channels = useAsync(() => helios.releaseChannels.channels(), []);
  const migs = useAsync(() => helios.migrations.list(), []);
  const plugins = useAsync(() => helios.pluginUpgrades.versions(), []);

  const [busy, setBusy] = useState(false);
  const [newFlag, setNewFlag] = useState('');

  const m = mode.data ?? ({} as any);
  const d = diag.data ?? ({} as any);
  const checks = d.checks ?? {};

  async function setMode(mm: string) {
    setBusy(true);
    try { await helios.runtime.setMode({ mode: mm }); mode.reload(); }
    finally { setBusy(false); }
  }

  async function toggleFlag(f: any) {
    setBusy(true);
    try {
      if (f.enabled) await helios.featureFlags.disable(f.key);
      else await helios.featureFlags.enable(f.key);
      flags.reload();
    } finally { setBusy(false); }
  }

  async function killFlag(f: any) {
    setBusy(true);
    try { await helios.featureFlags.kill(f.key); flags.reload(); }
    finally { setBusy(false); }
  }

  async function createFlag() {
    if (!newFlag.trim()) return;
    setBusy(true);
    try {
      const key = newFlag.trim().toLowerCase().replace(/\s+/g, '_');
      await helios.featureFlags.create({ key, name: newFlag.trim(), enabled: false, rollout: 'experimental' });
      setNewFlag(''); flags.reload();
    } finally { setBusy(false); }
  }

  async function setFlagRollout(f: any, channel: string) {
    setBusy(true);
    try { await helios.featureFlags.setRollout(f.key, { channel }); flags.reload(); }
    finally { setBusy(false); }
  }

  return (
    <Page title="Development Center" subtitle="runtime modes · feature flags · release channels · migrations · plugin upgrades"
      actions={<Button size="sm" onClick={() => { mode.reload(); diag.reload(); flags.reload(); migs.reload(); plugins.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        {/* Runtime mode */}
        <Panel title="Runtime Mode">
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-3">
              <MetricCard label="Current Mode" value={String(m.mode || '—').toUpperCase()} accent />
              <MetricCard label="Production" value={m.is_production ? 'YES' : 'NO'} />
              <MetricCard label="Experimental" value={m.experimental_enabled ? 'ENABLED' : 'DISABLED'} />
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {RUNTIME_MODES.map((mm) => (
                <button key={mm} onClick={() => setMode(mm)} disabled={busy}
                  className={cls('px-2 py-2 rounded border text-[11px] mono transition-colors',
                    m.mode === mm ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:text-ivory hover:bg-ivory/5')}>
                  {mm}
                </button>
              ))}
            </div>
          </div>
        </Panel>

        {/* Startup diagnostics */}
        <div className="grid grid-cols-2 gap-3">
          <Panel title="Startup Diagnostics">
            {diag.loading ? <Loading /> : (
              <div className="flex flex-col gap-2">
                <div className={cls('mono text-[12px] uppercase', d.ok ? 'text-helgreen' : 'text-helred')}>
                  {d.ok ? '✓ All checks passed' : '✗ Issues detected'}
                </div>
                {Object.entries(checks).map(([name, c]: any) => (
                  <div key={name} className="flex items-center justify-between text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className="text-warmgray">{name.replace(/_/g, ' ')}</span>
                    <span className={cls('mono text-[10px]', c?.ok ? 'text-helgreen' : 'text-helred')}>
                      {c?.ok ? 'OK' : 'FAIL'}
                    </span>
                  </div>
                ))}
                <Button size="sm" variant="ghost" onClick={() => diag.reload()} className="w-full mt-1">Re-run Diagnostics</Button>
              </div>
            )}
          </Panel>

          <Panel title="Release Channels">
            {channels.loading ? <Loading /> : (
              <div className="flex flex-col gap-1.5">
                {(channels.data as any[] ?? []).map((c: any) => (
                  <div key={c.name} className="flex items-center justify-between text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className={cls('mono text-[11px] uppercase', channelColor(c.name))}>{c.name}</span>
                    <span className="text-warmgray text-[10px]">{c.description}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        {/* Feature flags */}
        <Panel title="Feature Flags">
          <div className="flex gap-1.5 mb-3">
            <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
              placeholder="New feature flag name" value={newFlag}
              onChange={(e) => setNewFlag(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && createFlag()} />
            <Button size="sm" variant="gold" onClick={createFlag} disabled={busy}>Add Flag</Button>
          </div>
          {flags.loading ? <Loading /> : (flags.data as any[] ?? []).length === 0 ? (
            <EmptyState message="No feature flags yet." />
          ) : (
            <div className="flex flex-col gap-1.5">
              {(flags.data as any[]).map((f: any) => (
                <div key={f.key} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                  <span className={cls('w-2 h-2 rounded-full', f.kill_switch ? 'bg-helred' : f.enabled ? 'bg-helgreen' : 'bg-warmgray')} />
                  <span className="flex-1">{f.name}</span>
                  <select value={f.rollout} onChange={(e) => setFlagRollout(f, e.target.value)}
                    className="bg-obsidian border border-hairline rounded px-1.5 py-0.5 text-[10px] mono">
                    {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <Button size="sm" variant="ghost" onClick={() => toggleFlag(f)} disabled={busy}>
                    {f.enabled ? 'Disable' : 'Enable'}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => killFlag(f)} disabled={busy}>Kill</Button>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Migrations + Plugin upgrades */}
        <div className="grid grid-cols-2 gap-3">
          <Panel title="Data Migrations">
            {migs.loading ? <Loading /> : (migs.data as any[] ?? []).length === 0 ? (
              <EmptyState message="No migrations registered." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {(migs.data as any[]).slice(0, 10).map((mg: any) => (
                  <div key={mg.id} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className="mono text-[10px] text-warmgray">v{mg.version}</span>
                    <span className="flex-1">{mg.name}</span>
                    <span className={cls('mono text-[10px] uppercase',
                      mg.status === 'applied' ? 'text-helgreen' :
                      mg.status === 'failed' ? 'text-helred' :
                      mg.status === 'rolled_back' ? 'text-gold' : 'text-warmgray')}>
                      {mg.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Plugin Versions">
            {plugins.loading ? <Loading /> : (plugins.data as any[] ?? []).length === 0 ? (
              <EmptyState message="No plugin versions registered." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {(plugins.data as any[]).slice(0, 10).map((p: any) => (
                  <div key={p.id} className="flex items-center gap-2 text-[12px] px-2 py-1.5 rounded border border-hairline">
                    <span className="flex-1">{p.plugin_id}</span>
                    <span className="mono text-[10px] text-warmgray">{p.version}</span>
                    {p.sandbox_verified ? <span className="mono text-[9px] text-helgreen">SANDBOX ✓</span> : null}
                    <span className={cls('mono text-[10px] uppercase',
                      p.status === 'active' ? 'text-helgreen' : 'text-warmgray')}>{p.status}</span>
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
