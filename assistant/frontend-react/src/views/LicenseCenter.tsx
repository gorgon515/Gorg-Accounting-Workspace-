import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, fmtMoney, timeAgo } from '../lib/format';

const TABS = ['Active License', 'Editions', 'History'] as const;
type Tab = typeof TABS[number];

export function LicenseCenter() {
  const [tab, setTab] = useState<Tab>('Active License');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to manage licensing." />;
  return (
    <Page
      title="License Center"
      subtitle="edition · seats · activation"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Active License' && <ActiveTab />}
      {tab === 'Editions' && <EditionsTab />}
      {tab === 'History' && <HistoryTab />}
    </Page>
  );
}

function ActiveTab() {
  const active = useAsync(() => helios.licensing.getActive(), []);
  const [key, setKey] = useState('');
  const [machine, setMachine] = useState('');
  const [msg, setMsg] = useState('');

  const lic = active.data && !active.data.active && active.data.edition ? active.data : null;

  async function activate() {
    if (!key) return;
    const res = await helios.licensing.activate({ license_key: key.trim(), machine_id: machine });
    setMsg(res?.success ? 'License activated.' : `Error: ${res?.error ?? 'invalid license'}`);
    setKey('');
    active.reload();
  }

  if (active.loading) return <Loading />;

  return (
    <div className="grid gap-3">
      {lic ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="Edition" value={<span className="capitalize">{lic.edition}</span>} accent />
            <MetricCard label="Seats" value={lic.seats} />
            <MetricCard label="Status" value={lic.valid ? 'Valid' : 'Expired'} />
            <MetricCard label="Expires" value={timeAgo(lic.expires_at)} />
          </div>
          <Panel title="License Details">
            <div className="mono text-[11px] text-warmgray grid gap-1">
              <div>License ID: {lic.license_id}</div>
              <div>Organization: {lic.org_name}</div>
              <div>Issued: {lic.issued_at}</div>
              <div>Expires: {lic.expires_at}</div>
            </div>
            <div className="flex flex-wrap gap-1 mt-3">
              {(lic.features || []).map((f: string) => (
                <span key={f} className="mono text-[10px] px-1.5 py-0.5 rounded border border-hairline text-helgreen">✓ {f}</span>
              ))}
            </div>
            <div className="mt-3">
              <Button variant="danger" size="sm"
                onClick={async () => { await helios.licensing.revoke(lic.license_id); active.reload(); }}>
                Revoke License
              </Button>
            </div>
          </Panel>
        </>
      ) : (
        <Panel title="No Active License">
          <p className="text-[12px] text-warmgray mb-3">Activate a license key to unlock edition features.</p>
          <div className="flex flex-wrap items-end gap-2">
            <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm flex-1 min-w-[260px]"
              placeholder="paste license key" value={key} onChange={(e) => setKey(e.target.value)} />
            <input className="border border-hairline bg-transparent rounded px-2 py-1 text-sm"
              placeholder="machine id (optional)" value={machine} onChange={(e) => setMachine(e.target.value)} />
            <Button variant="gold" size="sm" onClick={activate} disabled={!key}>Activate</Button>
          </div>
          {msg && <div className="mono text-[11px] text-gold mt-2">{msg}</div>}
        </Panel>
      )}
    </div>
  );
}

function EditionsTab() {
  const editions = useAsync(() => helios.licensing.listEditions(), []);
  const active = useAsync(() => helios.licensing.getActive(), []);
  if (editions.loading) return <Loading />;
  const list: any[] = editions.data?.editions ?? [];
  const currentEdition = active.data?.edition;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {list.map((e) => (
        <Panel key={e.name}
          title={<span className="capitalize">{e.name}</span>}
          subtitle={`${fmtMoney(e.price_monthly_usd)}/mo · ${e.max_seats} seats`}
          className={cls(e.name === currentEdition && 'ring-1 ring-gold/40')}
        >
          <div className="flex flex-col gap-1">
            {e.features.map((f: string) => (
              <span key={f} className="mono text-[11px] text-warmgray">✓ {f}</span>
            ))}
          </div>
          {e.name === currentEdition && <div className="mono text-[10px] text-gold mt-2 uppercase">Current</div>}
        </Panel>
      ))}
    </div>
  );
}

function HistoryTab() {
  const acts = useAsync(() => helios.licensing.listActivations(), []);
  if (acts.loading) return <Loading />;
  const list: any[] = acts.data?.activations ?? [];
  return (
    <Panel title="Activation History">
      {list.length === 0 ? (
        <EmptyState message="No activations recorded." />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left mono text-[10px] uppercase text-warmgray">
              <th className="py-1">License ID</th><th>Edition</th><th>Machine</th><th>Activated</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map((a) => (
              <tr key={a.id} className="border-t border-hairline">
                <td className="py-1.5 mono text-[11px]">{a.license_id}</td>
                <td className="capitalize">{a.edition}</td>
                <td className="mono text-[11px] text-warmgray">{a.machine_id || '—'}</td>
                <td className="text-warmgray text-[11px]">{timeAgo(a.activated_at)}</td>
                <td className={cls('mono text-[11px]', a.status === 'active' ? 'text-helgreen' : 'text-helred')}>{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
