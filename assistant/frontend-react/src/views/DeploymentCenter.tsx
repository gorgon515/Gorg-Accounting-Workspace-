import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, timeAgo } from '../lib/format';

const TABS = ['Updates', 'Installer', 'Build Info'] as const;
type Tab = typeof TABS[number];

export function DeploymentCenter() {
  const [tab, setTab] = useState<Tab>('Updates');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to manage deployment." />;
  return (
    <Page
      title="Deployment Center"
      subtitle="updates · installer · build"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Updates' && <UpdatesTab />}
      {tab === 'Installer' && <InstallerTab />}
      {tab === 'Build Info' && <BuildInfoTab />}
    </Page>
  );
}

function UpdatesTab() {
  const settings = useAsync(() => helios.updates.getSettings(), []);
  const channels = useAsync(() => helios.updates.listChannels(), []);
  const history = useAsync(() => helios.updates.history(), []);
  const [check, setCheck] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const s = settings.data ?? {};
  const chanList: any[] = channels.data?.channels ?? [];
  const hist: any[] = history.data?.history ?? [];

  async function doCheck() {
    setBusy(true);
    try {
      setCheck(await helios.updates.checkForUpdates(s.channel || 'stable'));
    } finally {
      setBusy(false);
    }
  }

  async function setChannel(ch: string) {
    await helios.updates.updateSettings({ channel: ch });
    settings.reload();
    setCheck(null);
  }

  async function download() {
    if (!check?.latest_version) return;
    await helios.updates.download({ version: check.latest_version, channel: s.channel });
    history.reload();
  }

  if (settings.loading) return <Loading />;

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Current Version" value={s.current_version ?? '—'} accent />
        <MetricCard label="Channel" value={<span className="capitalize">{s.channel}</span>} />
        <MetricCard label="Last Check" value={s.last_check ? timeAgo(s.last_check) : 'never'} />
      </div>
      <Panel title="Update Channel">
        <div className="flex flex-wrap gap-2">
          {chanList.map((c) => (
            <button key={c.name}
              onClick={() => setChannel(c.name)}
              className={cls('rounded-lg border px-3 py-2 text-left',
                c.name === s.channel ? 'border-gold/50 bg-gold/10' : 'border-hairline hover:bg-ivory/5')}>
              <div className="text-sm capitalize">{c.name}</div>
              <div className="mono text-[10px] text-warmgray">{c.description}</div>
            </button>
          ))}
        </div>
        <div className="mt-3">
          <Button variant="gold" size="sm" onClick={doCheck} disabled={busy}>
            {busy ? 'Checking…' : 'Check for Updates'}
          </Button>
        </div>
        {check && (
          <div className="mt-3 rounded-lg border border-hairline px-3 py-2">
            {check.update_available ? (
              <>
                <div className="text-sm text-gold">Update available: {check.latest_version}</div>
                <p className="text-[12px] text-warmgray mt-1">{check.release_notes}</p>
                <div className="mt-2"><Button size="sm" variant="primary" onClick={download}>Download Update</Button></div>
              </>
            ) : (
              <div className="text-sm text-helgreen">You are on the latest version ({check.current_version}).</div>
            )}
          </div>
        )}
      </Panel>
      <Panel title="Update History">
        {hist.length === 0 ? (
          <EmptyState message="No update history." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Version</th><th>Action</th><th>Status</th><th>When</th>
              </tr>
            </thead>
            <tbody>
              {hist.map((h) => (
                <tr key={h.id} className="border-t border-hairline">
                  <td className="py-1.5 mono text-[11px]">{h.version}</td>
                  <td>{h.action}</td>
                  <td className="text-helgreen">{h.status}</td>
                  <td className="text-warmgray text-[11px]">{timeAgo(h.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function InstallerTab() {
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [setupMsg, setSetupMsg] = useState('');

  async function validate() {
    setBusy(true);
    try {
      setResult(await helios.updates.validateInstall());
    } finally {
      setBusy(false);
    }
  }

  const checks = result?.checks ?? {};
  const checkRows: Array<[string, string]> = [
    ['Python Version', 'python_version'],
    ['Dependencies', 'dependencies'],
    ['Disk Space', 'disk_space'],
    ['Ports', 'ports'],
    ['Database Access', 'database_access'],
  ];

  return (
    <div className="grid gap-3">
      <Panel title="Installation Validation"
        actions={<Button size="sm" variant="gold" onClick={validate} disabled={busy}>{busy ? 'Running…' : 'Run Checks'}</Button>}>
        {!result ? (
          <EmptyState message="Run validation to check the install environment." />
        ) : (
          <div className="grid gap-1">
            {checkRows.map(([label, key]) => {
              const ok = checks[key]?.ok;
              return (
                <div key={key} className="flex items-center justify-between rounded-lg border border-hairline px-3 py-1.5">
                  <span className="text-sm">{label}</span>
                  <span className={cls('mono text-[12px]', ok ? 'text-helgreen' : 'text-helred')}>{ok ? '✓ pass' : '✗ fail'}</span>
                </div>
              );
            })}
            <div className={cls('mono text-[12px] mt-2', result.passed ? 'text-helgreen' : 'text-helred')}>
              {result.passed ? 'All checks passed.' : 'Some checks failed.'}
            </div>
          </div>
        )}
      </Panel>
      <Panel title="Setup Tasks">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={async () => { const r = await helios.updates.setupDataDir(); setSetupMsg(`Data dir: ${r.data_dir ?? 'ok'}`); }}>Initialize Data Directory</Button>
        </div>
        {setupMsg && <div className="mono text-[11px] text-gold mt-2">{setupMsg}</div>}
      </Panel>
    </div>
  );
}

function detectPlatform(): string {
  const ua = navigator.userAgent;
  if (/Windows/i.test(ua)) return 'Windows';
  if (/Mac/i.test(ua)) return 'macOS';
  if (/Linux/i.test(ua)) return 'Linux';
  return 'Unknown';
}

function BuildInfoTab() {
  const config = useAsync(() => helios.config(), []);
  const version = (config.data as any)?.version ?? '0.8.0';
  const rows: Array<[string, string]> = [
    ['HELIOS Version', version],
    ['Backend', 'Python FastAPI · 127.0.0.1:8420'],
    ['Frontend', 'Electron 33 · React 18 · Vite'],
    ['Build Date', new Date().toISOString().slice(0, 10)],
    ['Platform', detectPlatform()],
    ['Windows Target', 'NSIS installer (x64)'],
    ['macOS Target', 'DMG + ZIP (arm64, x64)'],
    ['Linux Target', 'AppImage + DEB (x64)'],
    ['CI Pipeline', 'GitHub Actions · build-installers.yml'],
  ];
  return (
    <Panel title="Build Information">
      <div className="grid gap-1">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between border-b border-hairline py-1.5">
            <span className="mono text-[11px] uppercase text-warmgray">{k}</span>
            <span className="text-sm">{v}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
