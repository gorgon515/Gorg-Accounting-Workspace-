import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function DesktopCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Desktop Center." />;
  const sysInfo = useAsync(() => helios.desktop.systemInfo(), [], 5000);
  const resources = useAsync(() => helios.desktop.resources(), [], 5000);
  const approvals = useAsync(() => helios.desktop.approvals(), [], 5000);
  const automations = useAsync(() => helios.desktop.automations(), [], 10000);

  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [newAuto, setNewAuto] = useState({ name: '', trigger: 'manual', steps: '' });
  const [directory, setDirectory] = useState<any>(null);
  const [dirPath, setDirPath] = useState('');
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const sys = sysInfo.data ?? {};
  const res = resources.data ?? {};
  const pendingApprovals: any[] = Array.isArray(approvals.data) ? approvals.data : [];

  function pct(v: number) {
    return Math.round(v || 0);
  }

  function barColor(v: number) {
    if (v > 85) return 'bg-helred';
    if (v > 65) return 'bg-gold';
    return 'bg-helgreen';
  }

  async function resolveApproval(id: string, action: 'approve' | 'reject') {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      if (action === 'approve') await helios.desktop.approve(id, {});
      else await helios.desktop.reject(id, {});
      approvals.reload();
    } finally { setBusy((b) => ({ ...b, [id]: false })); }
  }

  async function createAutomation() {
    if (!newAuto.name.trim()) return;
    const steps = newAuto.steps.split('\n').filter(Boolean).map((s) => ({ action: s.trim() }));
    await helios.desktop.createAutomation({ name: newAuto.name, trigger: newAuto.trigger, steps });
    setNewAuto({ name: '', trigger: 'manual', steps: '' });
    automations.reload();
  }

  async function browseDir() {
    const data = await helios.desktop.listDirectory(dirPath);
    setDirectory(data);
  }

  async function searchFiles() {
    if (!searchQ.trim()) return;
    const results = await helios.desktop.searchFiles({ q: searchQ });
    setSearchResults(Array.isArray(results) ? results : []);
  }

  return (
    <Page title="Desktop Center" subtitle="system monitor · automation · files · approval gates"
      actions={<Button size="sm" onClick={() => { sysInfo.reload(); resources.reload(); approvals.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="CPU" value={`${pct((res as any).cpu_percent)}%`} accent />
          <MetricCard label="Memory" value={`${pct((res as any).memory_percent)}%`} />
          <MetricCard label="Disk" value={`${pct((res as any).disk_percent)}%`} />
          <MetricCard label="Pending Approvals" value={pendingApprovals.length} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <Panel title="System Resources">
            {sysInfo.loading ? <Loading /> : (
              <div className="flex flex-col gap-3">
                <div className="mono text-[10px] text-warmgray">{(sys as any).platform} · {((sys as any).platform_version || '').slice(0, 40)}</div>
                {[
                  { label: 'CPU', value: pct((res as any).cpu_percent) },
                  { label: 'Memory', value: pct((res as any).memory_percent) },
                  { label: 'Disk', value: pct((res as any).disk_percent) },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div className="flex justify-between mono text-[10px] text-warmgray mb-1">
                      <span>{label}</span><span>{value}%</span>
                    </div>
                    <div className="h-1.5 bg-obsidian rounded-full overflow-hidden">
                      <div className={cls('h-full rounded-full transition-all', barColor(value))}
                        style={{ width: `${value}%` }} />
                    </div>
                  </div>
                ))}
                {(sys as any).memory_total_gb && (
                  <div className="mono text-[10px] text-warmgray">
                    RAM: {(sys as any).memory_used_gb}GB / {(sys as any).memory_total_gb}GB ·
                    Disk free: {(sys as any).disk_free_gb}GB
                  </div>
                )}
              </div>
            )}
          </Panel>

          <Panel title="Pending Approvals">
            {approvals.loading ? <Loading /> : pendingApprovals.length === 0 ? (
              <EmptyState message="No pending desktop approvals." />
            ) : (
              <div className="flex flex-col gap-2">
                {pendingApprovals.map((a: any) => (
                  <div key={a.id} className="rounded border border-gold/30 bg-gold/5 px-2.5 py-2">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="mono text-[10px] text-gold uppercase">{a.action_type}</span>
                      <div className="flex gap-1">
                        <Button size="sm" variant="gold"
                          onClick={() => resolveApproval(a.id, 'approve')}
                          disabled={busy[a.id]}>✓</Button>
                        <Button size="sm" variant="ghost"
                          onClick={() => resolveApproval(a.id, 'reject')}
                          disabled={busy[a.id]}>✕</Button>
                      </div>
                    </div>
                    <div className="text-[11px] text-warmgray truncate">
                      {JSON.stringify(a.payload).slice(0, 80)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Automations">
            {automations.loading ? <Loading /> : (
              <div className="flex flex-col gap-2">
                {(automations.data as any[] ?? []).length === 0 ? (
                  <EmptyState message="No automations yet." />
                ) : (
                  <div className="flex flex-col gap-1.5 mb-2">
                    {(automations.data as any[]).map((a: any) => (
                      <div key={a.id} className="flex items-center justify-between text-[12px]">
                        <div>
                          <div>{a.name}</div>
                          <div className="mono text-[10px] text-warmgray">{a.trigger} · {a.steps?.length ?? 0} steps</div>
                        </div>
                        <Button size="sm" variant="ghost"
                          onClick={async () => {
                            await helios.desktop.runAutomation(a.id, {});
                            approvals.reload();
                          }}>Run</Button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="border-t border-hairline pt-2">
                  <div className="mono text-[9px] text-warmgray uppercase mb-1.5">New Automation</div>
                  <div className="flex flex-col gap-1.5">
                    <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      placeholder="Name" value={newAuto.name}
                      onChange={(e) => setNewAuto({ ...newAuto, name: e.target.value })} />
                    <textarea className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs resize-none"
                      rows={2} placeholder="Steps (one per line)"
                      value={newAuto.steps}
                      onChange={(e) => setNewAuto({ ...newAuto, steps: e.target.value })} />
                    <Button size="sm" variant="gold" onClick={createAutomation}
                      disabled={!newAuto.name.trim()}>Create</Button>
                  </div>
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="File Browser">
            <div className="flex flex-col gap-2">
              <div className="flex gap-1.5">
                <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                  placeholder="Path (empty = home)" value={dirPath}
                  onChange={(e) => setDirPath(e.target.value)} />
                <Button size="sm" variant="ghost" onClick={browseDir}>Browse</Button>
              </div>
              {directory && (
                <div className="max-h-48 overflow-y-auto scroll-thin">
                  <div className="mono text-[10px] text-warmgray mb-1">{directory.path}</div>
                  {(directory.entries ?? []).map((e: any) => (
                    <div key={e.name} className="flex items-center gap-2 py-0.5 text-[11px]">
                      <span>{e.type === 'directory' ? '📁' : '📄'}</span>
                      <span className="truncate text-ivory/80">{e.name}</span>
                      {e.size != null && (
                        <span className="mono text-[10px] text-warmgray ml-auto">
                          {e.size > 1048576 ? `${(e.size / 1048576).toFixed(1)}MB` : `${Math.round(e.size / 1024)}KB`}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Panel>

          <Panel title="File Search">
            <div className="flex flex-col gap-2">
              <div className="flex gap-1.5">
                <input className="flex-1 bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                  placeholder="Search query…" value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') searchFiles(); }} />
                <Button size="sm" variant="ghost" onClick={searchFiles}>Search</Button>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-48 overflow-y-auto scroll-thin flex flex-col gap-1">
                  {searchResults.map((r: any, i) => (
                    <div key={i} className="flex items-center gap-2 text-[11px]">
                      <span>{r.type === 'directory' ? '📁' : '📄'}</span>
                      <span className="truncate text-ivory/80">{r.name}</span>
                      <span className="mono text-[10px] text-warmgray ml-auto truncate max-w-[120px]">{r.path}</span>
                    </div>
                  ))}
                </div>
              )}
              {searchResults.length === 0 && searchQ && (
                <EmptyState message="No files found." />
              )}
            </div>
          </Panel>
        </div>
      </div>
    </Page>
  );
}
