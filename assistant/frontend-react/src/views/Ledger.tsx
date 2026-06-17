import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, Table, StatusBadge, EmptyState, Loading } from '../components';
import type { Column } from '../components';
import { fmtMoney } from '../lib/format';

const TABS = ['Dashboard', 'Statements', 'Journal', 'AR / AP', 'Audit'] as const;
type Tab = typeof TABS[number];

export function Ledger() {
  const [tab, setTab] = useState<Tab>('Dashboard');
  const chart = useAsync(() => helios.sidecar.acctChart(), []);
  const seeded = (chart.data?.accounts?.length ?? 0) > 0;

  return (
    <Page title="Accounting Platform" subtitle="double-entry GL · statements · AR/AP · audit"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>)}
        </div>
      }>
      {!seeded && !chart.loading && (
        <Panel title="Set up your books" className="mb-3">
          <p className="text-[12px] text-warmgray mb-2">No chart of accounts yet. Seed a template to begin double-entry bookkeeping.</p>
          <div className="flex gap-2">
            {['general_small_business', 'professional_firm', 'tax_firm'].map((t) => (
              <Button key={t} variant="gold" onClick={async () => { await helios.sidecar.acctSeed(t); chart.reload(); }}>{t.replace(/_/g, ' ')}</Button>
            ))}
          </div>
        </Panel>
      )}
      {tab === 'Dashboard' && <Dash />}
      {tab === 'Statements' && <Statements />}
      {tab === 'Journal' && <Journal />}
      {tab === 'AR / AP' && <ARAP />}
      {tab === 'Audit' && <Audit />}
    </Page>
  );
}

function Dash() {
  const d = useAsync(() => helios.sidecar.acctDashboard(), []);
  const o = d.data;
  return d.loading ? <Loading /> : !o ? <EmptyState message="Platform offline." /> : (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Cash position" accent value={fmtMoney(o.cash_position)} />
        <MetricCard label="Receivables" value={fmtMoney(o.receivables?.total)} />
        <MetricCard label="Payables" value={fmtMoney(o.payables?.total)} />
        <MetricCard label="YTD net income" value={fmtMoney(o.profitability?.ytd_net_income)} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Balance sheet" subtitle={o.balance_sheet_summary?.balanced ? 'balanced ✓' : 'OUT OF BALANCE'}>
          <Row k="Total assets" v={fmtMoney(o.balance_sheet_summary?.total_assets)} />
          <Row k="Total liabilities" v={fmtMoney(o.balance_sheet_summary?.total_liabilities)} />
          <Row k="Total equity" v={fmtMoney(o.balance_sheet_summary?.total_equity)} />
        </Panel>
        <Panel title="Alerts & recent entries">
          {(o.alerts ?? []).map((a: any, i: number) => (
            <div key={i} className="text-[12px] text-helred/90 mb-1">⚠ {a.message}</div>
          ))}
          <ul className="text-[12px] mt-1">
            {(o.recent_entries ?? []).slice(0, 6).map((e: any) => (
              <li key={e.id} className="flex justify-between border-b border-hairline py-1">
                <span className="truncate">{e.date} · {e.memo || e.source}</span>
                <span className="mono text-warmgray">{fmtMoney(e.amount)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}

function Statements() {
  const year = new Date().getFullYear();
  const tb = useAsync(() => helios.sidecar.acctTrialBalance(), []);
  const bs = useAsync(() => helios.sidecar.acctBalanceSheet(), []);
  const inc = useAsync(() => helios.sidecar.acctIncome(`${year}-01-01`, `${year}-12-31`), []);
  const cols: Column<any>[] = [
    { key: 'n', header: 'Acct', render: (r) => <span className="mono text-warmgray">{r.number}</span> },
    { key: 'name', header: 'Name', render: (r) => r.name },
    { key: 'd', header: 'Debit', align: 'right', render: (r) => r.debit ? fmtMoney(r.debit) : '' },
    { key: 'c', header: 'Credit', align: 'right', render: (r) => r.credit ? fmtMoney(r.credit) : '' },
  ];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Trial balance" subtitle={tb.data?.balanced ? 'balanced ✓' : ''} scroll className="max-h-[460px]">
        {tb.loading ? <Loading /> : <Table columns={cols} rows={tb.data?.rows ?? []} empty="No posted entries." />}
      </Panel>
      <div className="flex flex-col gap-3">
        <Panel title="Income statement (YTD)">
          {inc.data ? <>
            <Row k="Revenue" v={fmtMoney(inc.data.total_revenue)} />
            <Row k="Expenses" v={fmtMoney(inc.data.total_expenses)} />
            <Row k="Net income" v={fmtMoney(inc.data.net_income)} accent />
          </> : <Loading />}
        </Panel>
        <Panel title="Balance sheet" subtitle={bs.data?.balanced ? 'balanced ✓' : ''}>
          {bs.data ? <>
            <Row k="Assets" v={fmtMoney(bs.data.total_assets)} />
            <Row k="Liabilities" v={fmtMoney(bs.data.total_liabilities)} />
            <Row k="Equity (incl. earnings)" v={fmtMoney(bs.data.total_equity)} accent />
          </> : <Loading />}
        </Panel>
      </div>
    </div>
  );
}

function Journal() {
  const list = useAsync(() => helios.sidecar.acctEntries(), []);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [memo, setMemo] = useState('');
  const [da, setDa] = useState(''); const [dAmt, setDAmt] = useState('');
  const [ca, setCa] = useState(''); const [cAmt, setCAmt] = useState('');
  const [err, setErr] = useState('');
  async function post() {
    setErr('');
    try {
      await helios.sidecar.acctJournal({ date, memo, lines: [
        { account: da, debit: Number(dAmt) }, { account: ca, credit: Number(cAmt) }] });
      setMemo(''); setDAmt(''); setCAmt(''); list.reload();
    } catch (e: any) { setErr(/400|balanced|account/i.test(e.message) ? e.message : 'Posting failed — check accounts and that debits equal credits.'); }
  }
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Post journal entry" subtitle="debits must equal credits">
        <div className="flex flex-col gap-2 text-[12px]">
          <div className="flex gap-2">
            <input value={date} onChange={(e) => setDate(e.target.value)} className="bg-obsidian/60 border border-hairline rounded-lg px-2 py-2 mono" />
            <input value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="Memo" className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2" />
          </div>
          <div className="flex gap-2 items-center">
            <span className="w-12 text-helgreen">Debit</span>
            <input value={da} onChange={(e) => setDa(e.target.value)} placeholder="acct #" className="w-20 bg-obsidian/60 border border-hairline rounded-lg px-2 py-2 mono" />
            <input value={dAmt} onChange={(e) => setDAmt(e.target.value)} placeholder="amount" className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-2 py-2" />
          </div>
          <div className="flex gap-2 items-center">
            <span className="w-12 text-helred">Credit</span>
            <input value={ca} onChange={(e) => setCa(e.target.value)} placeholder="acct #" className="w-20 bg-obsidian/60 border border-hairline rounded-lg px-2 py-2 mono" />
            <input value={cAmt} onChange={(e) => setCAmt(e.target.value)} placeholder="amount" className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-2 py-2" />
          </div>
          <Button variant="gold" onClick={post}>Post entry</Button>
          {err && <p className="text-helred text-[11px]">{err}</p>}
        </div>
      </Panel>
      <Panel title="Recent entries" scroll className="max-h-[460px]">
        {list.loading ? <Loading /> : !(list.data?.entries?.length) ? <EmptyState message="No entries yet." /> : (
          <ul className="flex flex-col gap-1.5">
            {list.data.entries.map((e: any) => (
              <li key={e.id} className="rounded-lg border border-hairline bg-obsidian/40 px-3 py-2 text-[12px]">
                <div className="flex justify-between"><span>#{e.id} · {e.date}</span><StatusBadge status={e.status === 'posted' ? 'ready' : 'idle'} label={e.status} /></div>
                <div className="text-warmgray">{e.memo}</div>
                {e.lines.map((l: any, i: number) => (
                  <div key={i} className="flex justify-between mono text-[10px] text-warmgray/80">
                    <span>{l.account_number} {l.account_name}</span>
                    <span>{l.debit ? `Dr ${fmtMoney(l.debit)}` : `Cr ${fmtMoney(l.credit)}`}</span>
                  </div>
                ))}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function ARAP() {
  const ar = useAsync(() => helios.sidecar.acctArAging(), []);
  const ap = useAsync(() => helios.sidecar.acctApAging(), []);
  const bucket = (data: any) => (
    <div className="grid grid-cols-5 gap-1 text-center text-[11px] mb-2">
      {['current', '1-30', '31-60', '61-90', '90+'].map((b) => (
        <div key={b} className="rounded border border-hairline py-1">
          <div className="mono text-[9px] text-warmgray">{b}</div>
          <div>{fmtMoney(data?.buckets?.[b])}</div>
        </div>
      ))}
    </div>
  );
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Accounts receivable aging" subtitle={`total ${fmtMoney(ar.data?.total)}`}>
        {ar.loading ? <Loading /> : <>{bucket(ar.data)}
          {(ar.data?.invoices ?? []).map((i: any) => (
            <div key={i.invoice_id} className="flex justify-between text-[12px] border-b border-hairline py-1">
              <span>{i.customer}</span><span className="mono text-warmgray">{fmtMoney(i.balance)} · {i.bucket}</span>
            </div>
          ))}</>}
      </Panel>
      <Panel title="Accounts payable aging" subtitle={`total ${fmtMoney(ap.data?.total)}`}>
        {ap.loading ? <Loading /> : <>{bucket(ap.data)}
          {(ap.data?.bills ?? []).map((b: any) => (
            <div key={b.bill_id} className="flex justify-between text-[12px] border-b border-hairline py-1">
              <span>{b.vendor}</span><span className="mono text-warmgray">{fmtMoney(b.balance)} · {b.bucket}</span>
            </div>
          ))}</>}
      </Panel>
    </div>
  );
}

function Audit() {
  const a = useAsync(() => helios.sidecar.acctAudit(), []);
  return (
    <Panel title="Audit trail" subtitle="immutable — every action logged" scroll className="max-h-[560px]">
      {a.loading ? <Loading /> : !(a.data?.events?.length) ? <EmptyState message="No events yet." /> : (
        <ul className="flex flex-col gap-1">
          {a.data.events.map((e: any) => (
            <li key={e.id} className="flex items-center gap-2 text-[11px] border-b border-hairline py-1">
              <span className="mono text-warmgray w-36 truncate">{e.ts?.slice(0, 19).replace('T', ' ')}</span>
              <span className="mono text-gold w-28 truncate">{e.entity} #{e.entity_id}</span>
              <span className="w-20">{e.action}</span>
              <span className="text-warmgray truncate flex-1">{e.user}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function Row({ k, v, accent }: { k: string; v: any; accent?: boolean }) {
  return (
    <div className="flex justify-between border-b border-hairline py-1.5 text-[12px]">
      <span className="text-warmgray">{k}</span>
      <span className={accent ? 'text-gold' : 'text-ivory'}>{v}</span>
    </div>
  );
}
