import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';

const TABS = ['Devices', 'Sync Status', 'Conflicts', 'Audit'] as const;
type Tab = typeof TABS[number];

const COMPONENTS = ['accounting', 'vault', 'documents', 'memory'] as const;
type Component = typeof COMPONENTS[number];

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function truncate(s: string, n = 16): string {
  if (!s) return '—';
  return s.length > n ? s.slice(0, n) + '…' : s;
}

export function SyncView() {
  const [tab, setTab] = useState<Tab>('Devices');

  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to use Sync." />;

  return (
    <Page
      title="Sync"
      subtitle="devices · sync status · conflicts"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>
              {t}
            </Button>
          ))}
        </div>
      }
    >
      {tab === 'Devices' && <DevicesTab />}
      {tab === 'Sync Status' && <SyncStatusTab />}
      {tab === 'Conflicts' && <ConflictsTab />}
      {tab === 'Audit' && <AuditTab />}
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Devices tab
// ---------------------------------------------------------------------------

function DevicesTab() {
  const status = useAsync(() => helios.sync.status(), []);
  const devices = useAsync(() => helios.sync.listDevices(), []);

  const [name, setName] = useState('');
  const [type, setType] = useState<'desktop' | 'mobile' | 'tablet' | 'server'>('desktop');
  const [platform, setPlatform] = useState('');
  const [busy, setBusy] = useState(false);
  const [regErr, setRegErr] = useState<string | null>(null);
  const [deregBusy, setDeregBusy] = useState<string | null>(null);

  const s = status.data as any;
  const devList: any[] = devices.data ?? [];

  // derive last sync from status or most recent device last_seen
  const lastSync: string | null =
    s?.last_sync ??
    devList.reduce<string | null>((best, d: any) => {
      if (!d.last_seen) return best;
      if (!best) return d.last_seen;
      return d.last_seen > best ? d.last_seen : best;
    }, null);

  const activeSessions: number = s?.sessions?.length ?? 0;

  async function registerDevice() {
    if (!name.trim() || !platform.trim()) return;
    setBusy(true);
    setRegErr(null);
    try {
      await helios.sync.registerDevice({ name: name.trim(), type, platform: platform.trim() });
      setName('');
      setPlatform('');
      devices.reload();
    } catch (e: any) {
      setRegErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function deregisterDevice(id: string) {
    setDeregBusy(id);
    try {
      await helios.sync.deregisterDevice(id);
      devices.reload();
    } finally {
      setDeregBusy(null);
    }
  }

  function deviceStatus(d: any): 'ok' | 'idle' {
    const st = (d.status ?? '').toLowerCase();
    return st === 'active' || st === 'online' ? 'ok' : 'idle';
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Registered Devices" accent value={devList.length} />
        <MetricCard label="Active Sessions" value={activeSessions} />
        <MetricCard
          label="Last Sync"
          value={lastSync ? new Date(lastSync).toLocaleDateString() : '—'}
          sub={lastSync ? new Date(lastSync).toLocaleTimeString() : ''}
        />
        <MetricCard label="Conflicts" value={s?.conflicts_count ?? '—'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel
          title="Devices"
          subtitle="registered sync peers"
          actions={<Button size="sm" onClick={() => devices.reload()}>refresh</Button>}
        >
          {devices.loading ? (
            <Loading />
          ) : devices.error ? (
            <p className="text-[12px] text-helred">{devices.error}</p>
          ) : !devList.length ? (
            <EmptyState message="No devices registered." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="mono text-[10px] uppercase text-warmgray text-left">
                    <th className="py-1 pr-3">Name</th>
                    <th className="py-1 pr-3">Type</th>
                    <th className="py-1 pr-3">Platform</th>
                    <th className="py-1 pr-3">Status</th>
                    <th className="py-1 pr-3">Last Seen</th>
                    <th className="py-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {devList.map((d: any) => (
                    <tr key={d.device_id} className="border-t border-hairline">
                      <td className="py-1.5 pr-3 text-ivory/90">{d.name}</td>
                      <td className="py-1.5 pr-3 text-warmgray">{d.type}</td>
                      <td className="py-1.5 pr-3 text-warmgray">{d.platform}</td>
                      <td className="py-1.5 pr-3">
                        <StatusBadge status={deviceStatus(d)} label={d.status ?? 'unknown'} />
                      </td>
                      <td className="py-1.5 pr-3 mono text-[11px] text-warmgray">{fmtTs(d.last_seen)}</td>
                      <td className="py-1.5">
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={deregBusy === d.device_id}
                          onClick={() => deregisterDevice(d.device_id)}
                        >
                          {deregBusy === d.device_id ? '…' : 'Deregister'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Register Device" subtitle="add a new sync peer">
          <div className="flex flex-col gap-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Device name (e.g. My MacBook)"
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
            <select
              value={type}
              onChange={(e) => setType(e.target.value as any)}
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            >
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
              <option value="tablet">Tablet</option>
              <option value="server">Server</option>
            </select>
            <input
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              placeholder="Platform (e.g. macOS, Windows, iOS)"
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
            <Button
              variant="gold"
              onClick={registerDevice}
              disabled={busy || !name.trim() || !platform.trim()}
            >
              {busy ? 'Registering…' : 'Register Device'}
            </Button>
            {regErr && <p className="text-[11px] text-helred">{regErr}</p>}
          </div>
        </Panel>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Sync Status tab
// ---------------------------------------------------------------------------

function SyncStatusTab() {
  const status = useAsync(() => helios.sync.status(), []);
  const [selected, setSelected] = useState<Set<Component>>(new Set(COMPONENTS));
  const [allSelected, setAllSelected] = useState(true);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sessionResult, setSessionResult] = useState<any>(null);
  const [sessionErr, setSessionErr] = useState<string | null>(null);

  const s = status.data as any;
  const components = s?.components ?? {};

  function toggleComponent(c: Component) {
    const next = new Set(selected);
    if (next.has(c)) {
      next.delete(c);
    } else {
      next.add(c);
    }
    setSelected(next);
    setAllSelected(next.size === COMPONENTS.length);
  }

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
      setAllSelected(false);
    } else {
      setSelected(new Set(COMPONENTS));
      setAllSelected(true);
    }
  }

  async function startSession() {
    setSessionBusy(true);
    setSessionErr(null);
    setSessionResult(null);
    try {
      const comps = allSelected ? undefined : Array.from(selected);
      const result = await helios.sync.startSession({
        device_id: 'current',
        components: comps,
      });
      setSessionResult(result);
    } catch (e: any) {
      setSessionErr(e?.message ?? String(e));
    } finally {
      setSessionBusy(false);
    }
  }

  function componentHealth(comp: any): 'ok' | 'error' | 'warn' | 'idle' {
    if (!comp) return 'idle';
    const st = (comp.status ?? '').toLowerCase();
    if (st === 'synced' || st === 'ok') return 'ok';
    if (st === 'error' || st === 'failed') return 'error';
    if (st === 'pending' || st === 'syncing') return 'warn';
    return 'idle';
  }

  const totalPending = COMPONENTS.reduce((sum, c) => sum + (components[c]?.pending_records ?? 0), 0);
  const syncedCount = COMPONENTS.filter((c) => componentHealth(components[c]) === 'ok').length;

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Components synced" accent value={`${syncedCount}/${COMPONENTS.length}`} />
        <MetricCard label="Pending records" value={totalPending} />
        <MetricCard label="Active sessions" value={s?.sessions?.length ?? '—'} />
        <MetricCard label="Conflicts" value={s?.conflicts_count ?? '—'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel
          title="Component sync status"
          subtitle="per-component health"
          actions={<Button size="sm" onClick={() => status.reload()}>refresh</Button>}
        >
          {status.loading ? (
            <Loading />
          ) : status.error ? (
            <p className="text-[12px] text-helred">{status.error}</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {COMPONENTS.map((c) => {
                const comp = components[c];
                return (
                  <div
                    key={c}
                    className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5 flex items-center gap-3"
                  >
                    <StatusBadge status={componentHealth(comp)} label={comp?.status ?? 'idle'} />
                    <div className="flex-1">
                      <div className="text-[12px] text-ivory/90 capitalize">{c}</div>
                      {comp?.last_sync && (
                        <div className="text-[11px] text-warmgray mono">{fmtTs(comp.last_sync)}</div>
                      )}
                    </div>
                    {comp?.pending_records != null && (
                      <span className="mono text-[11px] text-gold">{comp.pending_records} pending</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Panel>

        <Panel title="Start Sync Session" subtitle="choose components to sync">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-[12px] cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                  className="accent-gold"
                />
                <span className="text-gold">All components</span>
              </label>
              <div className="pl-4 flex flex-col gap-1">
                {COMPONENTS.map((c) => (
                  <label key={c} className="flex items-center gap-2 text-[12px] cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={selected.has(c)}
                      onChange={() => toggleComponent(c)}
                      className="accent-gold"
                    />
                    <span className="text-ivory/90 capitalize">{c}</span>
                  </label>
                ))}
              </div>
            </div>

            <Button
              variant="gold"
              onClick={startSession}
              disabled={sessionBusy || selected.size === 0}
            >
              {sessionBusy ? 'Starting…' : 'Start Sync Session'}
            </Button>

            {sessionErr && <p className="text-[11px] text-helred">{sessionErr}</p>}
            {sessionResult && (
              <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2 text-[12px]">
                <span className="text-gold">Session started</span>
                {sessionResult.session_id && (
                  <span className="mono text-[11px] text-warmgray ml-2">{sessionResult.session_id}</span>
                )}
              </div>
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Conflicts tab
// ---------------------------------------------------------------------------

function ConflictsTab() {
  const conflicts = useAsync(() => helios.sync.listConflicts(), []);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const list: any[] = conflicts.data ?? [];

  async function resolveConflict(id: string, strategy: 'last_write_wins' | 'keep_local' | 'keep_remote') {
    setResolvingId(id);
    try {
      await helios.sync.resolveConflict(id, { strategy });
      conflicts.reload();
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <Panel
      title="Conflicts"
      subtitle={list.length > 0 ? `${list.length} unresolved` : 'no conflicts'}
      actions={<Button size="sm" onClick={() => conflicts.reload()}>refresh</Button>}
    >
      {conflicts.loading ? (
        <Loading />
      ) : conflicts.error ? (
        <p className="text-[12px] text-helred">{conflicts.error}</p>
      ) : !list.length ? (
        <EmptyState message="No unresolved conflicts." />
      ) : (
        <div className="flex flex-col gap-2">
          {list.map((c: any) => (
            <div key={c.conflict_id} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5">
              <div className="flex items-start gap-2 mb-2">
                <div className="flex flex-col gap-0.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="mono text-[10px] uppercase text-gold px-1.5 py-0.5 rounded border border-gold/30">
                      {c.component}
                    </span>
                    <span className="mono text-[11px] text-warmgray" title={c.record_id}>
                      {truncate(c.record_id, 20)}
                    </span>
                  </div>
                  <div className="text-[11px] text-warmgray mt-0.5">
                    Local <span className="text-ivory/90 mono">{c.local_version}</span>
                    {' vs '}
                    Remote <span className="text-ivory/90 mono">{c.remote_version}</span>
                  </div>
                  <div className="mono text-[10px] text-warmgray/70">{fmtTs(c.created_at)}</div>
                </div>
              </div>
              <div className="flex gap-1.5 flex-wrap">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={resolvingId === c.conflict_id}
                  onClick={() => resolveConflict(c.conflict_id, 'last_write_wins')}
                >
                  {resolvingId === c.conflict_id ? '…' : 'Last Write Wins'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={resolvingId === c.conflict_id}
                  onClick={() => resolveConflict(c.conflict_id, 'keep_local')}
                >
                  Keep Local
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={resolvingId === c.conflict_id}
                  onClick={() => resolveConflict(c.conflict_id, 'keep_remote')}
                >
                  Keep Remote
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Audit tab
// ---------------------------------------------------------------------------

function AuditTab() {
  const log = useAsync(() => helios.sync.auditLog(), []);
  const entries: any[] = log.data ?? [];

  return (
    <Panel
      title="Audit Log"
      subtitle="sync activity history"
      actions={<Button size="sm" onClick={() => log.reload()}>refresh</Button>}
      scroll
      className="max-h-[560px]"
    >
      {log.loading ? (
        <Loading />
      ) : log.error ? (
        <p className="text-[12px] text-helred">{log.error}</p>
      ) : !entries.length ? (
        <EmptyState message="No audit log entries yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="mono text-[10px] uppercase text-warmgray text-left sticky top-0 bg-obsidian">
                <th className="py-1 pr-3">Timestamp</th>
                <th className="py-1 pr-3">Device</th>
                <th className="py-1 pr-3">Component</th>
                <th className="py-1 pr-3">Action</th>
                <th className="py-1 text-right">Records</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e: any, i: number) => (
                <tr key={i} className="border-t border-hairline">
                  <td className="py-1.5 pr-3 mono text-[11px] text-warmgray whitespace-nowrap">{fmtTs(e.ts)}</td>
                  <td className="py-1.5 pr-3 mono text-[11px] text-warmgray" title={e.device_id}>
                    {truncate(e.device_id, 14)}
                  </td>
                  <td className="py-1.5 pr-3 text-ivory/90 capitalize">{e.component}</td>
                  <td className="py-1.5 pr-3 text-warmgray">{e.action}</td>
                  <td className="py-1.5 text-right mono text-[11px] text-gold">{e.record_count ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
