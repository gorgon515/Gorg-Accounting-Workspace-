import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage } from './_langpicker';

// Assessments — placement test, level/unit tests, CEFR evaluation, weakness
// detection and study recommendations.
export function Assessments() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Assessments." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const [tab, setTab] = useState<'placement' | 'tests'>('placement');

  return (
    <Page title="Assessments" subtitle="placement · level exams · weakness detection · recommendations"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <Panel title="Mode">
          <div className="flex gap-1.5">
            {(['placement', 'tests'] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={cls('px-3 py-1.5 rounded border text-[11px] mono capitalize',
                  tab === t ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>{t}</button>
            ))}
          </div>
        </Panel>
        {tab === 'placement' ? <Placement lang={lang} /> : <Tests lang={lang} />}
      </div>
    </Page>
  );
}

function Placement({ lang }: { lang: string }) {
  const test = useAsync(() => helios.languageAcademy.placement({ language: lang }), [lang]);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const questions: any[] = test.data?.questions ?? (Array.isArray(test.data) ? test.data : []);

  async function submit() {
    setBusy(true);
    try { setResult(await helios.languageAcademy.placement({ language: lang, answers })); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-3">
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard label="Estimated CEFR" value={result.estimated_level ?? result.level ?? '—'} accent />
          <MetricCard label="Score" value={result.score != null ? `${Math.round(result.score)}` : '—'} />
          <MetricCard label="Areas tested" value={Object.keys(result.per_area ?? result.breakdown ?? {}).length || '—'} />
        </div>
      )}
      <Panel title="Placement Test" subtitle={`${questions.length} questions · ${lang}`}
        actions={<Button size="sm" variant="gold" onClick={submit} disabled={busy}>{busy ? '…' : 'Submit & Estimate'}</Button>}>
        {test.loading ? <Loading /> : questions.length === 0 ? (
          <EmptyState message="Placement test unavailable." />
        ) : (
          <QuestionList questions={questions} answers={answers} setAnswers={setAnswers} />
        )}
      </Panel>
      {result && <Weakness result={result} />}
    </div>
  );
}

function Tests({ lang }: { lang: string }) {
  const tests = useAsync(() => helios.languageAcademy.tests({ language: lang }), [lang]);
  const [openId, setOpenId] = useState<string | null>(null);
  const detail = useAsync(() => (openId ? helios.languageAcademy.tests({ language: lang }) : Promise.resolve(null)), [openId]);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const list: any[] = Array.isArray(tests.data) ? tests.data : (tests.data?.tests ?? []);
  const open = list.find((t) => (t.id ?? t.test_id) === openId);
  const questions: any[] = open?.questions ?? [];

  async function submit() {
    if (!openId) return;
    setBusy(true);
    try { setResult(await helios.languageAcademy.submitTest({ test_id: openId, answers })); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Tests" subtitle={`${list.length} · ${lang}`}>
        {tests.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No tests available." />
        ) : (
          <div className="grid gap-1.5 max-h-[460px] overflow-y-auto scroll-thin">
            {list.map((t: any) => {
              const id = t.id ?? t.test_id;
              return (
                <div key={id}
                  className={cls('flex items-center gap-2 px-2.5 py-2 rounded border cursor-pointer hover:bg-ivory/5',
                    openId === id ? 'border-gold/40 bg-gold/5' : 'border-hairline')}
                  onClick={() => { setOpenId(id); setAnswers({}); setResult(null); }}>
                  <span className="mono text-[10px] text-gold w-8">{t.level}</span>
                  <span className="text-[12px] flex-1">{t.title ?? t.name}</span>
                  <span className="mono text-[10px] text-warmgray">{t.kind ?? 'unit'}</span>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel title={open?.title ?? 'Test'} subtitle={openId ? `${questions.length} questions` : 'select a test'}
        actions={openId ? <Button size="sm" variant="gold" onClick={submit} disabled={busy}>{busy ? '…' : 'Submit'}</Button> : undefined}>
        {!openId ? <EmptyState message="Select a test to begin." />
          : result ? <Weakness result={result} />
            : questions.length === 0 ? <EmptyState message="No questions in this test." />
              : <QuestionList questions={questions} answers={answers} setAnswers={setAnswers} />}
      </Panel>
    </div>
  );
}

function QuestionList({ questions, answers, setAnswers }: {
  questions: any[]; answers: Record<string, any>; setAnswers: (a: Record<string, any>) => void;
}) {
  return (
    <div className="grid gap-2.5 max-h-[420px] overflow-y-auto scroll-thin">
      {questions.map((q: any, n: number) => {
        const qid = q.id ?? String(n);
        const opts: any[] = q.options ?? q.choices ?? [];
        return (
          <div key={qid} className="px-2.5 py-2 rounded border border-hairline">
            <p className="text-[12px] mb-1.5"><span className="mono text-gold mr-1.5">{n + 1}.</span>{q.q ?? q.prompt ?? q.question}</p>
            {opts.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {opts.map((o: any, k: number) => {
                  const val = typeof o === 'string' ? o : o.value ?? o.text;
                  return (
                    <button key={k} onClick={() => setAnswers({ ...answers, [qid]: val })}
                      className={cls('px-2 py-1 rounded border text-[11px]',
                        answers[qid] === val ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray hover:bg-ivory/5')}>
                      {val}
                    </button>
                  );
                })}
              </div>
            ) : (
              <input className="w-full bg-obsidian border border-hairline rounded px-2 py-1 text-[12px]"
                placeholder="Your answer" value={answers[qid] ?? ''}
                onChange={(e) => setAnswers({ ...answers, [qid]: e.target.value })} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function Weakness({ result }: { result: any }) {
  const weaknesses: any[] = result.weaknesses ?? [];
  const recs: any[] = result.recommendations ?? [];
  const perTopic: Array<[string, any]> = Object.entries(result.per_topic ?? result.per_area ?? result.breakdown ?? {});
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <MetricCard label="Score" value={result.score != null ? `${Math.round(result.score)}` : '—'} accent />
        <MetricCard label="Result" value={result.passed != null ? (result.passed ? 'PASS' : 'REVIEW') : (result.estimated_level ?? '—')} />
        <MetricCard label="Weak areas" value={weaknesses.length || '—'} />
      </div>
      {perTopic.length > 0 && (
        <Panel title="By area">
          <div className="grid gap-1">
            {perTopic.map(([k, v]) => {
              const pct = typeof v === 'number' ? v : (v?.score ?? 0);
              return (
                <div key={k} className="flex items-center gap-2">
                  <span className="text-[11px] w-28 capitalize truncate">{k.replace(/_/g, ' ')}</span>
                  <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                    <div className={cls('h-full rounded-full', pct >= 70 ? 'bg-helgreen' : pct >= 40 ? 'bg-gold' : 'bg-helred')}
                      style={{ width: `${Math.min(100, pct)}%` }} />
                  </div>
                  <span className="mono text-[10px] text-warmgray w-8 text-right">{Math.round(pct)}</span>
                </div>
              );
            })}
          </div>
        </Panel>
      )}
      {recs.length > 0 && (
        <Panel title="Study Recommendations">
          <ul className="grid gap-1">
            {recs.map((r: any, n: number) => (
              <li key={n} className="flex gap-1.5 text-[12px] text-ivory/80"><span className="text-gold">•</span>{typeof r === 'string' ? r : r.text ?? JSON.stringify(r)}</li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
