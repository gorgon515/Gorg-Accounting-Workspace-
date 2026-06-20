import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage, LEVELS } from './_langpicker';

// Lessons — browse the generated CEFR lesson catalog and open a full lesson.
export function Lessons() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Lessons." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const [level, setLevel] = useState('A1');
  const list = useAsync(() => helios.languageAcademy.lessons({ language: lang, level, limit: 200 }), [lang, level]);
  const [openId, setOpenId] = useState<string | null>(null);
  const lesson = useAsync(() => (openId ? helios.languageAcademy.lesson(openId) : Promise.resolve(null)), [openId]);

  const lessons: any[] = Array.isArray(list.data) ? list.data : (list.data?.lessons ?? []);

  return (
    <Page title="Lessons" subtitle="structured CEFR lessons · objectives · vocab · grammar · exercises"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <Panel title="Level">
          <div className="flex gap-1.5">
            {LEVELS.map((lv) => (
              <button key={lv} onClick={() => { setLevel(lv); setOpenId(null); }}
                className={cls('px-3 py-1.5 rounded border text-[11px] mono',
                  level === lv ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-ivory/60 hover:bg-ivory/5')}>
                {lv}
              </button>
            ))}
          </div>
        </Panel>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="Catalog" subtitle={`${lessons.length} lessons · ${lang} ${level}`}>
            {list.loading ? <Loading /> : lessons.length === 0 ? (
              <EmptyState message="No lessons for this selection." />
            ) : (
              <div className="grid gap-1.5 max-h-[520px] overflow-y-auto scroll-thin">
                {lessons.map((l: any) => (
                  <div key={l.id}
                    className={cls('flex items-center gap-2 px-2.5 py-2 rounded border cursor-pointer hover:bg-ivory/5',
                      openId === l.id ? 'border-gold/40 bg-gold/5' : 'border-hairline')}
                    onClick={() => setOpenId(l.id)}>
                    <span className="mono text-[10px] text-gold w-8">{l.level}</span>
                    <span className="text-[12px] flex-1 truncate">{l.title}</span>
                    <span className="mono text-[10px] text-warmgray capitalize">{l.topic}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title={lesson.data?.title ?? 'Lesson'} subtitle={openId ? `${lesson.data?.level ?? ''} · ${lesson.data?.topic ?? ''}` : 'select a lesson'}>
            {!openId ? <EmptyState message="Select a lesson to study." />
              : lesson.loading ? <Loading /> : !lesson.data ? <EmptyState message="Lesson unavailable." />
                : <LessonBody l={lesson.data} />}
          </Panel>
        </div>
      </div>
    </Page>
  );
}

function LessonBody({ l }: { l: any }) {
  return (
    <div className="grid gap-3 max-h-[520px] overflow-y-auto scroll-thin">
      <Block title="Objectives">
        <ul className="grid gap-1">
          {(l.objectives ?? []).map((o: string, n: number) => (
            <li key={n} className="text-[12px] text-ivory/80 flex gap-1.5"><span className="text-gold">•</span>{o}</li>
          ))}
        </ul>
      </Block>

      {(l.vocabulary ?? []).length > 0 && (
        <Block title="Vocabulary">
          <div className="grid grid-cols-2 gap-1">
            {(l.vocabulary ?? []).slice(0, 12).map((v: any, n: number) => (
              <div key={n} className="flex items-center justify-between text-[11px] px-1.5 py-1 rounded bg-ivory/5">
                <span className="text-ivory/80">{v.translation ?? v.word}</span>
                <span className="text-warmgray">{v.word ?? v.translation}</span>
              </div>
            ))}
          </div>
        </Block>
      )}

      {l.grammar && (
        <Block title={`Grammar — ${l.grammar.title ?? ''}`}>
          <p className="text-[12px] text-ivory/80">{l.grammar.explanation}</p>
          {(l.grammar.examples ?? []).slice(0, 3).map((e: any, n: number) => (
            <p key={n} className="mono text-[11px] text-warmgray mt-1">› {typeof e === 'string' ? e : e.text ?? ''}</p>
          ))}
        </Block>
      )}

      {l.reading && (
        <Block title="Reading">
          <p className="text-[12px] text-ivory/80 leading-relaxed">{l.reading.passage ?? l.reading}</p>
        </Block>
      )}

      {l.listening_script && (
        <Block title="Listening script"><p className="text-[12px] text-ivory/70 italic">{l.listening_script}</p></Block>
      )}

      {(l.exercises ?? []).length > 0 && (
        <Block title="Exercises">
          <div className="grid gap-1.5">
            {(l.exercises ?? []).map((ex: any, n: number) => (
              <div key={n} className="text-[11px] px-2 py-1.5 rounded border border-hairline">
                <span className="mono text-[9px] uppercase text-gold mr-1.5">{ex.type}</span>
                <span className="text-ivory/80">{ex.prompt}</span>
                {ex.answer != null && <span className="text-warmgray"> — {String(ex.answer)}</span>}
              </div>
            ))}
          </div>
        </Block>
      )}
    </div>
  );
}

function Block({ title, children }: { title: string; children: any }) {
  return (
    <div>
      <p className="mono text-[10px] uppercase tracking-wider text-warmgray mb-1.5">{title}</p>
      {children}
    </div>
  );
}
