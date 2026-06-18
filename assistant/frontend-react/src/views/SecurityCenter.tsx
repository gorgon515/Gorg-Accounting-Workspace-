import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Overview', 'Vault', 'Backup & Recovery', 'Sync', 'Compliance', 'Permissions'] as const;
type Tab = typeof TABS[number];

export function SecurityCenter() {
  const [tab, setTab] = useState<Tab>('Overview');
  return (
    <Page title="Security Center" subtitle="vault · encryption · backup · recovery · sync · compliance"
      actions={
        <div className="flex flex-wrap gap-1">
          {TABS.map((t) => <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>)}
        </div>
      }>
      {tab === 'Overview' && <Overview />}
      {tab === 'Vault' && <VaultPanel />}
      {tab === 'Backup & Recovery' && <BackupRecovery />}
      {tab === 'Sync' && <SyncPanel />}
      {tab === 'Compliance' && <Compliance />}
      {tab === 'Permissions' && <Permissions />}
    </Page>
  );
}

// ------------------------------- Overview -------------------------------
function Overview() {
  const status = useAsync(() => helios.sidecar.securityStatus(), [], 8000);
  const health = useAsync(() => helios.sidecar.securityHealth(), [], 8000);
  const ledger = useAsync(() => helios.sidecar.integrityLedger(), []);
  const s = status.data;
  const h = health.data;
  if (status.loading && !s) return <Loading />;
  const vault = s?.vault ?? {};
  const chain = s?.compliance?.chain ?? {};
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Vault" accent value={vault.initialized ? (vault.unlocked ? 'Unlocked' : 'Locked') : 'Not set'} />
        <MetricCard label="Encryption" value={vault.algorithm || 'AES-256-GCM'} />
        <MetricCard label="Secrets" value={vault.secret_count ?? 0} />
        <MetricCard label="Audit chain" value={chain.valid ? 'Intact ✓' : 'Broken ✗'} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="System health" subtitle={h ? `${h.status} · ${Math.round(h.uptime_seconds)}s uptime` : ''}>
          {health.loading && !h ? <Loading /> : !h ? <EmptyState message="Health unavailable." /> : (
            <table className="w-full text-[12px]">
              <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Store</th><th className="text-right">Tables</th><th className="text-right">Size</th><th className="text-right">OK</th></tr></thead>
              <tbody>
                {Object.entries(h.stores || {}).map(([name, st]: any) => (
                  <tr key={name} className="border-t border-hairline">
                    <td className="py-1">{name}</td>
                    <td className="text-right">{st.tables}</td>
                    <td className="text-right mono">{fmtBytes(st.size_bytes)}</td>
                    <td className="text-right">{st.ok ? <span className="text-helgreen">✓</span> : <span className="text-helred">✗</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel title="Data integrity" subtitle="double-entry ledger consistency"
          actions={<Button size="sm" onClick={() => ledger.reload()}>Re-scan</Button>}>
          {ledger.loading ? <Loading /> : !ledger.data ? <EmptyState message="No ledger data." /> : (
            <div className="flex flex-col gap-2 text-[12px]">
              <Row label="Posted entries checked" value={ledger.data.entries_checked} />
              <Row label="Debits" value={`$${num(ledger.data.global_debits)}`} />
              <Row label="Credits" value={`$${num(ledger.data.global_credits)}`} />
              <Row label="Globally balanced" value={ledger.data.global_balanced ? 'Yes ✓' : 'No ✗'} />
              <Row label="Trial balance ties" value={ledger.data.trial_balance_balanced ? 'Yes ✓' : 'No ✗'} />
              <div className="mt-1">
                <StatusBadge status={ledger.data.valid ? 'ready' : 'error'} label={ledger.data.valid ? 'Ledger integrity verified' : 'Integrity issue detected'} />
              </div>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

// ------------------------------- Vault -------------------------------
function VaultPanel() {
  const status = useAsync(() => helios.sidecar.securityStatus(), [], 6000);
  const secrets = useAsync(() => helios.sidecar.vaultSecrets(), []);
  const [pw, setPw] = useState('');
  const [ref, setRef] = useState('');
  const [val, setVal] = useState('');
  const [msg, setMsg] = useState('');
  const vault = status.data?.vault ?? {};

  async function act(fn: () => Promise<any>, ok: string) {
    setMsg('');
    try { await fn(); setMsg(ok); setPw(''); status.reload(); secrets.reload(); }
    catch (e: any) { setMsg(e?.message || String(e)); }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Vault control" subtitle={vault.initialized ? (vault.unlocked ? 'unlocked' : 'locked') : 'not initialized'}>
        <div className="flex flex-col gap-2">
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="master password"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono" />
          <div className="flex flex-wrap gap-2">
            {!vault.initialized && <Button size="sm" variant="gold" onClick={() => act(() => helios.sidecar.vaultInitialize(pw), 'Vault initialized & unlocked.')}>Initialize</Button>}
            {vault.initialized && !vault.unlocked && <Button size="sm" variant="gold" onClick={() => act(() => helios.sidecar.vaultUnlock(pw), 'Unlocked.')}>Unlock</Button>}
            {vault.unlocked && <Button size="sm" onClick={() => act(() => helios.sidecar.vaultLock(), 'Locked.')}>Lock</Button>}
          </div>
          <p className="text-[11px] text-warmgray leading-relaxed mt-1">
            Secrets are encrypted with AES-256-GCM under a key derived from your master password via scrypt.
            Plaintext is never stored. The data key encrypting memory, documents and sync lives inside the vault.
          </p>
          {msg && <div className="text-[11px] text-gold">{msg}</div>}
        </div>
      </Panel>
      <Panel title="Add / rotate secret" subtitle="requires unlock">
        <div className="flex flex-col gap-2">
          <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="ref (e.g. broker:apikey)"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono" />
          <input value={val} onChange={(e) => setVal(e.target.value)} placeholder="secret value"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono" />
          <Button size="sm" variant="gold" disabled={!vault.unlocked || !ref || !val}
            onClick={() => act(async () => { await helios.sidecar.vaultSetSecret({ ref, value: val }); setRef(''); setVal(''); }, 'Secret stored.')}>
            Store secret
          </Button>
        </div>
      </Panel>
      <Panel title="Stored secrets" subtitle="metadata only — plaintext never listed" className="lg:col-span-2" scroll>
        {secrets.loading ? <Loading /> : !(secrets.data?.secrets?.length) ? <EmptyState message="No secrets yet. Unlock the vault and add one." /> : (
          <table className="w-full text-[12px]">
            <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Ref</th><th>Category</th><th className="text-right">Version</th><th className="text-right">Updated</th></tr></thead>
            <tbody>
              {secrets.data.secrets.map((sec: any) => (
                <tr key={sec.ref} className="border-t border-hairline">
                  <td className="py-1 mono">{sec.ref}</td>
                  <td>{sec.category}</td>
                  <td className="text-right">v{sec.version}</td>
                  <td className="text-right mono text-warmgray">{(sec.updated_at || '').slice(0, 19).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

// ------------------------- Backup & Recovery -------------------------
function BackupRecovery() {
  const list = useAsync(() => helios.sidecar.backupList(), []);
  const plan = useAsync(() => helios.sidecar.recoveryPlan(), []);
  const [pw, setPw] = useState('');
  const [msg, setMsg] = useState('');
  const [drill, setDrill] = useState<any>(null);
  const backups = list.data?.backups ?? [];

  async function run(fn: () => Promise<any>, ok: string) {
    setMsg('');
    try { const r = await fn(); setMsg(ok); list.reload(); plan.reload(); return r; }
    catch (e: any) { setMsg(e?.message || String(e)); }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Create backup" subtitle="AES-256-GCM encrypted · gzip compressed">
        <div className="flex flex-col gap-2">
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="backup password"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono" />
          <div className="flex gap-2">
            <Button size="sm" variant="gold" disabled={!pw} onClick={() => run(() => helios.sidecar.backupCreate({ password: pw, kind: 'full' }), 'Full backup created.')}>Full backup</Button>
            <Button size="sm" disabled={!pw} onClick={() => run(() => helios.sidecar.backupCreate({ password: pw, kind: 'incremental' }), 'Incremental backup created.')}>Incremental</Button>
          </div>
          {msg && <div className="text-[11px] text-gold">{msg}</div>}
        </div>
      </Panel>
      <Panel title="Disaster recovery" subtitle={plan.data?.ready ? `ready · recovery point ${(plan.data.recovery_point || '').slice(0, 19).replace('T', ' ')}` : 'no recoverable backup'}>
        {plan.loading ? <Loading /> : (
          <div className="flex flex-col gap-2 text-[12px]">
            <StatusBadge status={plan.data?.ready ? 'ready' : 'error'} label={plan.data?.ready ? 'Recovery plan ready' : 'Not ready'} />
            {plan.data?.ready && <Row label="Base backup" value={plan.data.base_backup} />}
            {plan.data?.ready && <Row label="Incrementals layered" value={plan.data.incrementals?.length ?? 0} />}
            <Button size="sm" className="mt-1" disabled={!pw || !plan.data?.ready}
              onClick={async () => { const r = await run(() => helios.sidecar.recoverySimulate(pw), 'Recovery drill complete.'); setDrill(r); }}>
              Run recovery drill (non-destructive)
            </Button>
            {drill && <div className={cls('text-[11px]', drill.success ? 'text-helgreen' : 'text-helred')}>
              {drill.success ? `Drill OK — ${drill.restored_targets} targets rebuilt at ${(drill.recovery_point || '').slice(0, 19).replace('T', ' ')}` : `Drill failed: ${drill.reason}`}
            </div>}
          </div>
        )}
      </Panel>
      <Panel title="Backup catalog" subtitle="checksum-verified snapshots" className="lg:col-span-2" scroll>
        {list.loading ? <Loading /> : !backups.length ? <EmptyState message="No backups yet. Create one above." /> : (
          <table className="w-full text-[12px]">
            <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Backup</th><th>Kind</th><th className="text-right">Size</th><th className="text-right">Created</th><th className="text-right">Verify</th></tr></thead>
            <tbody>
              {backups.map((b: any) => <BackupRow key={b.backup_id} b={b} />)}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function BackupRow({ b }: { b: any }) {
  const [v, setV] = useState<boolean | null>(null);
  return (
    <tr className="border-t border-hairline">
      <td className="py-1 mono">{b.backup_id}</td>
      <td>{b.kind}</td>
      <td className="text-right mono">{fmtBytes(b.size_bytes)}</td>
      <td className="text-right mono text-warmgray">{(b.created_at || '').slice(0, 19).replace('T', ' ')}</td>
      <td className="text-right">
        {v === null
          ? <Button size="sm" onClick={async () => setV((await helios.sidecar.backupVerify(b.backup_id)).valid)}>Verify</Button>
          : <span className={v ? 'text-helgreen' : 'text-helred'}>{v ? 'valid ✓' : 'corrupt ✗'}</span>}
      </td>
    </tr>
  );
}

// ------------------------------- Sync -------------------------------
function SyncPanel() {
  const status = useAsync(() => helios.sidecar.syncStatus().catch(() => null), [], 6000);
  const devices = useAsync(() => helios.sidecar.syncDevices().catch(() => ({ devices: [] })), []);
  const conflicts = useAsync(() => helios.sidecar.syncConflicts().catch(() => ({ conflicts: [] })), []);
  const [name, setName] = useState('');
  const [msg, setMsg] = useState('');
  const locked = !status.data;

  async function add() {
    setMsg('');
    try { await helios.sidecar.syncRegisterDevice(name || 'device'); setName(''); devices.reload(); status.reload(); setMsg('Device registered.'); }
    catch (e: any) { setMsg(e?.message || 'Vault must be unlocked for sync.'); }
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Server version" accent value={status.data?.server_version ?? '—'} />
        <MetricCard label="Devices" value={status.data?.devices ?? '—'} />
        <MetricCard label="Records" value={status.data?.records ?? '—'} />
        <MetricCard label="Conflicts" value={status.data?.conflicts ?? '—'} />
      </div>
      {locked && <Panel title="Sync locked"><EmptyState message="Unlock the vault (Vault tab) to enable encrypted multi-device sync." /></Panel>}
      {!locked && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="Register device">
            <div className="flex gap-2">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="device name (e.g. laptop)"
                className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono" />
              <Button size="sm" variant="gold" onClick={add}>Register</Button>
            </div>
            {msg && <div className="text-[11px] text-gold mt-2">{msg}</div>}
            <p className="text-[11px] text-warmgray leading-relaxed mt-2">
              Delta sync with a server version clock. Payloads are AES-256-GCM encrypted in transit and at rest;
              concurrent edits are recorded as conflicts and resolved last-write-wins.
            </p>
          </Panel>
          <Panel title="Devices" scroll>
            {!(devices.data?.devices?.length) ? <EmptyState message="No devices registered." /> : (
              <table className="w-full text-[12px]">
                <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Device</th><th>ID</th><th className="text-right">Last pull</th></tr></thead>
                <tbody>
                  {devices.data.devices.map((d: any) => (
                    <tr key={d.device_id} className="border-t border-hairline">
                      <td className="py-1">{d.name}</td>
                      <td className="mono text-warmgray">{d.device_id}</td>
                      <td className="text-right">v{d.last_pull_version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
          <Panel title="Conflicts (last-write-wins)" className="lg:col-span-2" scroll>
            {!(conflicts.data?.conflicts?.length) ? <EmptyState message="No sync conflicts recorded." /> : (
              <table className="w-full text-[12px]">
                <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">When</th><th>Key</th><th className="text-right">Base→Current</th><th>Resolution</th></tr></thead>
                <tbody>
                  {conflicts.data.conflicts.map((c: any, i: number) => (
                    <tr key={i} className="border-t border-hairline">
                      <td className="py-1 mono text-warmgray">{(c.ts || '').slice(0, 19).replace('T', ' ')}</td>
                      <td className="mono">{c.key}</td>
                      <td className="text-right">{c.base_version}→{c.current_version}</td>
                      <td>{c.resolution}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}

// ----------------------------- Compliance -----------------------------
function Compliance() {
  const stats = useAsync(() => helios.sidecar.complianceStats(), [], 8000);
  const events = useAsync(() => helios.sidecar.complianceEvents(), [], 8000);
  const audit = useAsync(() => helios.sidecar.integrityAudit(), []);
  const evs = events.data?.events ?? [];
  const chain = stats.data?.chain ?? {};
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Total events" accent value={stats.data?.total ?? 0} />
        <MetricCard label="Chain" value={chain.valid ? 'Intact ✓' : 'Broken ✗'} />
        <MetricCard label="Events checked" value={chain.events_checked ?? 0} />
        <MetricCard label="Audit trail" value={audit.data?.valid ? 'Complete ✓' : audit.loading ? '…' : 'Gaps ✗'} />
      </div>
      <Panel title="Immutable compliance log" subtitle="hash-chained · tamper-evident" scroll className="max-h-[520px]">
        {events.loading ? <Loading /> : !evs.length ? <EmptyState message="No compliance events recorded yet." /> : (
          <table className="w-full text-[12px]">
            <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">When</th><th>Category</th><th>Action</th><th>Actor</th></tr></thead>
            <tbody>
              {evs.map((e: any) => (
                <tr key={e.id} className="border-t border-hairline">
                  <td className="py-1 mono text-warmgray">{(e.ts || '').slice(0, 19).replace('T', ' ')}</td>
                  <td><span className="mono text-[10px] uppercase text-gold">{e.category}</span></td>
                  <td>{e.action}</td>
                  <td className="text-warmgray">{e.actor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}

// ----------------------------- Permissions -----------------------------
function Permissions() {
  const matrix = useAsync(() => helios.sidecar.permissionMatrix(), []);
  const m = matrix.data?.matrix ?? {};
  return (
    <Panel title="Agent security model" subtitle={matrix.data?.invariant || 'no agent may approve or execute money/filing actions'} scroll className="max-h-[600px]">
      {matrix.loading ? <Loading /> : !Object.keys(m).length ? <EmptyState message="Permission matrix unavailable." /> : (
        <table className="w-full text-[12px]">
          <thead><tr className="mono text-[10px] uppercase text-warmgray text-left">
            <th className="py-1">Agent</th><th>Memory</th><th>Documents</th><th>Execution</th><th>Approval</th><th>Audited</th>
          </tr></thead>
          <tbody>
            {Object.entries(m).map(([agent, p]: any) => (
              <tr key={agent} className="border-t border-hairline">
                <td className="py-1">{agent}</td>
                <td className="mono text-[11px]">{p.memory}</td>
                <td>{p.documents ? '✓' : '—'}</td>
                <td className="mono text-[11px]">{p.execution}</td>
                <td className={p.approval ? 'text-helred' : 'text-helgreen'}>{p.approval ? 'yes' : 'never'}</td>
                <td>{p.audit ? '✓' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

// ------------------------------- helpers -------------------------------
function Row({ label, value }: { label: string; value: any }) {
  return <div className="flex justify-between"><span className="text-warmgray">{label}</span><span className="mono">{value}</span></div>;
}
function fmtBytes(n: number): string {
  if (!n) return '0 B';
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}
function num(n: number): string {
  return (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
