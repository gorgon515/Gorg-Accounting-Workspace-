import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, StatusBadge, EmptyState, Loading } from '../components';
import { fmtMoney } from '../lib/format';

const TABS = ['Documents', 'Tax Research', 'Workpapers', 'Due Diligence', 'Search'] as const;
type Tab = typeof TABS[number];

export function Workbench() {
  const [tab, setTab] = useState<Tab>('Documents');
  return (
    <Page title="Tax & Advisory Workbench" subtitle="document intelligence · tax research · workpapers · diligence"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>)}
        </div>
      }>
      {tab === 'Documents' && <Documents />}
      {tab === 'Tax Research' && <TaxResearch />}
      {tab === 'Workpapers' && <Workpapers />}
      {tab === 'Due Diligence' && <DueDiligence />}
      {tab === 'Search' && <Search />}
    </Page>
  );
}

function Documents() {
  const ocr = useAsync(() => helios.sidecar.ocrStatus(), []);
  const [text, setText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    if (!text.trim()) return;
    setBusy(true);
    try { setResult(await helios.sidecar.docProcess({ text, filename: 'pasted.txt', save: true })); }
    catch { setResult(null); } finally { setBusy(false); }
  }
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Process a document" subtitle="paste text, or the brain can ingest files"
        actions={<StatusBadge status={ocr.data?.tesseract ? 'ready' : 'idle'} label={ocr.data?.tesseract ? 'OCR ready' : 'OCR: install Tesseract'} />}>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8}
          placeholder="Paste invoice / W-2 / 1099 / bank statement text…"
          className="w-full bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 resize-none mb-2" />
        <Button variant="gold" onClick={run} disabled={busy}>{busy ? 'Processing…' : 'Extract & classify'}</Button>
        <p className="text-[10px] text-warmgray/70 mt-2">{ocr.data?.note}</p>
      </Panel>
      <Panel title="Extraction result">
        {!result ? <EmptyState message="Process a document to see classification + extracted fields." /> : (
          <div className="text-[12px] flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="mono text-[10px] uppercase text-gold">{result.doc_type}</span>
              <StatusBadge status="ready" label={`${Math.round((result.classification_confidence || 0) * 100)}% confident`} />
            </div>
            <div className="rounded-lg border border-hairline bg-obsidian/40 p-2">
              {Object.entries(result.fields || {}).filter(([, v]) => v != null && !Array.isArray(v)).map(([k, v]: any) => (
                <div key={k} className="flex justify-between"><span className="text-warmgray">{k}</span>
                  <span>{typeof v === 'number' ? fmtMoney(v) : String(v)}</span></div>
              ))}
            </div>
            {result.validation && (
              <div className={result.validation.valid ? 'text-helgreen' : 'text-helred'}>
                {result.validation.valid ? '✓ validated' : '⚠ ' + (result.validation.issues || []).join('; ')}
              </div>
            )}
            <p className="text-warmgray text-[11px]">{result.summary}</p>
          </div>
        )}
      </Panel>
    </div>
  );
}

function TaxResearch() {
  const [q, setQ] = useState('home office');
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState('');
  async function go() {
    setErr('');
    try { setRes(await helios.sidecar.taxResearch(q)); }
    catch (e: any) { setErr('Topic not in the tax knowledge base. Try: home office, meals, §179, QBI, S-corp comp, hobby loss.'); setRes(null); }
  }
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Tax research" subtitle="primary authorities, ranked by hierarchy">
        <div className="flex gap-2 mb-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px]" />
          <Button variant="gold" onClick={go}>Research</Button>
        </div>
        {err && <p className="text-helred text-[11px]">{err}</p>}
        {res && <p className="text-[12px] text-ivory/90">{res.summary}</p>}
      </Panel>
      <Panel title="Authorities & planning">
        {!res ? <EmptyState message="Run a query." /> : (
          <div className="text-[12px]">
            <div className="mono text-[10px] uppercase text-warmgray mb-1">Authorities (highest first)</div>
            {res.authorities.map((a: any, i: number) => (
              <div key={i} className="flex justify-between border-b border-hairline py-1">
                <span>{a.cite}</span><span className="mono text-[10px] text-warmgray">{a.type} · {a.weight}</span>
              </div>
            ))}
            <div className="mono text-[10px] uppercase text-warmgray mt-2 mb-1">Planning</div>
            <ul>{res.planning_opportunities.map((p: string, i: number) => <li key={i}>• {p}</li>)}</ul>
            <p className="text-helred/90 text-[11px] mt-2">Risk: {res.risk_assessment}</p>
          </div>
        )}
      </Panel>
    </div>
  );
}

function Workpapers() {
  const tb = useAsync(() => helios.sidecar.wpTrialBalance(), []);
  return (
    <Panel title="Trial Balance workpaper" subtitle={tb.data ? (tb.data.tie_out ? 'ties out ✓' : 'OUT OF BALANCE') : ''} scroll className="max-h-[560px]">
      {tb.loading ? <Loading /> : !(tb.data?.rows?.length) ? <EmptyState message="Seed the chart of accounts and post entries in the Ledger first." /> : (
        <table className="w-full text-[12px]">
          <thead><tr className="mono text-[10px] uppercase text-warmgray text-left"><th className="py-1">Ref</th><th>Account</th><th className="text-right">Debit</th><th className="text-right">Credit</th></tr></thead>
          <tbody>
            {tb.data.rows.map((r: any) => (
              <tr key={r.ref} className="border-t border-hairline">
                <td className="mono text-warmgray py-1">{r.ref}</td><td>{r.number} {r.name}</td>
                <td className="text-right tabular-nums">{r.debit ? fmtMoney(r.debit) : ''}</td>
                <td className="text-right tabular-nums">{r.credit ? fmtMoney(r.credit) : ''}</td>
              </tr>
            ))}
            <tr className="border-t border-gold/40 text-gold"><td /><td>Total</td>
              <td className="text-right">{fmtMoney(tb.data.total_debit)}</td><td className="text-right">{fmtMoney(tb.data.total_credit)}</td></tr>
          </tbody>
        </table>
      )}
    </Panel>
  );
}

function DueDiligence() {
  const year = new Date().getFullYear();
  const dd = useAsync(() => helios.sidecar.advisoryDD(year), []);
  const d = dd.data;
  return dd.loading ? <Loading /> : !d ? <EmptyState message="Diligence runs on the live books." /> : (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Diligence summary"><p className="text-[12px] mb-2">{d.summary}</p>
        <div className="text-[12px]">
          <div className="flex justify-between border-b border-hairline py-1"><span className="text-warmgray">Top customer share</span><span>{((d.customer_concentration?.top_share || 0) * 100).toFixed(0)}%</span></div>
          <div className="flex justify-between border-b border-hairline py-1"><span className="text-warmgray">Working capital</span><span>{fmtMoney(d.working_capital)}</span></div>
          <div className="flex justify-between border-b border-hairline py-1"><span className="text-warmgray">OCF / Net income</span><span>{d.quality_of_earnings?.cf_to_ni ?? '—'}</span></div>
        </div>
      </Panel>
      <Panel title="Risk flags">
        {(d.risks ?? []).length ? <ul className="text-[12px]">{d.risks.map((r: string, i: number) => <li key={i} className="text-helred/90 border-b border-hairline py-1">⚠ {r}</li>)}</ul>
          : <EmptyState message="No material risk flags." />}
      </Panel>
    </div>
  );
}

function Search() {
  const [q, setQ] = useState('');
  const [res, setRes] = useState<any>(null);
  async function go() { if (q.trim()) try { setRes(await helios.sidecar.globalSearch(q)); } catch { setRes(null); } }
  return (
    <Panel title="Global search" subtitle="documents · accounting · tax research · clients">
      <form className="flex gap-2 mb-3" onSubmit={(e) => { e.preventDefault(); go(); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search everything…"
          className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
        <Button variant="gold" type="submit">Search</Button>
      </form>
      {!res ? <EmptyState message="Search across all of HELIOS." /> : !res.results.length ? <EmptyState message="No matches." /> : (
        <ul className="flex flex-col gap-1.5">
          {res.results.map((r: any, i: number) => (
            <li key={i} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2">
              <div className="flex justify-between"><span className="text-[12px]">{r.title}</span>
                <span className="mono text-[9px] uppercase text-gold">{r.source} · {r.score}</span></div>
              {r.snippet && <div className="text-[11px] text-warmgray truncate">{r.snippet}</div>}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
