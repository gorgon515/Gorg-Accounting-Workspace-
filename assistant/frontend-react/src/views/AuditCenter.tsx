import { useState, useCallback } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';

// ── types ─────────────────────────────────────────────────────────────────────

interface LogEntry {
  id: string | number;
  ts: string;
  event_type: string;
  actor: string;
  action: string;
  resource: string;
  outcome: string;
  hash?: string;
}

interface ChainResult {
  total: number;
  valid: number;
  invalid: number;
  tampered: number;
  integrity_score: number;
}

// ── helpers ───────────────────────────────────────────────────────────────────

const TABS = ['Audit Log', 'Integrity', 'Export'] as const;
type Tab = typeof TABS[number];

function outcomeClass(outcome: string): string {
  const o = outcome.toLowerCase();
  if (o === 'success' || o === 'ok' || o === 'allowed') return 'text-helgreen';
  if (o === 'error' || o === 'denied' || o === 'failed') return 'text-helred';
  if (o === 'warn' || o === 'warning') return 'text-amber-400';
  return 'text-ivory/80';
}

function eventTypeClass(event_type: string): string {
  const e = event_type.toLowerCase();
  if (e.includes('auth') || e.includes('vault')) return 'text-gold';
  return 'text-ivory/80';
}

// ── sub-views ─────────────────────────────────────────────────────────────────

function AuditLogTab() {
  const [filterEventType, setFilterEventType] = useState('');
  const [filterActor, setFilterActor] = useState('');
  const [filterResource, setFilterResource] = useState('');
  const [appliedFilters, setAppliedFilters] = useState<{
    event_type?: string; actor?: string; resource?: string; limit: number;
  }>({ limit: 50 });

  const [verifyResults, setVerifyResults] = useState<Record<string | number, { valid: boolean; message: string } | 'loading'>>({});

  const log = useAsync(
    () => helios.security.complianceLog(appliedFilters),
    [appliedFilters],
  );

  function applyFilters() {
    setAppliedFilters({
      limit: appliedFilters.limit,
      event_type: filterEventType || undefined,
      actor: filterActor || undefined,
      resource: filterResource || undefined,
    });
  }

  function clearFilters() {
    setFilterEventType('');
    setFilterActor('');
    setFilterResource('');
    setAppliedFilters({ limit: 50 });
  }

  function loadMore() {
    setAppliedFilters((f) => ({ ...f, limit: (f.limit ?? 50) + 50 }));
  }

  async function verifyEntry(id: string | number) {
    setVerifyResults((prev) => ({ ...prev, [id]: 'loading' }));
    try {
      const result = await helios.security.verifyEntry(id);
      setVerifyResults((prev) => ({ ...prev, [id]: result }));
    } catch {
      setVerifyResults((prev) => ({ ...prev, [id]: { valid: false, message: 'Verification failed.' } }));
    }
  }

  const entries: LogEntry[] = log.data ?? [];

  return (
    <div className="flex flex-col gap-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray w-36"
          placeholder="Event type"
          value={filterEventType}
          onChange={(e) => setFilterEventType(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
        />
        <input
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray w-32"
          placeholder="Actor"
          value={filterActor}
          onChange={(e) => setFilterActor(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
        />
        <input
          className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray w-36"
          placeholder="Resource"
          value={filterResource}
          onChange={(e) => setFilterResource(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
        />
        <Button size="sm" variant="primary" onClick={applyFilters}>Apply</Button>
        <Button size="sm" variant="ghost" onClick={clearFilters}>Clear</Button>
      </div>

      {/* Table panel */}
      <Panel
        title="Compliance Log"
        subtitle={log.loading ? 'loading…' : `${entries.length} entr${entries.length === 1 ? 'y' : 'ies'}`}
        scroll
        bodyClass="p-0"
      >
        {log.loading && !entries.length ? (
          <div className="p-4"><Loading /></div>
        ) : log.error && !entries.length ? (
          <div className="p-4"><EmptyState message="Audit log requires the desktop app." /></div>
        ) : !entries.length ? (
          <div className="p-4"><EmptyState message="No entries match the current filters." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-hairline bg-obsidian/60">
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2 w-20">ID</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2 w-36">Timestamp</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2">Event Type</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2">Actor</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2">Action</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2">Resource</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2">Outcome</th>
                  <th className="mono text-[10px] text-warmgray font-normal text-left px-3 py-2 w-24">Verify</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const vr = verifyResults[entry.id];
                  return (
                    <tr key={entry.id} className="border-b border-hairline hover:bg-obsidian/30 transition-colors">
                      <td className="mono text-[10px] text-warmgray px-3 py-2 truncate max-w-[80px]" title={String(entry.id)}>
                        {String(entry.id).slice(0, 8)}
                      </td>
                      <td className="mono text-[11px] text-warmgray px-3 py-2 whitespace-nowrap">
                        {entry.ts ? new Date(entry.ts).toLocaleString() : '—'}
                      </td>
                      <td className={`mono text-[12px] px-3 py-2 ${eventTypeClass(entry.event_type)}`}>
                        {entry.event_type}
                      </td>
                      <td className="text-ivory/90 px-3 py-2">{entry.actor}</td>
                      <td className="text-ivory/80 px-3 py-2">{entry.action}</td>
                      <td className="text-warmgray px-3 py-2 truncate max-w-[120px]" title={entry.resource}>
                        {entry.resource}
                      </td>
                      <td className={`mono text-[12px] px-3 py-2 ${outcomeClass(entry.outcome)}`}>
                        {entry.outcome}
                      </td>
                      <td className="px-3 py-2">
                        {vr === 'loading' ? (
                          <span className="text-warmgray text-[11px]">…</span>
                        ) : vr ? (
                          <span
                            className={`mono text-[11px] ${vr.valid ? 'text-helgreen' : 'text-helred'}`}
                            title={vr.message}
                          >
                            {vr.valid ? '✓' : '✗'}
                          </span>
                        ) : (
                          <button
                            className="mono text-[10px] text-warmgray hover:text-gold transition-colors"
                            onClick={() => verifyEntry(entry.id)}
                          >
                            verify
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!log.loading && entries.length > 0 && (
          <div className="px-4 py-3 border-t border-hairline flex items-center justify-between">
            <span className="mono text-[10px] text-warmgray">{entries.length} loaded</span>
            <Button size="sm" variant="ghost" onClick={loadMore}>Load 50 more</Button>
          </div>
        )}
      </Panel>
    </div>
  );
}

function IntegrityTab() {
  const [chainResult, setChainResult] = useState<ChainResult | null>(null);
  const [chainBusy, setChainBusy] = useState(false);
  const [chainError, setChainError] = useState<string | null>(null);

  const [singleId, setSingleId] = useState('');
  const [singleBusy, setSingleBusy] = useState(false);
  const [singleResult, setSingleResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [singleError, setSingleError] = useState<string | null>(null);

  async function runVerifyChain() {
    setChainBusy(true);
    setChainError(null);
    try {
      const result = await helios.security.verifyChain();
      setChainResult(result);
    } catch (err: any) {
      setChainError(err?.message ?? 'Verification failed.');
    } finally {
      setChainBusy(false);
    }
  }

  async function runVerifyEntry() {
    if (!singleId.trim()) return;
    setSingleBusy(true);
    setSingleError(null);
    setSingleResult(null);
    try {
      const result = await helios.security.verifyEntry(singleId.trim());
      setSingleResult(result);
    } catch (err: any) {
      setSingleError(err?.message ?? 'Verification failed.');
    } finally {
      setSingleBusy(false);
    }
  }

  const score = chainResult ? Math.round(chainResult.integrity_score * 100) / 100 : null;
  const intact = chainResult ? chainResult.invalid === 0 && chainResult.tampered === 0 : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      {/* Chain integrity */}
      <Panel
        title="Chain Integrity"
        subtitle="tamper detection across full audit log"
        actions={
          <Button size="sm" variant="primary" onClick={runVerifyChain} disabled={chainBusy}>
            {chainBusy ? 'Verifying…' : 'Verify Chain'}
          </Button>
        }
      >
        {chainError && (
          <p className="text-helred text-[12px] mb-3">{chainError}</p>
        )}

        {!chainResult && !chainBusy && !chainError && (
          <EmptyState message="Click Verify Chain to run a full integrity check." />
        )}

        {chainBusy && <Loading label="Verifying chain…" />}

        {chainResult && !chainBusy && (
          <div className="flex flex-col gap-3">
            {/* Verdict */}
            <div className={`text-lg font-light tracking-wide ${intact ? 'text-helgreen' : 'text-helred'}`}>
              {intact ? '✓ Chain intact' : '✗ Chain compromised'}
            </div>

            {/* Metrics row */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5">
                <div className="mono text-[10px] text-warmgray uppercase tracking-wider">Total entries</div>
                <div className="text-ivory text-lg font-light mt-0.5 tabular-nums">{chainResult.total}</div>
              </div>
              <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5">
                <div className="mono text-[10px] text-warmgray uppercase tracking-wider">Valid</div>
                <div className="text-helgreen text-lg font-light mt-0.5 tabular-nums">{chainResult.valid}</div>
              </div>
              <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5">
                <div className="mono text-[10px] text-warmgray uppercase tracking-wider">Invalid</div>
                <div className={`text-lg font-light mt-0.5 tabular-nums ${chainResult.invalid > 0 ? 'text-helred' : 'text-helgreen'}`}>
                  {chainResult.invalid}
                </div>
              </div>
              <div className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2.5">
                <div className="mono text-[10px] text-warmgray uppercase tracking-wider">Tampered</div>
                <div className={`text-lg font-light mt-0.5 tabular-nums ${chainResult.tampered > 0 ? 'text-helred' : 'text-helgreen'}`}>
                  {chainResult.tampered}
                </div>
              </div>
            </div>

            {/* Integrity score bar */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="mono text-[10px] text-warmgray uppercase tracking-wider">Integrity score</span>
                <span className={`mono text-[12px] ${(score ?? 0) >= 99 ? 'text-helgreen' : (score ?? 0) >= 90 ? 'text-amber-400' : 'text-helred'}`}>
                  {score !== null ? `${score}%` : '—'}
                </span>
              </div>
              <div className="h-2 rounded-full bg-obsidian border border-hairline overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${(score ?? 0) >= 99 ? 'bg-helgreen' : (score ?? 0) >= 90 ? 'bg-amber-400' : 'bg-helred'}`}
                  style={{ width: `${Math.min(score ?? 0, 100)}%` }}
                />
              </div>
            </div>
          </div>
        )}
      </Panel>

      {/* Verify single entry */}
      <Panel title="Verify Single Entry" subtitle="check hash integrity for one log entry">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray"
              placeholder="Entry ID"
              value={singleId}
              onChange={(e) => setSingleId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !singleBusy && runVerifyEntry()}
            />
            <Button
              size="sm"
              variant="primary"
              onClick={runVerifyEntry}
              disabled={singleBusy || !singleId.trim()}
            >
              {singleBusy ? 'Checking…' : 'Verify'}
            </Button>
          </div>

          {singleError && (
            <p className="text-helred text-[12px]">{singleError}</p>
          )}

          {singleResult && (
            <div className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-[12px] ${singleResult.valid ? 'border-helgreen/30 bg-helgreen/5 text-helgreen' : 'border-helred/30 bg-helred/5 text-helred'}`}>
              <span className="text-base leading-none mt-0.5">{singleResult.valid ? '✓' : '✗'}</span>
              <div>
                <div className="font-medium">{singleResult.valid ? 'Valid' : 'Invalid'}</div>
                {singleResult.message && (
                  <div className="mt-0.5 text-[11px] opacity-80">{singleResult.message}</div>
                )}
              </div>
            </div>
          )}

          {!singleResult && !singleError && !singleBusy && (
            <p className="text-[11px] text-warmgray">Enter an entry ID from the audit log to verify its hash signature.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}

function ExportTab() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [busy, setBusy] = useState(false);
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function filterByDateRange(entries: LogEntry[]): LogEntry[] {
    if (!startDate && !endDate) return entries;
    return entries.filter((e) => {
      const ts = new Date(e.ts).getTime();
      if (startDate && ts < new Date(startDate).getTime()) return false;
      if (endDate && ts > new Date(endDate + 'T23:59:59').getTime()) return false;
      return true;
    });
  }

  async function handleExport() {
    setBusy(true);
    setError(null);
    setPreviewCount(null);
    try {
      const all = await helios.security.complianceLog({});
      const filtered = filterByDateRange(all as LogEntry[]);
      setPreviewCount(filtered.length);
      const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log${startDate ? `-from-${startDate}` : ''}${endDate ? `-to-${endDate}` : ''}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message ?? 'Export failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Export Compliance Log" subtitle="downloads as JSON">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="mono text-[10px] text-warmgray uppercase tracking-wider">Date range</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <span className="text-warmgray text-[12px]">to</span>
              <input
                type="date"
                className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 text-ivory/90 placeholder:text-warmgray"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <p className="text-[11px] text-warmgray">
            Exports all matching entries as JSON. Leave dates empty to export the full audit log.
          </p>

          {error && <p className="text-helred text-[12px]">{error}</p>}

          {previewCount !== null && !busy && (
            <div className="flex items-center gap-2 rounded-lg border border-helgreen/30 bg-helgreen/5 px-3 py-2 text-[12px] text-helgreen">
              <span>✓</span>
              <span>Exported {previewCount} entr{previewCount === 1 ? 'y' : 'ies'}</span>
            </div>
          )}

          <Button variant="gold" onClick={handleExport} disabled={busy}>
            {busy ? 'Fetching…' : 'Export audit-log.json'}
          </Button>
        </div>
      </Panel>

      <Panel title="Export Notes" subtitle="format reference">
        <ul className="flex flex-col gap-2 text-[12px] text-warmgray">
          <li className="flex gap-2">
            <span className="text-gold mt-0.5">·</span>
            <span>Output is a JSON array of log entries.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-gold mt-0.5">·</span>
            <span>Each entry includes: id, ts, event_type, actor, action, resource, outcome, hash.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-gold mt-0.5">·</span>
            <span>Date filtering is applied client-side after fetching all entries.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-gold mt-0.5">·</span>
            <span>Hash fields can be cross-verified using the Integrity tab.</span>
          </li>
        </ul>
      </Panel>
    </div>
  );
}

// ── main view ─────────────────────────────────────────────────────────────────

export function AuditCenter() {
  const [tab, setTab] = useState<Tab>('Audit Log');

  if (!helios.hasBridge()) {
    return (
      <Page title="Audit Center" subtitle="audit log · integrity · export">
        <EmptyState message="Open in desktop app to use Audit Center." />
      </Page>
    );
  }

  return (
    <Page
      title="Audit Center"
      subtitle="audit log · integrity · export"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button
              key={t}
              size="sm"
              variant={tab === t ? 'primary' : 'ghost'}
              onClick={() => setTab(t)}
            >
              {t}
            </Button>
          ))}
        </div>
      }
    >
      {tab === 'Audit Log' && <AuditLogTab />}
      {tab === 'Integrity' && <IntegrityTab />}
      {tab === 'Export' && <ExportTab />}
    </Page>
  );
}
