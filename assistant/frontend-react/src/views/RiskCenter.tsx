import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const SEV_COLOR: Record<string, string> = {
  critical: 'text-helred', high: 'text-helred', medium: 'text-gold', low: 'text-warmgray',
};

export function RiskCenter() {
  const [severity, setSeverity] = useState('');
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for risk monitoring." />;

  const risks = useAsync(() => helios.intelligence.listRisks({ status: 'open', severity: severity || undefined }), [severity]);
  const summary = useAsync(() => helios.intelligence.riskSummary(), []);
  const list: any[] = risks.data?.risks ?? [];

  async function scan() {
    await helios.intelligence.scanRisks();
    risks.reload();
    summary.reload();
  }

  async function mitigate(id: string) {
    await helios.intelligence.setRiskStatus(id, 'mitigating');
    risks.reload();
    summary.reload();
  }

  const bySev = summary.data?.by_severity ?? {};

  return (
    <Page
      title="Risk Center"
      subtitle="continuous risk detection · mitigation"
      actions={<Button size="sm" variant="gold" onClick={scan}>Re-scan</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Open Risks" value={summary.data?.open_risks ?? list.length} accent />
          <MetricCard label="Critical" value={bySev.critical ?? 0} />
          <MetricCard label="High" value={bySev.high ?? 0} />
          <MetricCard label="Max Score" value={summary.data?.max_score ?? 0} />
        </div>
        <Panel
          title="Risks"
          actions={
            <select className="border border-hairline bg-obsidian rounded px-2 py-1 text-xs"
              value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">all severities</option>
              {['critical', 'high', 'medium', 'low'].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          }
        >
          {risks.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No open risks. Run a scan to detect them." />
          ) : (
            <div className="grid gap-2">
              {list.map((r) => (
                <div key={r.id} className="rounded-lg border border-hairline px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{r.title}</span>
                    <div className="flex items-center gap-3">
                      <span className={cls('mono text-[10px] uppercase', SEV_COLOR[r.severity] ?? 'text-warmgray')}>
                        {r.severity} · {Math.round(r.score)}
                      </span>
                      <Button size="sm" onClick={() => mitigate(r.id)}>Mitigate</Button>
                    </div>
                  </div>
                  <p className="text-[12px] text-warmgray mt-1">{r.description}</p>
                  <div className="flex gap-4 mt-1 mono text-[10px] text-warmgray">
                    <span>probability {Math.round((r.probability ?? 0) * 100)}%</span>
                    <span>impact {Math.round((r.impact ?? 0) * 100)}%</span>
                  </div>
                  {(r.mitigation ?? []).length > 0 && (
                    <ul className="mt-2 flex flex-wrap gap-1">
                      {r.mitigation.map((m: string, i: number) => (
                        <li key={i} className="mono text-[10px] px-1.5 py-0.5 rounded border border-hairline text-helgreen">
                          {m}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}
