import { useState } from 'react';
import { Page } from './_page';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage } from './_langpicker';

// Pronunciation Lab — score an attempt against a target phrase across accuracy,
// fluency, clarity and intonation, with targeted drills.
export function PronunciationLab() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Pronunciation Lab." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const [target, setTarget] = useState('');
  const [attempt, setAttempt] = useState('');
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function score() {
    if (!target.trim() || !attempt.trim()) return;
    setBusy(true);
    try { setResult(await helios.languageAcademy.pronunciation({ language: lang, target, attempt })); }
    finally { setBusy(false); }
  }

  return (
    <Page title="Pronunciation Lab" subtitle="accuracy · fluency · clarity · intonation"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <Panel title="Score an Attempt">
          <div className="grid gap-2">
            <input className="bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
              placeholder="Target phrase (what should be said)" value={target} onChange={(e) => setTarget(e.target.value)} />
            <input className="bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
              placeholder="Your attempt (transcribed)" value={attempt} onChange={(e) => setAttempt(e.target.value)} />
            <Button variant="gold" onClick={score} disabled={busy}>{busy ? 'Scoring…' : 'Score Pronunciation'}</Button>
          </div>
        </Panel>

        {result && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <MetricCard label="Overall" value={fmt(result.overall ?? result.score)} accent />
              <MetricCard label="Accuracy" value={fmt(result.accuracy)} />
              <MetricCard label="Fluency" value={fmt(result.fluency)} />
              <MetricCard label="Clarity" value={fmt(result.clarity)} />
              <MetricCard label="Intonation" value={fmt(result.intonation)} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <Panel title="Corrections">
                {(result.corrections ?? []).length === 0 ? (
                  <p className="text-[12px] text-helgreen">✓ Clean — no word-level differences.</p>
                ) : (
                  <div className="grid gap-1.5">
                    {(result.corrections ?? []).map((c: any, n: number) => (
                      <div key={n} className="text-[12px] px-2 py-1.5 rounded border border-hairline">
                        {typeof c === 'string' ? c : (
                          <>
                            <span className="text-helred line-through">{c.expected ?? c.target ?? c.wrong}</span>
                            <span className="text-warmgray mx-1.5">→</span>
                            <span className="text-helgreen">{c.got ?? c.attempt ?? c.right}</span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {result.feedback && <p className="text-[11px] text-warmgray mt-2">{result.feedback}</p>}
              </Panel>

              <Panel title="Practice Drills">
                {(result.drills ?? []).length === 0 ? (
                  <EmptyState message="No drills — keep practicing." />
                ) : (
                  <ul className="grid gap-1.5">
                    {(result.drills ?? []).map((d: any, n: number) => (
                      <li key={n} className="flex gap-1.5 text-[12px] text-ivory/80">
                        <span className="text-gold">•</span>{typeof d === 'string' ? d : d.text ?? JSON.stringify(d)}
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </>
        )}
      </div>
    </Page>
  );
}

function fmt(v: any): string {
  return typeof v === 'number' ? `${Math.round(v)}` : '—';
}
