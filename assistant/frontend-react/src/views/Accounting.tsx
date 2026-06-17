import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, StatusBadge, EmptyState, Loading } from '../components';
import { fmtMoney } from '../lib/format';
import type { MemoResult } from '../ipc/types';

const TABS = ['Briefing', 'Research', 'Memo', 'Trackers'] as const;
type Tab = typeof TABS[number];

const TRACKERS = [
  { name: 'FASB', desc: 'Accounting Standards Updates, exposure drafts, effective dates' },
  { name: 'SEC', desc: '10-K/10-Q/8-K, disclosure guidance' },
  { name: 'PCAOB', desc: 'Auditing standards and releases' },
  { name: 'IRS', desc: 'Notices, revenue rulings & procedures' },
];

export function Accounting() {
  const [tab, setTab] = useState<Tab>('Briefing');
  return (
    <Page title="Accounting Center" subtitle="briefing · ASC research · technical memos"
      actions={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <Button key={t} size="sm" variant={t === tab ? 'primary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>
          ))}
        </div>
      }>
      {tab === 'Briefing' && <Briefing />}
      {tab === 'Research' && <Research />}
      {tab === 'Memo' && <MemoGen />}
      {tab === 'Trackers' && <Trackers />}
    </Page>
  );
}

function Briefing() {
  const acct = useAsync(() => helios.accounting.summary(), []);
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Income" value={fmtMoney(acct.data?.income)} />
        <MetricCard label="Expenses" value={fmtMoney(acct.data?.expenses)} />
        <MetricCard label="Net" accent value={fmtMoney(acct.data?.net)} />
        <MetricCard label="Receivable" value={fmtMoney(acct.data?.receivable)} />
      </div>
      <Panel title="Daily accounting briefing" subtitle="standards intelligence">
        <p className="text-[12px] text-warmgray leading-relaxed">
          The Accounting Intelligence Engine tracks FASB / SEC / PCAOB / IRS updates and ties them to
          your books and CPA exam topics. The ASC knowledge base and technical-memo generator are live
          (see Research and Memo); scheduled live crawlers populate the daily feed in the next phase.
        </p>
      </Panel>
    </>
  );
}

function Research() {
  const [topic, setTopic] = useState<string | null>(null);
  const topics = useAsync(() => helios.sidecar.ascTopics(), []);
  const detail = useAsync(() => (topic ? helios.sidecar.explainAsc(topic) : Promise.resolve(null)), [topic]);
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-3">
      <Panel title="ASC topics" scroll className="max-h-[440px]">
        {topics.loading ? <Loading /> : topics.error ? <EmptyState message="Sidecar offline." />
          : (topics.data?.topics ?? []).map((t) => (
            <button key={t.asc} onClick={() => setTopic(t.asc.replace('ASC ', ''))}
              className="w-full text-left px-2 py-2 rounded-lg hover:bg-ivory/5 border-b border-hairline">
              <div className="text-[12px] text-gold mono">{t.asc}</div>
              <div className="text-[12px]">{t.title}</div>
            </button>
          ))}
      </Panel>
      <Panel title={detail.data ? detail.data.asc : 'Select a topic'}>
        {!topic ? <EmptyState message="Choose an ASC topic to explain." />
          : detail.loading ? <Loading />
          : detail.data ? (
            <div className="text-[12px] flex flex-col gap-2.5">
              <p className="text-ivory/90">{detail.data.summary}</p>
              {detail.data.framework && (
                <div><b className="text-gold">Framework</b>
                  <ul className="mt-1">{detail.data.framework.map((f: string, i: number) => <li key={i}>• {f}</li>)}</ul></div>
              )}
              {detail.data.fs_impact && <div><b className="text-gold">FS impact</b><p className="text-warmgray">{detail.data.fs_impact}</p></div>}
              {detail.data.cpa_exam && <div><b className="text-gold">CPA exam</b><p className="text-warmgray">{detail.data.cpa_exam}</p></div>}
            </div>
          ) : <EmptyState message="No detail." />}
      </Panel>
    </div>
  );
}

function MemoGen() {
  const [issue, setIssue] = useState('');
  const [facts, setFacts] = useState('');
  const [topic, setTopic] = useState('606');
  const [memo, setMemo] = useState<MemoResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function gen() {
    if (!issue.trim() || !facts.trim()) return;
    setBusy(true); setErr(null);
    try { setMemo(await helios.sidecar.memo({ issue, facts, topic })); }
    catch (e: any) { setErr(/bridge|offline|503/i.test(e.message) ? 'Sidecar offline — start the desktop app.' : e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Technical memo generator" subtitle="Issue · Facts · ASC topic">
        <div className="flex flex-col gap-2">
          <input value={issue} onChange={(e) => setIssue(e.target.value)} placeholder="Issue / question"
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
          <textarea value={facts} onChange={(e) => setFacts(e.target.value)} placeholder="Relevant facts" rows={4}
            className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40 resize-none" />
          <div className="flex gap-2">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="ASC (e.g. 606)"
              className="w-32 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] mono outline-none focus:border-gold/40" />
            <Button variant="gold" onClick={gen} disabled={busy}>{busy ? 'Generating…' : 'Generate memo'}</Button>
          </div>
          {err && <p className="text-[11px] text-helred">{err}</p>}
        </div>
      </Panel>
      <Panel title="Memo" scroll className="max-h-[460px]">
        {!memo ? <EmptyState message="Fill the form to generate a grounded memo." /> : (
          <div className="text-[12px] flex flex-col gap-2.5">
            <Section h="Issue">{memo.issue}</Section>
            <Section h="Facts">{memo.facts}</Section>
            <Section h={`Guidance — ${memo.guidance.citation}`}>{memo.guidance.summary}</Section>
            <Section h="Analysis">{memo.analysis}</Section>
            <Section h="Conclusion">{memo.conclusion}</Section>
            <Section h="Disclosure impact">{memo.disclosure_impact.join(' · ')}</Section>
            <Section h="CPA exam impact">{memo.cpa_exam_impact}</Section>
            <div className="mono text-[10px] text-gold">Citations: {memo.citations.join(', ')}</div>
          </div>
        )}
      </Panel>
    </div>
  );
}

function Section({ h, children }: { h: string; children: React.ReactNode }) {
  return <div><b className="text-gold">{h}</b><p className="text-ivory/90 mt-0.5">{children}</p></div>;
}

function Trackers() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {TRACKERS.map((t) => (
        <Panel key={t.name} title={t.name + ' Tracker'} actions={<StatusBadge status="idle" label="monitoring" />}>
          <p className="text-[12px] text-warmgray">{t.desc}</p>
          <p className="text-[11px] text-warmgray/70 mt-2">
            Source configured. Scheduled crawlers and the effective-date feed populate here in Phase 2;
            ASC research is already live under Research.
          </p>
        </Panel>
      ))}
    </div>
  );
}
