import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

export function Language() {
  const [lang, setLang] = useState<string | undefined>(undefined);
  const langs = useAsync(() => helios.language.languages(), []);
  const prof = useAsync(() => helios.language.profile(), []);
  const active = lang || prof.data?.language;

  const prog = useAsync(() => helios.language.progress(active), [active]);
  const miss = useAsync(() => helios.language.missions(active), [active]);
  const path = useAsync(() => helios.language.curriculum(), []);

  const [word, setWord] = useState(''); const [tr, setTr] = useState('');

  async function pick(code: string) {
    setLang(code);
    try { await helios.language.setLanguage({ language: code }); } catch { /* offline */ }
  }
  async function complete(id: string) {
    try { await helios.language.completeMission({ id, language: active }); miss.reload(); prog.reload(); } catch { /* */ }
  }
  async function addVocab() {
    if (!word.trim() || !tr.trim()) return;
    try { await helios.language.addVocab({ language: active, word, translation: tr }); setWord(''); setTr(''); prog.reload(); } catch { /* */ }
  }

  return (
    <Page title="Language Immersion" subtitle="seven languages · SRS · daily missions · CEFR pathway"
      actions={
        <div className="flex gap-1 flex-wrap justify-end">
          {(langs.data ?? []).map((l) => (
            <Button key={l.code} size="sm" variant={l.code === active ? 'primary' : 'ghost'} onClick={() => pick(l.code)}>
              {l.flag} {l.name}
            </Button>
          ))}
        </div>
      }>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Language" accent value={prog.data ? `${prog.data.flag} ${prog.data.name}` : '—'} sub={prog.data?.native} />
        <MetricCard label="Estimated level" value={prog.data ? `~${prog.data.estimatedLevel}` : '—'} sub={prog.data ? `self ${prog.data.selfLevel}` : ''} />
        <MetricCard label="Vocabulary" value={prog.data?.words ?? '—'} sub={`${prog.data?.dueNow ?? 0} due`} />
        <MetricCard label="Streak" value={prog.data?.streakDays ?? '—'} sub="days" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Today's missions" subtitle={prog.data ? `${prog.data.missionsDoneToday}/${prog.data.missionsToday} done` : ''}>
          {miss.loading ? <Loading /> : miss.error ? <EmptyState message="Lives in the desktop app." />
            : (miss.data?.missions ?? []).map((m) => (
              <div key={m.id} className={cls('flex items-center gap-2.5 py-2 border-b border-hairline', m.done && 'opacity-50')}>
                <button onClick={() => complete(m.id)}
                  className={cls('w-5 h-5 rounded-full border shrink-0 flex items-center justify-center text-[10px]',
                    m.done ? 'border-helgreen text-helgreen' : 'border-hairline')}>{m.done ? '✓' : ''}</button>
                <span className="mono text-[9px] uppercase text-gold w-16 shrink-0">{m.kind}</span>
                <span className={cls('text-[12px] flex-1', m.done && 'line-through')}>{m.text}</span>
              </div>
            ))}
        </Panel>

        <div className="flex flex-col gap-3">
          <Panel title="Add vocabulary" subtitle="enters spaced-repetition review">
            <div className="flex flex-col gap-2">
              <input value={word} onChange={(e) => setWord(e.target.value)} placeholder="Word / phrase"
                className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
              <input value={tr} onChange={(e) => setTr(e.target.value)} placeholder="Translation"
                className="bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[12px] outline-none focus:border-gold/40" />
              <Button variant="gold" onClick={addVocab}>Add card</Button>
            </div>
          </Panel>
          <Panel title="CEFR pathway" scroll className="max-h-[220px]">
            {(path.data ?? []).map((lv) => (
              <div key={lv.level} className="flex gap-2 py-1.5 border-b border-hairline">
                <span className="mono text-[11px] text-gold w-7">{lv.level}</span>
                <div className="text-[12px]"><b>{lv.label}</b>
                  <span className="text-warmgray"> — {lv.goals.join(' · ')}</span></div>
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </Page>
  );
}
