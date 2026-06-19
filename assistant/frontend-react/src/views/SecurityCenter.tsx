import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Overview', 'Vault', 'Events', 'Compliance'] as const;
type Tab = typeof TABS[number];

export function SecurityCenter() {
  const [tab, setTab] = useState<Tab>('Overview');

  if (!helios.hasBridge()) {
    return <EmptyState message="Open in desktop app to use Security Center." />;
  }

  return (
    <Page
      title="Security Center"
      subtitle="vault · compliance · events"
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
      {tab === 'Overview' && <OverviewTab />}
      {tab === 'Vault' && <VaultTab />}
      {tab === 'Events' && <EventsTab />}
      {tab === 'Compliance' && <ComplianceTab />}
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Overview tab
// ---------------------------------------------------------------------------

function OverviewTab() {
  const status = useAsync(() => helios.security.status(), []);
  const log = useAsync(() => helios.security.complianceLog({ limit: 20 }), []);

  const checks: any[] = status.data?.checks ?? [];
  const entries: any[] = log.data?.entries ?? log.data ?? [];

  const vaultStatus = status.data?.vault_status ?? status.data?.vault?.status ?? '—';
  const backupStatus = status.data?.backup_status ?? '—';
  const syncDevices = status.data?.sync_devices ?? status.data?.devices ?? '—';
  const activeSecrets = status.data?.active_secrets ?? status.data?.secrets_count ?? '—';

  const alerts = checks.filter(
    (c: any) => c.level === 'critical' || c.status === 'error',
  );

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Vault Status" accent value={vaultStatus} sub="encrypted store" />
        <MetricCard label="Backup Status" value={backupStatus} sub="last snapshot" />
        <MetricCard label="Sync Devices" value={syncDevices} sub="registered" />
        <MetricCard label="Active Secrets" value={activeSecrets} sub="in vault" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-3">
        <Panel title="Security Health" subtitle="live check results">
          {status.loading ? (
            <Loading />
          ) : status.error ? (
            <EmptyState message={status.error} />
          ) : !checks.length ? (
            <EmptyState message="No security checks available." />
          ) : (
            <table className="w-full text-[12px]">
              <thead>
                <tr className="mono text-[10px] uppercase text-warmgray text-left">
                  <th className="py-1 pr-3">Check</th>
                  <th className="py-1 pr-3">Status</th>
                  <th className="py-1">Detail</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((c: any, i: number) => (
                  <tr key={i} className="border-t border-hairline">
                    <td className="py-1.5 pr-3 text-ivory/90">{c.name ?? c.check}</td>
                    <td className="py-1.5 pr-3">
                      <CheckDot status={c.status ?? c.level} />
                    </td>
                    <td className="py-1.5 text-warmgray truncate max-w-[200px]">{c.detail ?? c.message ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel title="Risk Alerts" subtitle="critical / error items">
          {status.loading ? (
            <Loading />
          ) : !alerts.length ? (
            <EmptyState message="No critical alerts." />
          ) : (
            <ul className="flex flex-col gap-2">
              {alerts.map((a: any, i: number) => (
                <li key={i} className="rounded-lg border border-helred/30 bg-helred/5 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-helred shrink-0" />
                    <span className="text-[12px] text-ivory/90 font-medium">{a.name ?? a.check}</span>
                  </div>
                  {(a.detail ?? a.message) && (
                    <p className="text-[11px] text-warmgray mt-1 pl-4">{a.detail ?? a.message}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="Recent Security Events" subtitle="last 20 entries">
        {log.loading ? (
          <Loading />
        ) : log.error ? (
          <EmptyState message={log.error} />
        ) : !entries.length ? (
          <EmptyState message="No events recorded." />
        ) : (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="mono text-[10px] uppercase text-warmgray text-left">
                <th className="py-1 pr-3">Time</th>
                <th className="py-1 pr-3">Event</th>
                <th className="py-1 pr-3">Actor</th>
                <th className="py-1">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e: any, i: number) => (
                <tr key={i} className="border-t border-hairline">
                  <td className="py-1.5 pr-3 mono text-[11px] text-warmgray whitespace-nowrap">
                    {fmtTs(e.ts ?? e.timestamp)}
                  </td>
                  <td className="py-1.5 pr-3 text-ivory/90">{e.event_type ?? e.event}</td>
                  <td className="py-1.5 pr-3 text-warmgray">{e.actor ?? '—'}</td>
                  <td className={cls('py-1.5 mono text-[11px]', outcomeColor(e.outcome))}>
                    {e.outcome ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Vault tab
// ---------------------------------------------------------------------------

function VaultTab() {
  const vault = useAsync(() => helios.security.vaultStatus(), []);
  const secrets = useAsync(() => helios.security.listSecrets(), []);
  const audit = useAsync(() => helios.security.vaultAudit(), []);

  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState('');

  const [addName, setAddName] = useState('');
  const [addValue, setAddValue] = useState('');
  const [addCategory, setAddCategory] = useState('general');
  const [addDesc, setAddDesc] = useState('');
  const [addBusy, setAddBusy] = useState(false);
  const [addErr, setAddErr] = useState('');

  const [rotateMap, setRotateMap] = useState<Record<string, string>>({});
  const [rotateBusy, setRotateBusy] = useState<Record<string, boolean>>({});

  const vaultData = vault.data as any;
  const isUnlocked = vaultData?.status === 'unlocked';
  const isUninitialized =
    !vaultData || vaultData?.status === 'uninitialized' || vaultData?.initialized === false;
  const secretList: any[] = secrets.data?.secrets ?? secrets.data ?? [];
  const auditLog: any[] = audit.data?.entries ?? audit.data ?? [];

  async function handleVaultAction() {
    if (!password) return;
    setBusy(true);
    setFormErr('');
    try {
      if (isUninitialized) {
        await helios.security.vaultInit({ password });
      } else {
        await helios.security.vaultUnlock({ password });
      }
      setPassword('');
      vault.reload();
      secrets.reload();
    } catch (e: any) {
      setFormErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleLock() {
    setBusy(true);
    try {
      await helios.security.vaultLock();
      vault.reload();
      secrets.reload();
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(name: string) {
    try {
      await helios.security.deleteSecret(name);
    } finally {
      secrets.reload();
    }
  }

  async function handleRotate(name: string) {
    const newVal = rotateMap[name];
    if (!newVal) return;
    setRotateBusy((p) => ({ ...p, [name]: true }));
    try {
      await helios.security.rotateSecret(name, { new_value: newVal });
      setRotateMap((p) => {
        const n = { ...p };
        delete n[name];
        return n;
      });
      secrets.reload();
    } catch {
      secrets.reload();
    } finally {
      setRotateBusy((p) => ({ ...p, [name]: false }));
    }
  }

  function toggleRotate(name: string) {
    setRotateMap((p) => {
      if (p[name] !== undefined) {
        const n = { ...p };
        delete n[name];
        return n;
      }
      return { ...p, [name]: '' };
    });
  }

  async function handleAddSecret() {
    if (!addName || !addValue) {
      setAddErr('Name and value are required.');
      return;
    }
    setAddBusy(true);
    setAddErr('');
    try {
      await helios.security.storeSecret({
        name: addName,
        value: addValue,
        category: addCategory,
        description: addDesc,
      });
      setAddName('');
      setAddValue('');
      setAddDesc('');
      setAddCategory('general');
      secrets.reload();
    } catch (e: any) {
      setAddErr(e?.message || String(e));
    } finally {
      setAddBusy(false);
    }
  }

  if (vault.loading) return <Loading />;

  if (!isUnlocked) {
    return (
      <Panel
        title={isUninitialized ? 'Initialize Vault' : 'Unlock Vault'}
        subtitle="AES-256 encrypted secret store"
      >
        <div className="max-w-sm flex flex-col gap-3">
          <p className="text-[12px] text-warmgray">
            {isUninitialized
              ? 'Set a master password to initialize the HELIOS vault. Store this password safely — it cannot be recovered.'
              : 'Enter your vault master password to unlock.'}
          </p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleVaultAction()}
            placeholder="Master password"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
          />
          {formErr && <p className="text-helred text-[11px]">{formErr}</p>}
          <Button
            variant="gold"
            size="sm"
            disabled={busy || !password}
            onClick={handleVaultAction}
          >
            {busy ? 'Working…' : isUninitialized ? 'Initialize Vault' : 'Unlock Vault'}
          </Button>
        </div>
      </Panel>
    );
  }

  return (
    <>
      <Panel
        title="Secrets"
        subtitle="stored credentials & keys"
        actions={
          <Button size="sm" variant="danger" disabled={busy} onClick={handleLock}>
            {busy ? 'Locking…' : 'Lock Vault'}
          </Button>
        }
      >
        {secrets.loading ? (
          <Loading />
        ) : !secretList.length ? (
          <EmptyState message="No secrets stored. Add one below." />
        ) : (
          <table className="w-full text-[12px] mb-2">
            <thead>
              <tr className="mono text-[10px] uppercase text-warmgray text-left">
                <th className="py-1 pr-3">Name</th>
                <th className="py-1 pr-3">Category</th>
                <th className="py-1 pr-3">Version</th>
                <th className="py-1 pr-3">Updated</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {secretList.map((s: any) => (
                <>
                  <tr key={s.name} className="border-t border-hairline">
                    <td className="py-1.5 pr-3 mono text-gold">{s.name}</td>
                    <td className="py-1.5 pr-3 text-warmgray">{s.category ?? '—'}</td>
                    <td className="py-1.5 pr-3 text-warmgray mono">{s.version ?? '—'}</td>
                    <td className="py-1.5 pr-3 text-warmgray mono text-[11px] whitespace-nowrap">
                      {fmtTs(s.last_updated ?? s.updated_at)}
                    </td>
                    <td className="py-1.5">
                      <div className="flex gap-1.5">
                        <Button size="sm" variant="ghost" onClick={() => toggleRotate(s.name)}>
                          Rotate
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => handleDelete(s.name)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                  {rotateMap[s.name] !== undefined && (
                    <tr key={`${s.name}-rotate`} className="bg-obsidian/40">
                      <td colSpan={5} className="py-2 px-1">
                        <div className="flex gap-2 items-center">
                          <input
                            type="password"
                            value={rotateMap[s.name]}
                            onChange={(e) =>
                              setRotateMap((p) => ({ ...p, [s.name]: e.target.value }))
                            }
                            placeholder="New value"
                            className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-1.5 text-[12px] outline-none focus:border-gold/40"
                          />
                          <Button
                            size="sm"
                            variant="gold"
                            disabled={rotateBusy[s.name] || !rotateMap[s.name]}
                            onClick={() => handleRotate(s.name)}
                          >
                            {rotateBusy[s.name] ? 'Saving…' : 'Save'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}

        <div className="border-t border-hairline pt-4 mt-2">
          <p className="mono text-[10px] uppercase text-warmgray mb-3">Add Secret</p>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              placeholder="Secret name"
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
            <input
              type="password"
              value={addValue}
              onChange={(e) => setAddValue(e.target.value)}
              placeholder="Value"
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
          </div>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <select
              value={addCategory}
              onChange={(e) => setAddCategory(e.target.value)}
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90"
            >
              <option value="general">general</option>
              <option value="api_key">api_key</option>
              <option value="password">password</option>
              <option value="certificate">certificate</option>
              <option value="token">token</option>
            </select>
            <input
              value={addDesc}
              onChange={(e) => setAddDesc(e.target.value)}
              placeholder="Description (optional)"
              className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40"
            />
          </div>
          {addErr && <p className="text-helred text-[11px] mb-2">{addErr}</p>}
          <Button
            size="sm"
            variant="gold"
            disabled={addBusy || !addName || !addValue}
            onClick={handleAddSecret}
          >
            {addBusy ? 'Storing…' : 'Store Secret'}
          </Button>
        </div>
      </Panel>

      <Panel title="Vault Audit Log" subtitle="access history" className="mt-3">
        {audit.loading ? (
          <Loading />
        ) : !auditLog.length ? (
          <EmptyState message="No audit entries." />
        ) : (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="mono text-[10px] uppercase text-warmgray text-left">
                <th className="py-1 pr-3">Time</th>
                <th className="py-1 pr-3">Action</th>
                <th className="py-1 pr-3">Secret</th>
                <th className="py-1">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {auditLog.map((e: any, i: number) => (
                <tr key={i} className="border-t border-hairline">
                  <td className="py-1.5 pr-3 mono text-[11px] text-warmgray whitespace-nowrap">
                    {fmtTs(e.ts ?? e.timestamp)}
                  </td>
                  <td className="py-1.5 pr-3 text-ivory/90">{e.action ?? e.event ?? '—'}</td>
                  <td className="py-1.5 pr-3 mono text-gold">{e.secret ?? e.name ?? '—'}</td>
                  <td className={cls('py-1.5 mono text-[11px]', outcomeColor(e.outcome))}>
                    {e.outcome ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}

// ---------------------------------------------------------------------------
// Events tab
// ---------------------------------------------------------------------------

function EventsTab() {
  const [eventType, setEventType] = useState('');
  const [actor, setActor] = useState('');
  const [verifyResults, setVerifyResults] = useState<Record<string, any>>({});
  const [verifyBusy, setVerifyBusy] = useState<Record<string, boolean>>({});

  const log = useAsync(
    () =>
      helios.security.complianceLog({
        limit: 200,
        event_type: eventType || undefined,
        actor: actor || undefined,
      }),
    [eventType, actor],
  );

  const entries: any[] = log.data?.entries ?? log.data ?? [];

  async function handleVerify(id: string) {
    setVerifyBusy((p) => ({ ...p, [id]: true }));
    try {
      const result = await helios.security.verifyEntry(id);
      setVerifyResults((p) => ({ ...p, [id]: result }));
    } catch (e: any) {
      setVerifyResults((p) => ({ ...p, [id]: { error: e?.message || String(e) } }));
    } finally {
      setVerifyBusy((p) => ({ ...p, [id]: false }));
    }
  }

  return (
    <Panel
      title="Compliance Events"
      subtitle="audit log · tamper-evident"
      actions={
        <Button size="sm" variant="ghost" onClick={log.reload}>
          Refresh
        </Button>
      }
    >
      <div className="flex gap-2 mb-4">
        <input
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          placeholder="Filter event type…"
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 flex-1"
        />
        <input
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          placeholder="Filter actor…"
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 flex-1"
        />
      </div>

      {log.loading ? (
        <Loading />
      ) : log.error ? (
        <EmptyState message={log.error} />
      ) : !entries.length ? (
        <EmptyState message="No events match the current filters." />
      ) : (
        <table className="w-full text-[12px]">
          <thead>
            <tr className="mono text-[10px] uppercase text-warmgray text-left">
              <th className="py-1 pr-3">Time</th>
              <th className="py-1 pr-3">Event</th>
              <th className="py-1 pr-3">Actor</th>
              <th className="py-1 pr-3">Action</th>
              <th className="py-1 pr-3">Resource</th>
              <th className="py-1 pr-3">Outcome</th>
              <th className="py-1" />
            </tr>
          </thead>
          <tbody>
            {entries.map((e: any, i: number) => {
              const id = e.id != null ? String(e.id) : String(i);
              const vr = verifyResults[id];
              return (
                <>
                  <tr key={id} className="border-t border-hairline">
                    <td className="py-1.5 pr-3 mono text-[11px] text-warmgray whitespace-nowrap">
                      {fmtTs(e.ts ?? e.timestamp)}
                    </td>
                    <td className="py-1.5 pr-3 text-ivory/90">{e.event_type ?? e.event ?? '—'}</td>
                    <td className="py-1.5 pr-3 text-warmgray">{e.actor ?? '—'}</td>
                    <td className="py-1.5 pr-3 text-warmgray">{e.action ?? '—'}</td>
                    <td className="py-1.5 pr-3 text-warmgray truncate max-w-[120px]">
                      {e.resource ?? '—'}
                    </td>
                    <td className={cls('py-1.5 pr-3 mono text-[11px]', outcomeColor(e.outcome))}>
                      {e.outcome ?? '—'}
                    </td>
                    <td className="py-1.5">
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={verifyBusy[id]}
                        onClick={() => handleVerify(id)}
                      >
                        {verifyBusy[id] ? '…' : 'Verify'}
                      </Button>
                    </td>
                  </tr>
                  {vr && (
                    <tr key={`${id}-vr`} className="bg-obsidian/40">
                      <td colSpan={7} className="px-3 py-1.5">
                        {vr.error ? (
                          <span className="text-helred text-[11px]">{vr.error}</span>
                        ) : (
                          <span
                            className={cls(
                              'mono text-[11px]',
                              vr.valid ? 'text-helgreen' : 'text-helred',
                            )}
                          >
                            {vr.valid ? 'Entry verified — hash intact.' : 'Entry tampered or invalid.'}
                            {vr.hash && (
                              <span className="text-warmgray ml-2">{vr.hash}</span>
                            )}
                          </span>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Compliance tab
// ---------------------------------------------------------------------------

function ComplianceTab() {
  const log = useAsync(() => helios.security.complianceLog({}), []);
  const entries: any[] = log.data?.entries ?? log.data ?? [];

  const [chainResult, setChainResult] = useState<any>(null);
  const [chainBusy, setChainBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);

  const total = entries.length;
  const loginEvents = entries.filter((e: any) =>
    /login|auth|session/i.test(e.event_type ?? e.event ?? ''),
  ).length;
  const vaultEvents = entries.filter((e: any) =>
    /vault|secret/i.test(e.event_type ?? e.event ?? ''),
  ).length;
  const acctEvents = entries.filter((e: any) =>
    /account|journal|invoice|ledger|transaction|acct/i.test(e.event_type ?? e.event ?? ''),
  ).length;

  async function handleVerifyChain() {
    setChainBusy(true);
    setChainResult(null);
    try {
      const r = await helios.security.verifyChain();
      setChainResult(r);
    } catch (e: any) {
      setChainResult({ error: e?.message || String(e) });
    } finally {
      setChainBusy(false);
    }
  }

  async function handleExport() {
    setExportBusy(true);
    try {
      const data = await helios.security.complianceLog({});
      const all: any[] = data?.entries ?? data ?? [];
      const blob = new Blob([JSON.stringify(all, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `compliance-log-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportBusy(false);
    }
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Total Events" accent value={log.loading ? '—' : total} sub="in log" />
        <MetricCard
          label="Login Events"
          value={log.loading ? '—' : loginEvents}
          sub="auth / session"
        />
        <MetricCard
          label="Vault Access"
          value={log.loading ? '—' : vaultEvents}
          sub="secret ops"
        />
        <MetricCard
          label="Acct Actions"
          value={log.loading ? '—' : acctEvents}
          sub="accounting"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Chain Integrity" subtitle="cryptographic tamper detection">
          <p className="text-[12px] text-warmgray mb-4 leading-relaxed">
            Verifies every entry in the compliance log is hash-chained. Any modification after
            recording will break the chain and be flagged.
          </p>
          <Button variant="gold" size="sm" disabled={chainBusy} onClick={handleVerifyChain}>
            {chainBusy ? 'Verifying…' : 'Verify Chain Integrity'}
          </Button>

          {chainResult && (
            <div className="mt-4 rounded-lg border border-hairline bg-obsidian/40 px-4 py-3">
              {chainResult.error ? (
                <p className="text-helred text-[12px]">{chainResult.error}</p>
              ) : (
                <div className="grid grid-cols-2 gap-y-2 text-[12px]">
                  <span className="text-warmgray">Total entries</span>
                  <span className="text-ivory/90 mono">{chainResult.total ?? '—'}</span>
                  <span className="text-warmgray">Valid</span>
                  <span className="text-helgreen mono">{chainResult.valid ?? '—'}</span>
                  <span className="text-warmgray">Invalid</span>
                  <span
                    className={cls(
                      'mono',
                      (chainResult.invalid ?? 0) > 0 ? 'text-helred' : 'text-warmgray',
                    )}
                  >
                    {chainResult.invalid ?? 0}
                  </span>
                  <span className="text-warmgray">Tampered</span>
                  <span
                    className={cls(
                      'mono',
                      (chainResult.tampered ?? 0) > 0 ? 'text-helred' : 'text-warmgray',
                    )}
                  >
                    {chainResult.tampered ?? 0}
                  </span>
                  {chainResult.integrity !== undefined && (
                    <>
                      <span className="text-warmgray">Integrity</span>
                      <span
                        className={cls(
                          'mono',
                          chainResult.integrity ? 'text-helgreen' : 'text-helred',
                        )}
                      >
                        {chainResult.integrity ? 'INTACT' : 'COMPROMISED'}
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </Panel>

        <Panel title="Export" subtitle="download compliance log as JSON">
          <p className="text-[12px] text-warmgray mb-4 leading-relaxed">
            Download the full compliance event log as a JSON file for external audit, archiving,
            or regulatory submission.
          </p>
          <Button
            variant="primary"
            size="sm"
            disabled={exportBusy || log.loading}
            onClick={handleExport}
          >
            {exportBusy ? 'Preparing…' : 'Export Compliance Log'}
          </Button>
          {log.loading && (
            <p className="text-[11px] text-warmgray mt-2">Loading log data…</p>
          )}
        </Panel>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function CheckDot({ status }: { status?: string }) {
  const s = (status ?? '').toLowerCase();
  const color =
    s === 'ok' || s === 'pass' || s === 'good'
      ? 'bg-helgreen'
      : s === 'warn' || s === 'warning'
      ? 'bg-gold'
      : s === 'error' || s === 'fail' || s === 'critical'
      ? 'bg-helred'
      : 'bg-warmgray';
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cls('w-2 h-2 rounded-full shrink-0', color)} />
      <span className="mono text-[10px] text-warmgray uppercase">{status ?? '—'}</span>
    </span>
  );
}

function outcomeColor(outcome?: string): string {
  const o = (outcome ?? '').toLowerCase();
  if (o === 'ok' || o === 'success' || o === 'pass') return 'text-helgreen';
  if (o === 'error' || o === 'fail' || o === 'failure') return 'text-helred';
  if (o === 'warn' || o === 'warning') return 'text-gold';
  return 'text-warmgray';
}

function fmtTs(ts?: string | number | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return String(ts);
  }
}
