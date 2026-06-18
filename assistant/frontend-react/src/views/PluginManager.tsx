import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls, timeAgo } from '../lib/format';

const TABS = ['Installed', 'Browse', 'Audit'] as const;
type Tab = typeof TABS[number];

const REGISTRY = [
  {
    name: 'example-tool', version: '1.0.0', author: 'HELIOS Platform Team',
    description: 'Demonstrates the plugin SDK with a read-only accounting summary tool.',
    permissions: ['accounting:read', 'memory:read'], entry_point: 'main.py',
  },
  {
    name: 'csv-importer', version: '1.2.0', author: 'Community',
    description: 'Import CSV transaction files directly into the accounting ledger.',
    permissions: ['accounting:read', 'accounting:write', 'filesystem:read'], entry_point: 'main.py',
  },
  {
    name: 'pdf-extractor', version: '0.9.1', author: 'Community',
    description: 'Extract structured data from PDF invoices and receipts.',
    permissions: ['filesystem:read', 'reports:read'], entry_point: 'main.py',
  },
];

export function PluginManager() {
  const [tab, setTab] = useState<Tab>('Installed');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app to manage plugins." />;
  return (
    <Page
      title="Plugin Manager"
      subtitle="extend HELIOS · sandboxed · permission-gated"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }
    >
      {tab === 'Installed' && <InstalledTab />}
      {tab === 'Browse' && <BrowseTab />}
      {tab === 'Audit' && <AuditTab />}
    </Page>
  );
}

function statusVariant(status: string) {
  return status === 'enabled' ? 'text-helgreen' : status === 'disabled' ? 'text-warmgray' : 'text-gold';
}

function InstalledTab() {
  const [filter, setFilter] = useState('');
  const plugins = useAsync(() => helios.plugins.list(filter || undefined), [filter]);
  const list: any[] = plugins.data?.plugins ?? [];

  async function act(id: string, action: 'enable' | 'disable' | 'uninstall') {
    await helios.plugins[action](id);
    plugins.reload();
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Installed" value={list.length} />
        <MetricCard label="Enabled" value={list.filter((p) => p.status === 'enabled').length} accent />
        <MetricCard label="Disabled" value={list.filter((p) => p.status === 'disabled').length} />
      </div>
      <Panel
        title="Installed Plugins"
        actions={
          <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
            value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">all</option>
            <option value="enabled">enabled</option>
            <option value="disabled">disabled</option>
            <option value="installed">installed</option>
          </select>
        }
      >
        {plugins.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No plugins installed. Browse the registry to add one." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left mono text-[10px] uppercase text-warmgray">
                <th className="py-1">Name</th><th>Version</th><th>Author</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id} className="border-t border-hairline">
                  <td className="py-1.5">{p.name}</td>
                  <td className="mono text-[11px]">{p.version}</td>
                  <td className="text-warmgray">{p.author}</td>
                  <td className={cls('mono text-[11px] uppercase', statusVariant(p.status))}>{p.status}</td>
                  <td className="text-right flex justify-end gap-1 py-1.5">
                    {p.status === 'enabled'
                      ? <Button size="sm" onClick={() => act(p.id, 'disable')}>Disable</Button>
                      : <Button size="sm" variant="primary" onClick={() => act(p.id, 'enable')}>Enable</Button>}
                    <Button size="sm" variant="danger" onClick={() => act(p.id, 'uninstall')}>Uninstall</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function BrowseTab() {
  const [installing, setInstalling] = useState('');
  const [msg, setMsg] = useState('');

  async function install(p: typeof REGISTRY[number]) {
    setInstalling(p.name);
    setMsg('');
    try {
      const res = await helios.plugins.install({
        name: p.name, version: p.version, description: p.description,
        author: p.author, entry_point: p.entry_point, permissions: p.permissions,
      });
      setMsg(res?.error ? `Error: ${res.error}` : `Installed ${p.name}.`);
    } finally {
      setInstalling('');
    }
  }

  return (
    <div className="grid gap-3">
      {msg && <div className="mono text-[11px] text-gold">{msg}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {REGISTRY.map((p) => (
          <Panel key={p.name} title={p.name} subtitle={`v${p.version} · ${p.author}`}>
            <p className="text-[12px] text-warmgray">{p.description}</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {p.permissions.map((perm) => (
                <span key={perm} className="mono text-[10px] px-1.5 py-0.5 rounded border border-hairline text-warmgray">
                  {perm}
                </span>
              ))}
            </div>
            <div className="mt-3">
              <Button variant="gold" size="sm" disabled={installing === p.name} onClick={() => install(p)}>
                {installing === p.name ? 'Installing…' : 'Install'}
              </Button>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}

function AuditTab() {
  const audit = useAsync(() => helios.plugins.sandboxAudit(), []);
  if (audit.loading) return <Loading />;
  const list: any[] = audit.data?.audit ?? [];
  return (
    <Panel title="Sandbox Execution Audit">
      {list.length === 0 ? (
        <EmptyState message="No plugin executions recorded yet." />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left mono text-[10px] uppercase text-warmgray">
              <th className="py-1">Plugin</th><th>Function</th><th>Allowed</th><th>When</th>
            </tr>
          </thead>
          <tbody>
            {list.map((a) => (
              <tr key={a.id} className="border-t border-hairline">
                <td className="py-1.5">{a.plugin_id}</td>
                <td className="mono text-[11px]">{a.function_name}</td>
                <td className={cls('mono text-[11px]', a.allowed ? 'text-helgreen' : 'text-helred')}>
                  {a.allowed ? 'yes' : 'no'}
                </td>
                <td className="text-warmgray text-[11px]">{timeAgo(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
