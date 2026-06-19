import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';

export function Automations() {
  const status = useAsync(() => helios.sidecar.n8nStatus(), []);
  const workflows = useAsync(() => helios.sidecar.n8nWorkflows(), []);
  const [gen, setGen] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const connected = status.data?.connected;

  async function generate() {
    setBusy(true);
    try {
      setGen(await helios.sidecar.n8nGenerate({ kind: 'accounting_briefing', email_to: 'you@example.com' }));
    } catch { setGen(null); } finally { setBusy(false); }
  }

  const wfList = workflows.data?.workflows ?? [];

  return (
    <Page title="Automation Center" subtitle="N8N workflows · AI generation"
      actions={<StatusBadge status={connected ? 'online' : 'idle'} label={connected ? 'N8N connected' : 'N8N not connected'} />}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="N8N" value={connected ? 'Connected' : 'Offline'} sub={status.data?.url} />
        <MetricCard label="Workflows" value={connected ? wfList.length : '—'} />
        <MetricCard label="Generator" accent value="Ready" sub="AI → N8N JSON" />
        <MetricCard label="Example" value="Briefing" sub="daily accounting" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Workflows" subtitle="live from N8N">
          {workflows.loading ? <Loading />
            : !connected ? (
              <EmptyState message="Set N8N_URL + N8N_API_KEY in the desktop app to list and run workflows. Generation below works without N8N." />
            ) : !wfList.length ? <EmptyState message="No workflows yet." /> : (
              <ul className="flex flex-col gap-1.5">
                {wfList.map((w: any) => (
                  <li key={w.id} className="flex items-center justify-between rounded-lg border border-hairline bg-obsidian/40 px-3 py-2 text-[12px]">
                    <span>{w.name}</span>
                    <StatusBadge status={w.active ? 'online' : 'idle'} label={w.active ? 'active' : 'inactive'} />
                  </li>
                ))}
              </ul>
            )}
        </Panel>

        <Panel title="AI workflow generator" subtitle="produces importable N8N JSON"
          actions={<Button variant="gold" onClick={generate} disabled={busy}>{busy ? 'Generating…' : 'Generate briefing workflow'}</Button>}>
          {!gen ? (
            <p className="text-[12px] text-warmgray leading-relaxed">
              Generate a real N8N workflow from a request — e.g. the daily accounting briefing:
              Schedule → fetch HELIOS briefing → format → email. The JSON imports directly into N8N.
            </p>
          ) : (
            <div className="text-[12px]">
              <div className="text-ivory mb-2">{gen.name}</div>
              <div className="mono text-[11px] text-warmgray mb-2">{gen.nodes?.length} nodes · {Object.keys(gen.connections || {}).length} connections</div>
              <ol className="flex flex-col gap-1">
                {(gen.nodes ?? []).map((n: any, i: number) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="mono text-[10px] text-gold w-5">{i + 1}</span>
                    <span>{n.name}</span>
                    <span className="mono text-[10px] text-warmgray">{n.type?.split('.').pop()}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}
