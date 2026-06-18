import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';

// ── utilities ────────────────────────────────────────────────────────────────

function fmtBytes(n: number): string {
  if (!n) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  if (n < 1024 * 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + ' MB';
  return (n / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function timeAgo(iso: string): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  if (isNaN(diff)) return iso;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function truncId(id: string): string {
  if (!id) return '—';
  return id.length > 12 ? id.slice(0, 12) + '…' : id;
}

// ── tab list ─────────────────────────────────────────────────────────────────

const TABS = ['Backups', 'Restore', 'Disaster Recovery'] as const;
type Tab = typeof TABS[number];

const COMPONENTS = ['accounting', 'vault', 'documents', 'memory'] as const;
type Component = typeof COMPONENTS[number];

// ── BackupsTab ────────────────────────────────────────────────────────────────

function BackupsTab() {
  const status = useAsync(() => (helios as any).backup.status(), []);
  const backups = useAsync(() => (helios as any).backup.list(), []);

  const [password, setPassword] = useState('');
  const [type, setType] = useState<'Full' | 'Incremental' | 'Selective'>('Full');
  const [components, setComponents] = useState<Set<Component>>(new Set());
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createResult, setCreateResult] = useState<any>(null);

  const [verifyStates, setVerifyStates] = useState<Record<string, { busy: boolean; result?: string; error?: string }>>({});

  const st = status.data as any;
  const list: any[] = backups.data ?? [];

  function toggleComponent(c: Component) {
    setComponents((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    setCreateResult(null);
    try {
      let result: any;
      if (type === 'Full') {
        result = await (helios as any).backup.createFull({ password });
      } else if (type === 'Incremental') {
        result = await (helios as any).backup.createIncremental({ password });
      } else {
        result = await (helios as any).backup.createSelective({ password, components: [...components] });
      }
      setCreateResult(result);
      backups.reload();
      status.reload();
    } catch (err: any) {
      setCreateError(err?.message || String(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleVerify(id: string) {
    setVerifyStates((prev) => ({ ...prev, [id]: { busy: true } }));
    try {
      await (helios as any).backup.verify(id);
      setVerifyStates((prev) => ({ ...prev, [id]: { busy: false, result: 'Verified' } }));
      backups.reload();
    } catch (err: any) {
      setVerifyStates((prev) => ({
        ...prev,
        [id]: { busy: false, error: err?.message || 'Verification failed' },
      }));
    }
  }

  return (
    <>
      {/* metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard
          label="Total Backups"
          value={status.loading ? '…' : (st?.total_backups ?? '—')}
        />
        <MetricCard
          label="Last Backup"
          value={status.loading ? '…' : (st?.last_backup_time ? timeAgo(st.last_backup_time) : '—')}
          sub={st?.last_backup_time ? new Date(st.last_backup_time).toLocaleDateString() : undefined}
        />
        <MetricCard
          label="Disk Usage"
          value={status.loading ? '…' : fmtBytes(st?.disk_usage)}
          accent
        />
        <MetricCard
          label="Verified"
          value={status.loading ? '…' : (st?.verified_count ?? '—')}
          sub="backups verified"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* create backup */}
        <Panel title="Create Backup" subtitle="full · incremental · selective">
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[11px] text-warmgray block mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Encryption password"
                className="w-full bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
              />
            </div>
            <div>
              <label className="text-[11px] text-warmgray block mb-1">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as typeof type)}
                className="w-full bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
              >
                <option value="Full">Full</option>
                <option value="Incremental">Incremental</option>
                <option value="Selective">Selective</option>
              </select>
            </div>

            {type === 'Selective' && (
              <div>
                <label className="text-[11px] text-warmgray block mb-1.5">Components</label>
                <div className="flex flex-col gap-1.5">
                  {COMPONENTS.map((c) => (
                    <label key={c} className="flex items-center text-[12px] cursor-pointer">
                      <input
                        type="checkbox"
                        className="mr-2"
                        checked={components.has(c)}
                        onChange={() => toggleComponent(c)}
                      />
                      <span className="capitalize">{c}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            <Button
              size="sm"
              variant="gold"
              onClick={handleCreate}
              disabled={creating || !password}
            >
              {creating ? 'Creating…' : `Create ${type} Backup`}
            </Button>

            {createError && (
              <div className="text-helred text-[11px]">{createError}</div>
            )}
            {createResult && (
              <div className="text-[11px] text-ivory/70 mono bg-obsidian/60 rounded-lg px-3 py-2">
                Backup created · ID: {truncId(createResult?.backup_id ?? '—')}
              </div>
            )}
          </div>
        </Panel>

        {/* backup list */}
        <Panel
          title="Backups"
          subtitle="all backup snapshots"
          actions={
            <Button size="sm" variant="ghost" onClick={() => backups.reload()}>
              Refresh
            </Button>
          }
        >
          {backups.loading ? (
            <Loading />
          ) : backups.error ? (
            <EmptyState message="Could not load backups." />
          ) : !list.length ? (
            <EmptyState message="No backups yet. Create one above." />
          ) : (
            <ul className="flex flex-col gap-1.5">
              {list.map((b: any) => {
                const vs = verifyStates[b.backup_id] ?? {};
                return (
                  <li
                    key={b.backup_id}
                    className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2 text-[12px]"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="mono text-gold shrink-0">{truncId(b.backup_id)}</span>
                      <span className="text-warmgray capitalize shrink-0">{b.type}</span>
                      <StatusBadge
                        status={
                          b.status === 'ok' || b.status === 'complete'
                            ? 'ok'
                            : b.status === 'error' || b.status === 'failed'
                            ? 'error'
                            : 'idle'
                        }
                        label={b.status}
                      />
                      <span className="mono text-[11px] text-warmgray">{fmtBytes(b.size_bytes)}</span>
                      <span className="text-[11px] text-warmgray/70 shrink-0">
                        {b.created_at ? timeAgo(b.created_at) : '—'}
                      </span>
                      <span className={b.verified ? 'text-[11px] text-helgreen' : 'text-[11px] text-warmgray/50'}>
                        {b.verified ? '✓' : '–'}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleVerify(b.backup_id)}
                        disabled={vs.busy}
                      >
                        {vs.busy ? 'Verifying…' : 'Verify'}
                      </Button>
                    </div>
                    {vs.result && (
                      <div className="text-[11px] text-helgreen mt-1">{vs.result}</div>
                    )}
                    {vs.error && (
                      <div className="text-[11px] text-helred mt-1">{vs.error}</div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>
    </>
  );
}

// ── RestoreTab ────────────────────────────────────────────────────────────────

function RestoreTab() {
  const points = useAsync(() => (helios as any).backup.restorePoints(), []);
  const allPoints: any[] = points.data ?? [];

  const [componentFilter, setComponentFilter] = useState('');
  const [selected, setSelected] = useState<any>(null);
  const [restoreType, setRestoreType] = useState<'Full' | 'Selective'>('Full');
  const [restoreComponents, setRestoreComponents] = useState<Set<Component>>(new Set());
  const [password, setPassword] = useState('');
  const [dryRun, setDryRun] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreResult, setRestoreResult] = useState<any>(null);

  const uniqueComponents = [...new Set(allPoints.map((p: any) => p.component).filter(Boolean))];
  const filtered = componentFilter
    ? allPoints.filter((p: any) => p.component === componentFilter)
    : allPoints;

  function toggleRestoreComponent(c: Component) {
    setRestoreComponents((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }

  async function handleRestore() {
    if (!selected) return;
    setRestoring(true);
    setRestoreError(null);
    setRestoreResult(null);
    try {
      let result: any;
      if (restoreType === 'Full') {
        result = await (helios as any).backup.restoreFull({
          backup_id: selected.backup_id,
          password,
          dry_run: dryRun,
        });
      } else {
        result = await (helios as any).backup.restoreSelective({
          backup_id: selected.backup_id,
          password,
          components: [...restoreComponents],
          dry_run: dryRun,
        });
      }
      setRestoreResult(result);
    } catch (err: any) {
      setRestoreError(err?.message || String(err));
    } finally {
      setRestoring(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      {/* restore points list */}
      <Panel
        title="Restore Points"
        subtitle="select a point to restore from"
        actions={
          uniqueComponents.length > 0 ? (
            <select
              value={componentFilter}
              onChange={(e) => setComponentFilter(e.target.value)}
              className="bg-obsidian/60 border border-hairline rounded-lg px-2 py-1 text-[11px] outline-none focus:border-gold/40"
            >
              <option value="">All components</option>
              {uniqueComponents.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          ) : undefined
        }
      >
        {points.loading ? (
          <Loading />
        ) : points.error ? (
          <EmptyState message="Could not load restore points." />
        ) : !filtered.length ? (
          <EmptyState message="No restore points found." />
        ) : (
          <ul className="flex flex-col gap-1.5">
            {filtered.map((p: any, i: number) => (
              <li
                key={p.backup_id + (p.component ?? '') + i}
                onClick={() => setSelected(p)}
                className={[
                  'rounded-lg border px-3 py-2 text-[12px] cursor-pointer transition-colors',
                  selected?.backup_id === p.backup_id && selected?.component === p.component
                    ? 'border-gold/50 bg-gold/10'
                    : 'border-hairline bg-obsidian/40 hover:border-gold/30',
                ].join(' ')}
              >
                <div className="flex items-center gap-2">
                  <span className="mono text-gold">{truncId(p.backup_id)}</span>
                  {p.component && (
                    <span className="mono text-[11px] text-warmgray capitalize">{p.component}</span>
                  )}
                  <span className="text-[11px] text-warmgray/70 ml-auto">
                    {p.created_at ? timeAgo(p.created_at) : '—'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {/* restore form */}
      <Panel title="Restore" subtitle="configure and execute restore">
        <div className="flex flex-col gap-3">
          <div>
            <div className="text-[11px] text-warmgray mb-1">Selected Restore Point</div>
            <div className="mono text-[12px] bg-obsidian/60 border border-hairline rounded-lg px-3 py-2">
              {selected ? truncId(selected.backup_id) : (
                <span className="text-warmgray/60">Select a restore point on the left</span>
              )}
            </div>
          </div>

          <div>
            <label className="text-[11px] text-warmgray block mb-1">Restore Type</label>
            <select
              value={restoreType}
              onChange={(e) => setRestoreType(e.target.value as typeof restoreType)}
              className="w-full bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            >
              <option value="Full">Full</option>
              <option value="Selective">Selective</option>
            </select>
          </div>

          {restoreType === 'Selective' && (
            <div>
              <label className="text-[11px] text-warmgray block mb-1.5">Components</label>
              <div className="flex flex-col gap-1.5">
                {COMPONENTS.map((c) => (
                  <label key={c} className="flex items-center text-[12px] cursor-pointer">
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={restoreComponents.has(c)}
                      onChange={() => toggleRestoreComponent(c)}
                    />
                    <span className="capitalize">{c}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="text-[11px] text-warmgray block mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Backup password"
              className="w-full bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
          </div>

          <label className="flex items-center text-[12px] cursor-pointer">
            <input
              type="checkbox"
              className="mr-2"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            <span>Dry run <span className="text-warmgray">(preview only)</span></span>
          </label>

          <Button
            size="sm"
            variant={dryRun ? 'ghost' : 'primary'}
            onClick={handleRestore}
            disabled={restoring || !selected || !password}
          >
            {restoring ? 'Restoring…' : dryRun ? 'Preview Restore' : 'Restore Now'}
          </Button>

          {restoreError && (
            <div className="text-helred text-[11px]">{restoreError}</div>
          )}

          {restoreResult && (
            <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
              <div className="text-[11px] text-gold mb-1.5">
                {dryRun ? 'Dry run result' : 'Restore complete'}
              </div>
              <pre className="text-[11px] text-warmgray whitespace-pre-wrap break-all max-h-48 overflow-y-auto scroll-thin">
                {JSON.stringify(restoreResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}

// ── DRTab ─────────────────────────────────────────────────────────────────────

type DRAction = 'integrity' | 'plan' | 'report';

interface DRActionState {
  busy: boolean;
  result: any;
  error: string | null;
}

const DR_INITIAL: DRActionState = { busy: false, result: null, error: null };

function DRTab() {
  const drStatus = useAsync(() => (helios as any).backup.drStatus(), []);
  const st = drStatus.data as any;

  const [integrity, setIntegrity] = useState<DRActionState>(DR_INITIAL);
  const [plan, setPlan] = useState<DRActionState>(DR_INITIAL);
  const [report, setReport] = useState<DRActionState>(DR_INITIAL);

  async function runAction(
    action: DRAction,
    setter: React.Dispatch<React.SetStateAction<DRActionState>>,
  ) {
    setter({ busy: true, result: null, error: null });
    try {
      let result: any;
      if (action === 'integrity') result = await (helios as any).backup.drIntegrity();
      else if (action === 'plan') result = await (helios as any).backup.drPlan();
      else result = await (helios as any).backup.drReport();
      setter({ busy: false, result, error: null });
    } catch (err: any) {
      setter({ busy: false, result: null, error: err?.message || String(err) });
    }
  }

  function formatResult(r: any): string {
    if (typeof r === 'string') return r;
    return JSON.stringify(r, null, 2);
  }

  return (
    <div className="flex flex-col gap-3">
      {/* DR Status */}
      <Panel title="DR Status" subtitle="disaster recovery posture">
        {drStatus.loading ? (
          <Loading />
        ) : drStatus.error ? (
          <EmptyState message="Could not load DR status." />
        ) : !st ? (
          <EmptyState message="No DR status available." />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(st).map(([k, v]) => (
              <div
                key={k}
                className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2"
              >
                <div className="text-[11px] text-gold mb-0.5 capitalize">
                  {k.replace(/_/g, ' ')}
                </div>
                <div className="text-[12px] mono break-all">
                  {v === null || v === undefined
                    ? '—'
                    : typeof v === 'boolean'
                    ? v ? 'yes' : 'no'
                    : String(v)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Integrity Check */}
      <Panel
        title="Integrity Check"
        subtitle="verify backup chain consistency"
        actions={
          <Button
            size="sm"
            variant="ghost"
            onClick={() => runAction('integrity', setIntegrity)}
            disabled={integrity.busy}
          >
            {integrity.busy ? 'Running…' : 'Run Integrity Check'}
          </Button>
        }
      >
        {integrity.busy ? (
          <Loading />
        ) : integrity.error ? (
          <div className="text-helred text-[11px]">{integrity.error}</div>
        ) : integrity.result ? (
          <pre className="text-[11px] text-warmgray whitespace-pre-wrap break-all max-h-64 overflow-y-auto scroll-thin mono">
            {formatResult(integrity.result)}
          </pre>
        ) : (
          <p className="text-[12px] text-warmgray">
            Run an integrity check to verify your backup chain is consistent and recoverable.
          </p>
        )}
      </Panel>

      {/* Recovery Plan */}
      <Panel
        title="Recovery Plan"
        subtitle="step-by-step restore procedure"
        actions={
          <Button
            size="sm"
            variant="ghost"
            onClick={() => runAction('plan', setPlan)}
            disabled={plan.busy}
          >
            {plan.busy ? 'Generating…' : 'Generate Recovery Plan'}
          </Button>
        }
      >
        {plan.busy ? (
          <Loading />
        ) : plan.error ? (
          <div className="text-helred text-[11px]">{plan.error}</div>
        ) : plan.result ? (
          <pre className="text-[11px] text-warmgray whitespace-pre-wrap break-all max-h-64 overflow-y-auto scroll-thin mono">
            {formatResult(plan.result)}
          </pre>
        ) : (
          <p className="text-[12px] text-warmgray">
            Generate a structured recovery plan outlining the steps required to restore from your latest backup.
          </p>
        )}
      </Panel>

      {/* DR Report */}
      <Panel
        title="DR Report"
        subtitle="comprehensive disaster recovery assessment"
        actions={
          <Button
            size="sm"
            variant="ghost"
            onClick={() => runAction('report', setReport)}
            disabled={report.busy}
          >
            {report.busy ? 'Generating…' : 'Generate DR Report'}
          </Button>
        }
      >
        {report.busy ? (
          <Loading />
        ) : report.error ? (
          <div className="text-helred text-[11px]">{report.error}</div>
        ) : report.result ? (
          <pre className="text-[11px] text-warmgray whitespace-pre-wrap break-all max-h-72 overflow-y-auto scroll-thin mono">
            {formatResult(report.result)}
          </pre>
        ) : (
          <p className="text-[12px] text-warmgray">
            Generate a full DR report covering backup coverage, retention policy, RTO/RPO estimates, and recommendations.
          </p>
        )}
      </Panel>
    </div>
  );
}

// ── BackupView ────────────────────────────────────────────────────────────────

export function BackupView() {
  if (!helios.hasBridge()) {
    return <EmptyState message="Open in desktop app to use Backup & Recovery." />;
  }

  const [tab, setTab] = useState<Tab>('Backups');

  return (
    <Page
      title="Backup & Recovery"
      subtitle="backups · restore · disaster recovery"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button
              key={t}
              size="sm"
              variant={t === tab ? 'primary' : 'ghost'}
              onClick={() => setTab(t)}
            >
              {t}
            </Button>
          ))}
        </div>
      }
    >
      {tab === 'Backups' && <BackupsTab />}
      {tab === 'Restore' && <RestoreTab />}
      {tab === 'Disaster Recovery' && <DRTab />}
    </Page>
  );
}
