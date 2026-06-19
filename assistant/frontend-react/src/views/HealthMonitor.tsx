import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const TABS = ['Live Status', 'Reports', 'History'] as const;
type Tab = typeof TABS[number];

// Map health overall status → StatusBadge status type
function overallToBadge(s: string): 'ready' | 'idle' | 'error' {
  if (s === 'healthy') return 'ready';
  if (s === 'critical') return 'error';
  return 'idle'; // degraded
}

// Dot color for subsystem status
function subsystemDotClass(s: string): string {
  if (!s) return 'bg-warmgray';
  const lower = s.toLowerCase();
  if (lower === 'healthy' || lower === 'ok' || lower === 'up') return 'bg-green-400';
  if (lower === 'degraded' || lower === 'warn' || lower === 'warning') return 'bg-yellow-400';
  return 'bg-helred'; // critical, error, down
}

// Dot color for check status
function checkDotClass(s: string): string {
  if (!s) return 'bg-warmgray';
  const lower = s.toLowerCase();
  if (lower === 'pass' || lower === 'ok' || lower === 'healthy') return 'bg-green-400';
  if (lower === 'warn' || lower === 'warning') return 'bg-yellow-400';
  return 'bg-helred';
}

const SUBSYSTEM_KEYS = [
  'database', 'vault', 'backup', 'sync', 'memory', 'documents', 'accounting',
] as const;

const SUBSYSTEM_LABELS: Record<string, string> = {
  database: 'Database',
  vault: 'Vault',
  backup: 'Backup',
  sync: 'Sync',
  memory: 'Memory',
  documents: 'Documents',
  accounting: 'Accounting',
};

function subsystemKeyMetric(sub: any): string {
  if (!sub) return '—';
  if (sub.message) return sub.message;
  if (sub.size_mb != null) return `${sub.size_mb} MB`;
  if (sub.used_mb != null && sub.total_mb != null) return `${sub.used_mb}/${sub.total_mb} MB`;
  if (sub.used_percent != null) return `${sub.used_percent}% used`;
  if (sub.count != null) return `${sub.count} items`;
  if (sub.latency_ms != null) return `${sub.latency_ms} ms`;
  if (sub.entries != null) return `${sub.entries} entries`;
  if (sub.pending != null) return `${sub.pending} pending`;
  return sub.status ?? '—';
}

export function HealthMonitor() {
  if (!helios.hasBridge()) {
    return <EmptyState message="Open in desktop app to use Health Monitor." />;
  }

  const [tab, setTab] = useState<Tab>('Live Status');

  return (
    <Page
      title="Health Monitor"
      subtitle="live status · reports · history"
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
      {tab === 'Live Status' && <LiveStatus />}
      {tab === 'Reports' && <Reports />}
      {tab === 'History' && <History />}
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Live Status
// ---------------------------------------------------------------------------

function LiveStatus() {
  const status = useAsync(() => helios.healthMonitor.status(), [], 30000);

  const overall = status.data?.overall ?? 'unknown';
  const checks: any[] = status.data?.checks ?? [];
  const subsystems: Record<string, any> = status.data?.subsystems ?? {};

  const passedCount = checks.filter((c) => {
    const s = (c.status ?? '').toLowerCase();
    return s === 'pass' || s === 'ok' || s === 'healthy';
  }).length;
  const failedCount = checks.length - passedCount;

  return (
    <>
      {/* Overall status banner */}
      <div className="flex items-center justify-between bg-obsidian/60 border border-hairline rounded-lg px-4 py-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="mono text-[10px] uppercase tracking-wider text-warmgray">Overall Status</span>
          <StatusBadge
            status={overallToBadge(overall)}
            label={overall.toUpperCase()}
          />
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={status.reload}
          disabled={status.loading}
        >
          {status.loading ? 'Refreshing…' : 'Refresh'}
        </Button>
      </div>

      {status.loading && !status.data && <Loading />}

      {status.error && !status.data && (
        <p className="text-[12px] text-helred py-4 text-center">{status.error}</p>
      )}

      {status.data && (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <MetricCard label="Checks" value={checks.length} />
            <MetricCard label="Passed" accent value={passedCount} />
            <MetricCard label="Failed" value={failedCount} />
            <MetricCard
              label="Auto-refresh"
              value="30s"
              sub="interval"
            />
          </div>

          {/* Subsystem grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            {SUBSYSTEM_KEYS.map((key) => {
              const sub = subsystems[key];
              const subStatus: string = sub?.status ?? (sub ? 'healthy' : 'unknown');
              return (
                <div
                  key={key}
                  className="bg-obsidian/40 border border-hairline rounded-lg p-3 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="mono text-[10px] uppercase tracking-wider text-gold">
                      {SUBSYSTEM_LABELS[key]}
                    </span>
                    <span className={cls('w-2 h-2 rounded-full', subsystemDotClass(subStatus))} />
                  </div>
                  <div className="text-[11px] text-warmgray truncate">
                    {sub ? subsystemKeyMetric(sub) : 'No data'}
                  </div>
                  {subStatus && (
                    <div className="text-[10px] mono text-ivory/60 capitalize">{subStatus}</div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Checks list */}
          <Panel
            title="Health Checks"
            subtitle={`${passedCount} passed · ${failedCount} failed`}
            scroll
            className="max-h-[400px]"
          >
            {!checks.length ? (
              <EmptyState message="No health checks reported." />
            ) : (
              <ul className="flex flex-col gap-1.5">
                {checks.map((c: any, i: number) => (
                  <li
                    key={c.name ?? i}
                    className="flex items-start gap-2.5 rounded-lg border border-hairline bg-obsidian/40 px-3 py-2"
                  >
                    <span
                      className={cls(
                        'w-2 h-2 rounded-full mt-1 shrink-0',
                        checkDotClass(c.status ?? ''),
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[12px] text-ivory/90 truncate">{c.name}</span>
                        <span className="mono text-[10px] uppercase text-warmgray shrink-0">
                          {c.status}
                        </span>
                      </div>
                      {c.message && (
                        <div className="text-[11px] text-warmgray mt-0.5 truncate">{c.message}</div>
                      )}
                      {c.metrics && Object.keys(c.metrics).length > 0 && (
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                          {Object.entries(c.metrics).map(([k, v]: any) => (
                            <span key={k} className="mono text-[10px] text-warmgray/70">
                              <span className="text-gold">{k}</span>: {String(v)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

type ReportType = 'daily' | 'weekly';

function renderReportSection(key: string, value: any): React.ReactNode {
  if (value === null || value === undefined) return null;
  const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  if (typeof value === 'object' && !Array.isArray(value)) {
    return (
      <div key={key} className="mb-3">
        <div className="mono text-[10px] uppercase tracking-wider text-gold mb-1">{label}</div>
        <div className="bg-obsidian/40 border border-hairline rounded-lg p-3 flex flex-col gap-1">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="flex justify-between text-[12px]">
              <span className="text-warmgray capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="text-ivory/90 mono text-[11px]">{String(v)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (Array.isArray(value)) {
    if (!value.length) return null;
    return (
      <div key={key} className="mb-3">
        <div className="mono text-[10px] uppercase tracking-wider text-gold mb-1">{label}</div>
        <ul className="bg-obsidian/40 border border-hairline rounded-lg p-3 flex flex-col gap-1">
          {value.map((item: any, i: number) => (
            <li key={i} className="text-[12px] text-ivory/90">
              {typeof item === 'object' ? (
                <pre className="mono text-[10px] text-warmgray whitespace-pre-wrap">
                  {JSON.stringify(item, null, 2)}
                </pre>
              ) : (
                String(item)
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div key={key} className="flex justify-between items-center py-1.5 border-b border-hairline last:border-0">
      <span className="mono text-[10px] uppercase tracking-wider text-warmgray">{label}</span>
      <span className="text-[12px] text-ivory/90">{String(value)}</span>
    </div>
  );
}

function Reports() {
  const [report, setReport] = useState<any>(null);
  const [reportType, setReportType] = useState<ReportType | null>(null);
  const [busy, setBusy] = useState<ReportType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<Date | null>(null);

  async function generate(type: ReportType) {
    setBusy(type);
    setError(null);
    try {
      const result =
        type === 'daily'
          ? await helios.healthMonitor.dailyReport()
          : await helios.healthMonitor.weeklyReport();
      setReport(result);
      setReportType(type);
      setGeneratedAt(new Date());
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="flex items-center gap-2 mb-3">
        <Button
          size="sm"
          variant="gold"
          onClick={() => generate('daily')}
          disabled={busy !== null}
        >
          {busy === 'daily' ? (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full border border-obsidian/60 border-t-transparent animate-spin" />
              Generating…
            </span>
          ) : (
            'Generate Daily Report'
          )}
        </Button>
        <Button
          size="sm"
          variant="primary"
          onClick={() => generate('weekly')}
          disabled={busy !== null}
        >
          {busy === 'weekly' ? (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full border border-gold/40 border-t-transparent animate-spin" />
              Generating…
            </span>
          ) : (
            'Generate Weekly Report'
          )}
        </Button>
        {generatedAt && (
          <span className="mono text-[10px] text-warmgray ml-2">
            Last generated:{' '}
            {generatedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        )}
      </div>

      {error && (
        <p className="text-[12px] text-helred mb-3 px-1">{error}</p>
      )}

      {!report && !busy && !error && (
        <EmptyState message="Generate a daily or weekly report to view it here." />
      )}

      {busy !== null && !report && <Loading label="Generating report…" />}

      {report && (
        <Panel
          title={reportType === 'daily' ? 'Daily Health Report' : 'Weekly Health Report'}
          subtitle={generatedAt ? generatedAt.toLocaleString() : undefined}
          scroll
          className="max-h-[540px]"
        >
          {typeof report === 'object' && report !== null && !Array.isArray(report) ? (
            <div className="flex flex-col">
              {Object.entries(report).map(([k, v]) => renderReportSection(k, v))}
            </div>
          ) : (
            <pre className="mono text-[10px] text-warmgray whitespace-pre-wrap">
              {JSON.stringify(report, null, 2)}
            </pre>
          )}
        </Panel>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

function fmtTimestamp(ts: string | number): string {
  if (!ts) return '—';
  const d = new Date(typeof ts === 'number' ? ts : ts);
  if (isNaN(d.getTime())) return String(ts);
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function fmtDuration(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function historyRowBadgeStatus(overall: string): 'ready' | 'idle' | 'error' {
  if (!overall) return 'idle';
  const l = overall.toLowerCase();
  if (l === 'healthy') return 'ready';
  if (l === 'critical') return 'error';
  return 'idle';
}

function History() {
  const history = useAsync(() => helios.healthMonitor.history(), []);

  const rows: any[] = [...(history.data ?? [])].sort((a, b) => {
    const ta = new Date(a.timestamp ?? 0).getTime();
    const tb = new Date(b.timestamp ?? 0).getTime();
    return tb - ta;
  });

  return (
    <>
      <div className="flex justify-end mb-3">
        <Button
          size="sm"
          variant="ghost"
          onClick={history.reload}
          disabled={history.loading}
        >
          {history.loading ? 'Loading…' : 'Refresh'}
        </Button>
      </div>

      {history.loading && !history.data && <Loading />}

      {history.error && !history.data && (
        <p className="text-[12px] text-helred py-4 text-center">{history.error}</p>
      )}

      {history.data && (
        <Panel
          title="Health Check History"
          subtitle={`${rows.length} records · newest first`}
          scroll
          className="max-h-[560px]"
        >
          {!rows.length ? (
            <EmptyState message="No health check history recorded yet." />
          ) : (
            <table className="w-full text-[12px]">
              <thead>
                <tr className="mono text-[10px] uppercase text-warmgray text-left">
                  <th className="py-1.5 pr-3">Timestamp</th>
                  <th className="py-1.5 pr-3">Status</th>
                  <th className="py-1.5 pr-3 text-right">Passed</th>
                  <th className="py-1.5 pr-3 text-right">Failed</th>
                  <th className="py-1.5 text-right">Duration</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row: any, i: number) => {
                  const failed = row.checks_failed ?? 0;
                  return (
                    <tr key={i} className="border-t border-hairline hover:bg-obsidian/30 transition-colors">
                      <td className="py-1.5 pr-3 mono text-[11px] text-warmgray">
                        {fmtTimestamp(row.timestamp)}
                      </td>
                      <td className="py-1.5 pr-3">
                        <StatusBadge
                          status={historyRowBadgeStatus(row.overall_status)}
                          label={row.overall_status ?? '—'}
                        />
                      </td>
                      <td className="py-1.5 pr-3 text-right mono text-[11px] text-green-400">
                        {row.checks_passed ?? '—'}
                      </td>
                      <td className={cls(
                        'py-1.5 pr-3 text-right mono text-[11px]',
                        failed > 0 ? 'text-helred' : 'text-warmgray',
                      )}>
                        {failed > 0 ? failed : '—'}
                      </td>
                      <td className="py-1.5 text-right mono text-[11px] text-warmgray">
                        {fmtDuration(row.duration_ms)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>
      )}
    </>
  );
}
