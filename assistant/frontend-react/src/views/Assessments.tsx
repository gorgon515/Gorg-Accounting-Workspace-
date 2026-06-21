import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage } from './_langpicker';

// Assessments — placement test, level/unit exams, CEFR evaluation, weakness
// detection and study recommendations. Answers are graded by position.
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
        {tab === 'placement' ? <Placement key={lang} lang={lang} /> : <Tests key={lang} lang={lang} />}
      </div>
    </Page>
  );
}

function Placement({ lang }: { lang: string }) {
  const test = useAsync(() => helios.languageAcademy.placement({ language: lang }), [lang]);
  const [answers, setAnswers] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const questions: any[] = test.data?.questions ?? [];

  async function submit() {
    setBusy(true);
    try { setResult(await helios.languageAcademy.placement({ language: lang, answers })); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-3">
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard label="Estimated CEFR" value={result.estimated_level ?? '—'} accent />
          <MetricCard label="Score" value={pct(result.score)} sub={`${result.correct}/${result.total}`} />
          <MetricCard label="Recommendation" value={result.estimated_level ?? '—'} sub={result.recommendation} />
        </div>
      )}
      <Panel title="Placement Test" subtitle={`${questions.length} questions · ${lang}`}
        actions={<Button size="sm" variant="gold" onClick={submit} disabled={busy || questions.length === 0}>{busy ? '…' : 'Submit & Estimate'}</Button>}>
        {test.loading ? <Loading /> : questions.length === 0 ? (
          <EmptyState message="Placement test unavailable." />
        ) : (
          <QuestionList questions={questions} answers={answers} setAnswers={setAnswers} />
        )}
      </Panel>
      {result?.per_area && <AreaBars title="By area" data={result.per_area} />}
      {result?.per_level && <AreaBars title="By CEFR level" data={result.per_level} />}
    </div>
  );
}

function Tests({ lang }: { lang: string }) {
  const tests = useAsync(() => helios.languageAcademy.tests({ language: lang }), [lang]);
  const [openId, setOpenId] = useState<string | null>(null);
  const detail = useAsync(() => (openId ? helios.languageAcademy.test(openId) : Promise.resolve(null)), [openId]);
  const [answers, setAnswers] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const list: any[] = Array.isArray(tests.data) ? tests.data : (tests.data?.tests ?? []);
  const questions: any[] = detail.data?.questions ?? [];

  async function submit() {
    if (!openId) return;
    setBusy(true);
    try { setResult(await helios.languageAcademy.submitTest({ test_id: openId, answers })); }
    finally { setBusy(false); }
  }

  function select(id: string) {
    setOpenId(id); setAnswers([]); setResult(null);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel title="Tests" subtitle={`${list.length} · ${lang}`}>
        {tests.loading ? <Loading /> : list.length === 0 ? (
          <EmptyState message="No tests available." />
        ) : (
          <div className="grid gap-1.5 max-h-[520px] overflow-y-auto scroll-thin">
            {list.map((t: any) => {
              const id = t.id ?? t.test_id;
              return (
                <div key={id}
                  className={cls('flex items-center gap-2 px-2.5 py-2 rounded border cursor-pointer hover:bg-ivory/5',
                    openId === id ? 'border-gold/40 bg-gold/5' : 'border-hairline')}
                  onClick={() => select(id)}>
                  <span className="mono text-[10px] text-gold w-8">{t.level}</span>
                  <span className="text-[12px] flex-1 truncate">{t.title ?? t.name}</span>
                  <span className="mono text-[9px] text-warmgray uppercase">{t.kind ?? 'unit'}</span>
                  <span className="mono text-[10px] text-warmgray">{t.question_count ?? ''}</span>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel title={detail.data?.title ?? 'Test'} subtitle={openId ? `${questions.length} questions` : 'select a test'}
        actions={openId && !result ? <Button size="sm" variant="gold" onClick={submit} disabled={busy || questions.length === 0}>{busy ? '…' : 'Submit'}</Button> : undefined}>
        {!openId ? <EmptyState message="Select a test to begin." />
          : result ? <Result result={result} />
            : detail.loading ? <Loading />
              : questions.length === 0 ? <EmptyState message="No questions in this test." />
                : <QuestionList questions={questions} answers={answers} setAnswers={setAnswers} />}
      </Panel>
    </div>
  );
}

function QuestionList({ questions, answers, setAnswers }: {
  questions: any[]; answers: any[]; setAnswers: (a: any[]) => void;
}) {
  function set(i: number, val: any) {
    const next = answers.slice();
    next[i] = val;
    setAnswers(next);
  }
  return (
    <div className="grid gap-2.5 max-h-[460px] overflow-y-auto scroll-thin">
      {questions.map((q: any, n: number) => {
        const opts: any[] = q.options ?? q.choices ?? [];
        return (
          <div key={n} className="px-2.5 py-2 rounded border border-hairline">
            <p className="text-[12px] mb-1.5">
              <span className="mono text-gold mr-1.5">{n + 1}.</span>{q.q ?? q.prompt ?? q.question}
              {q.cefr && <span className="mono text-[9px] text-warmgray ml-1.5">{q.cefr}</span>}
            </p>
            {opts.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {opts.map((o: any, k: number) => {
                  const val = typeof o === 'string' ? o : o.value ?? o.text;
                  return (
                    <button key={k} onClick={() => set(n, val)}
                      className={cls('px-2 py-1 rounded border text-[11px]',
                        answers[n] === val ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray hover:bg-ivory/5')}>
                      {val}
                    </button>
                  );
                })}
              </div>
            ) : (
              <input className="w-full bg-obsidian border border-hairline rounded px-2 py-1 text-[12px]"
                placeholder="Your answer" value={answers[n] ?? ''}
                onChange={(e) => set(n, e.target.value)} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function Result({ result }: { result: any }) {
  const weaknesses: any[] = result.weaknesses ?? [];
  const recs: any[] = result.recommendations ?? [];
  return (
    <div className="grid gap-3 max-h-[520px] overflow-y-auto scroll-thin">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Score" value={pct(result.score)} sub={`${result.correct}/${result.total}`} accent />
        <MetricCard label="Result" value={result.passed ? 'PASS' : 'REVIEW'} />
        <MetricCard label="Weak areas" value={weaknesses.length || '0'} />
      </div>
      {result.per_topic && <AreaBars title="By topic" data={result.per_topic} />}
      {weaknesses.length > 0 && (
        <div>
          <p className="mono text-[10px] uppercase text-warmgray mb-1.5">Weaknesses</p>
          <div className="flex flex-wrap gap-1.5">
            {weaknesses.map((w: any, n: number) => (
              <span key={n} className="text-[11px] text-helred bg-helred/10 rounded px-2 py-0.5 capitalize">
                {(w.topic ?? w).replace?.(/_/g, ' ') ?? w} {w.pct != null ? `· ${Math.round(w.pct * 100)}%` : ''}
              </span>
            ))}
          </div>
        </div>
      )}
      {recs.length > 0 && (
        <div>
          <p className="mono text-[10px] uppercase text-warmgray mb-1.5">Study Recommendations</p>
          <ul className="grid gap-1">
            {recs.map((r: any, n: number) => (
              <li key={n} className="flex gap-1.5 text-[12px] text-ivory/80">
                <span className="text-gold">•</span>
                {typeof r === 'string' ? r : `${r.action ?? 'Review'} — ${(r.topic ?? '').replace(/_/g, ' ')}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AreaBars({ title, data }: { title: string; data: Record<string, any> }) {
  const entries = Object.entries(data ?? {});
  if (entries.length === 0) return null;
  return (
    <Panel title={title}>
      <div className="grid gap-1">
        {entries.map(([k, v]) => {
          const p = typeof v === 'number' ? v * 100 : (v?.pct != null ? v.pct * 100 : (v?.score ?? 0));
          return (
            <div key={k} className="flex items-center gap-2">
              <span className="text-[11px] w-28 capitalize truncate">{k.replace(/_/g, ' ')}</span>
              <div className="flex-1 h-2 rounded-full bg-ivory/10 overflow-hidden">
                <div className={cls('h-full rounded-full', p >= 70 ? 'bg-helgreen' : p >= 40 ? 'bg-gold' : 'bg-helred')}
                  style={{ width: `${Math.min(100, p)}%` }} />
              </div>
              <span className="mono text-[10px] text-warmgray w-10 text-right">
                {v?.correct != null ? `${v.correct}/${v.total}` : `${Math.round(p)}`}
              </span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function pct(v: any): string {
  return typeof v === 'number' ? `${Math.round(v * 100)}%` : '—';
}
