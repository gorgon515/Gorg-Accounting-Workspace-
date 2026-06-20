import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage } from './_langpicker';

// Vocabulary — browse the topic-organized bank and drill due cards with SRS.
export function Vocabulary() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for Vocabulary." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const topics = useAsync(() => helios.languageAcademy.vocabTopics(), []);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const words = useAsync(() => helios.languageAcademy.vocabulary({ language: lang, topic, limit: 100 }), [lang, topic]);

  const topicList: Array<[string, number]> = Array.isArray(topics.data)
    ? topics.data.map((t: any) => [t.topic ?? t.name ?? t, t.count ?? 0])
    : Object.entries(topics.data ?? {});
  const list: any[] = Array.isArray(words.data) ? words.data : (words.data?.words ?? []);

  return (
    <Page title="Vocabulary" subtitle="topic-organized bank · spaced repetition"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <SrsDrill lang={lang} />

        <Panel title="Topics">
          <div className="flex flex-wrap gap-1.5">
            <button onClick={() => setTopic(undefined)}
              className={cls('px-2.5 py-1 rounded border text-[11px] mono',
                !topic ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray hover:bg-ivory/5')}>all</button>
            {topicList.map(([t, n]) => (
              <button key={t} onClick={() => setTopic(t)}
                className={cls('px-2.5 py-1 rounded border text-[11px] mono capitalize',
                  topic === t ? 'border-gold/40 bg-gold/10 text-gold' : 'border-hairline text-warmgray hover:bg-ivory/5')}>
                {t.replace(/_/g, ' ')} <span className="text-warmgray">{n}</span>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Words" subtitle={`${list.length} · ${lang}${topic ? ' · ' + topic : ''}`}>
          {words.loading ? <Loading /> : list.length === 0 ? (
            <EmptyState message="No vocabulary for this selection." />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 max-h-[460px] overflow-y-auto scroll-thin">
              {list.map((w: any, n: number) => (
                <div key={n} className="px-2.5 py-2 rounded border border-hairline">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] text-gold">{w.translation ?? w.word}</span>
                    <span className="text-[12px] text-warmgray">{w.word ?? ''}</span>
                    {w.pos && <span className="mono text-[9px] text-ivory/40 ml-auto">{w.pos}</span>}
                    {w.cefr && <span className="mono text-[9px] text-warmgray">{w.cefr}</span>}
                  </div>
                  {w.example && <p className="text-[10px] text-warmgray mt-0.5 italic">{w.example}</p>}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

function SrsDrill({ lang }: { lang: string }) {
  const cards = useAsync(() => helios.languageAcademy.review({ language: lang, limit: 20 }), [lang]);
  const [idx, setIdx] = useState(0);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const list: any[] = Array.isArray(cards.data) ? cards.data : (cards.data?.cards ?? []);
  const card = list[idx];

  async function grade(g: number) {
    if (!card) return;
    setBusy(true);
    try { await helios.languageAcademy.grade({ card_id: card.card_id ?? card.id, grade: g }); }
    catch { /* offline */ }
    finally {
      setBusy(false); setShow(false);
      if (idx + 1 >= list.length) { setIdx(0); cards.reload(); } else setIdx(idx + 1);
    }
  }

  return (
    <Panel title="Review (SRS)" subtitle={list.length ? `${idx + 1} / ${list.length} due` : 'spaced repetition'}>
      {cards.loading ? <Loading /> : !card ? (
        <EmptyState message="No cards due — come back later or browse topics below." />
      ) : (
        <div className="grid gap-3">
          <div className="rounded-xl border border-hairline p-6 text-center cursor-pointer hover:bg-ivory/5"
            onClick={() => setShow(!show)}>
            <p className="text-[20px] text-gold">{card.translation ?? card.word ?? card.headword}</p>
            <p className={cls('text-[15px] mt-2 transition-opacity', show ? 'opacity-100 text-ivory' : 'opacity-0')}>
              {card.word ?? card.headword ?? card.answer ?? '—'}
            </p>
            {!show && <p className="mono text-[10px] text-warmgray mt-3">tap to reveal</p>}
          </div>
          {show && (
            <div className="grid grid-cols-4 gap-1.5">
              <Button size="sm" variant="danger" onClick={() => grade(1)} disabled={busy}>Again</Button>
              <Button size="sm" variant="ghost" onClick={() => grade(3)} disabled={busy}>Hard</Button>
              <Button size="sm" variant="ghost" onClick={() => grade(4)} disabled={busy}>Good</Button>
              <Button size="sm" variant="gold" onClick={() => grade(5)} disabled={busy}>Easy</Button>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
