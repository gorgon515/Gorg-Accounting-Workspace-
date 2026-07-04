import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import {
  SPEED_PRESETS,
  getSavedRate,
  recognizeOnce,
  saveRate,
  speak,
  speakAsync,
  speakKaraoke,
  stopSpeaking,
  stripStress,
} from '../lib/speech';

interface TextSummary {
  slug: string;
  title: string;
  title_translation: string;
  kind: string;
  cefr_level: string;
  topic: string;
  summary: string;
  sentence_count: number;
  word_count: number;
  bookmark: number | null;
}

interface GlossaryEntry {
  id: number;
  stressed: string;
  translation: string;
  part_of_speech: string;
  in_srs: boolean;
}

interface TextDetail {
  slug: string;
  title: string;
  title_translation: string;
  kind: string;
  cefr_level: string;
  summary: string;
  sentences: { ru: string; en: string }[];
  bookmark: number;
  glossary: Record<string, GlossaryEntry>;
}

interface DictationResult {
  overall_score: number;
  feedback: string[];
  target: string;
}

type Mode = 'read' | 'shadow' | 'dictation';

const KIND_ICONS: Record<string, string> = {
  story: '📖', dialogue: '💬', fairy_tale: '🏰', article: '📰', news: '🗞️',
};

function stripWord(word: string): string {
  return word.replace(/́/g, '').toLowerCase().replace(/[^а-яё-]/g, '');
}

export default function Library() {
  const [texts, setTexts] = useState<TextSummary[]>([]);
  const [cefr, setCefr] = useState('');
  const [text, setText] = useState<TextDetail | null>(null);
  const [current, setCurrent] = useState(0);
  const [mode, setMode] = useState<Mode>('read');
  const [rate, setRateState] = useState(getSavedRate());
  const [looping, setLooping] = useState(false);
  const [karaokeWord, setKaraokeWord] = useState(-1);
  const [abRange, setAbRange] = useState<[number, number] | null>(null);

  const setRate = (value: number) => {
    setRateState(value);
    saveRate(value);
  };
  const [popup, setPopup] = useState<{ word: string; entry: GlossaryEntry } | null>(null);
  const [dictationInput, setDictationInput] = useState('');
  const [dictationResult, setDictationResult] = useState<DictationResult | null>(null);
  const [shadowHeard, setShadowHeard] = useState<string | null>(null);
  const loopRef = useRef(false);

  useEffect(() => {
    const params = cefr ? `?cefr=${cefr}` : '';
    api.get<TextSummary[]>(`/library/texts${params}`).then(setTexts).catch(() => {});
  }, [cefr]);

  const openText = async (slug: string) => {
    const detail = await api.get<TextDetail>(`/library/texts/${slug}`);
    setText(detail);
    setCurrent(detail.bookmark);
    setMode('read');
    setDictationResult(null);
    setShadowHeard(null);
  };

  const saveBookmark = useCallback(
    (index: number) => {
      if (!text) return;
      api.put(`/library/texts/${text.slug}/bookmark`, { sentence_index: index }).catch(() => {});
    },
    [text],
  );

  const goTo = (index: number) => {
    if (!text) return;
    const clamped = Math.max(0, Math.min(text.sentences.length - 1, index));
    setCurrent(clamped);
    saveBookmark(clamped);
    setDictationResult(null);
    setDictationInput('');
    setShadowHeard(null);
    stopLoop();
  };

  const stopLoop = () => {
    loopRef.current = false;
    setLooping(false);
    stopSpeaking();
  };

  const startLoop = async () => {
    if (!text || looping) return;
    loopRef.current = true;
    setLooping(true);
    // A/B repeat: loop the selected sentence range; otherwise the current one.
    const [from, to] = abRange ?? [current, current];
    while (loopRef.current) {
      for (let i = from; i <= to && loopRef.current; i++) {
        setCurrent(i);
        await speakAsync(text.sentences[i].ru, rate);
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
  };

  const playKaraoke = async () => {
    if (!text) return;
    const plain = stripStress(text.sentences[current].ru);
    const words = plain.split(/\s+/);
    const offsets: number[] = [];
    let cursor = 0;
    for (const word of words) {
      offsets.push(plain.indexOf(word, cursor));
      cursor = plain.indexOf(word, cursor) + word.length;
    }
    await speakKaraoke(plain, rate, (charIndex) => {
      let index = 0;
      for (let i = 0; i < offsets.length; i++) {
        if (charIndex >= offsets[i]) index = i;
      }
      setKaraokeWord(index);
    });
    setKaraokeWord(-1);
  };

  const shadow = async () => {
    if (!text) return;
    await speakAsync(text.sentences[current].ru, rate);
    const heard = await recognizeOnce();
    setShadowHeard(heard ?? '(speech recognition unavailable — repeat aloud anyway!)');
  };

  const checkDictation = async () => {
    if (!text) return;
    const result = await api.post<DictationResult>(
      `/library/texts/${text.slug}/dictation`,
      { sentence_index: current, typed_text: dictationInput },
    );
    setDictationResult(result);
  };

  const addToSrs = async (entry: GlossaryEntry, word: string) => {
    await api.post('/library/add-word', { lexeme_id: entry.id });
    if (text) {
      setText({
        ...text,
        glossary: { ...text.glossary, [word]: { ...entry, in_srs: true } },
      });
      setPopup({ word, entry: { ...entry, in_srs: true } });
    }
  };

  // ------------------------------------------------------------ list view
  if (!text) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Библиоте́ка · Reading Library</h1>
        <div className="flex gap-2">
          {['', 'A1', 'A2', 'B1'].map((level) => (
            <button
              key={level || 'all'}
              className={`btn ${cefr === level ? 'bg-brand-600 text-white' : 'btn-secondary'}`}
              onClick={() => setCefr(level)}
            >
              {level || 'All levels'}
            </button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {texts.map((item) => (
            <button
              key={item.slug}
              className="card text-left hover:border-brand-300"
              onClick={() => openText(item.slug)}
            >
              <div className="flex items-start justify-between">
                <span className="font-medium">
                  {KIND_ICONS[item.kind] ?? '📄'} {item.title}
                </span>
                <span className="badge bg-emerald-50 text-emerald-700">{item.cefr_level}</span>
              </div>
              <div className="text-xs text-slate-400">{item.title_translation}</div>
              <p className="mt-2 text-sm text-slate-500">{item.summary}</p>
              <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                <span>{item.sentence_count} sentences</span>
                <span>{item.word_count} words</span>
                {item.bookmark !== null && item.bookmark > 0 && (
                  <span className="text-brand-600">🔖 sentence {item.bookmark + 1}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------- reader view
  const sentence = text.sentences[current];
  const words = sentence.ru.split(/\s+/);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <button className="text-sm text-brand-600 hover:underline" onClick={() => setText(null)}>
          ← Library
        </button>
        <span className="badge bg-emerald-50 text-emerald-700">{text.cefr_level}</span>
      </div>
      <h1 className="text-2xl font-bold">{text.title}</h1>
      <div className="text-sm text-slate-400">{text.title_translation}</div>

      <div className="flex flex-wrap items-center gap-2">
        {(['read', 'shadow', 'dictation'] as Mode[]).map((m) => (
          <button
            key={m}
            className={`btn ${mode === m ? 'bg-brand-600 text-white' : 'btn-secondary'}`}
            onClick={() => {
              setMode(m);
              stopLoop();
            }}
          >
            {m === 'read' ? '📖 Read' : m === 'shadow' ? '🗣️ Shadow' : '✍️ Dictation'}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1" role="group" aria-label="Playback speed">
          {SPEED_PRESETS.map((preset) => (
            <button
              key={preset.label}
              className={`badge ${Math.abs(rate - preset.rate) < 0.01
                ? 'bg-brand-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              onClick={() => setRate(preset.rate)}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span>
            Sentence {current + 1} / {text.sentences.length}
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary px-2 py-1" onClick={playKaraoke}
                    title="Play with word highlighting">
              🔊
            </button>
            <button className="btn-secondary px-2 py-1" onClick={() => speak(sentence.ru, 0.6)}
                    title="Slow playback">
              🐢
            </button>
            <button
              className={`btn-secondary px-2 py-1 ${looping ? 'border-red-400 text-red-600' : ''}`}
              onClick={looping ? stopLoop : startLoop}
              title={abRange ? `Loop sentences ${abRange[0] + 1}–${abRange[1] + 1}` : 'Loop sentence'}
            >
              {looping ? '⏹ Stop' : '🔁 Loop'}
            </button>
            <button
              className={`btn-secondary px-2 py-1 ${abRange ? 'border-brand-400 text-brand-700' : ''}`}
              onClick={() => {
                if (abRange) setAbRange(null);
                else setAbRange([current, Math.min(current + 2, text.sentences.length - 1)]);
              }}
              title="A/B repeat: loop this sentence and the next two"
            >
              {abRange ? `A·B ${abRange[0] + 1}–${abRange[1] + 1}` : 'A·B'}
            </button>
          </div>
        </div>

        {mode !== 'dictation' && (
          <p className="text-xl leading-relaxed" lang="ru">
            {words.map((word, index) => {
              const key = stripWord(word);
              const entry = text.glossary[key];
              const highlighted = index === karaokeWord;
              return (
                <span key={index}>
                  <button
                    className={`rounded transition-colors ${
                      highlighted ? 'bg-amber-200' : ''
                    } ${entry ? 'hover:bg-brand-50 hover:text-brand-700' : ''}`}
                    onClick={() => entry && setPopup({ word: key, entry })}
                    disabled={!entry}
                  >
                    {word}
                  </button>{' '}
                </span>
              );
            })}
          </p>
        )}

        {mode === 'read' && <p className="mt-3 text-sm text-slate-400">{sentence.en}</p>}

        {mode === 'shadow' && (
          <div className="mt-4 space-y-2">
            <button className="btn-primary" onClick={shadow}>
              🔊 Listen, then repeat aloud
            </button>
            {shadowHeard && (
              <div className="rounded-lg bg-slate-50 p-3 text-sm">
                <span className="text-slate-400">Heard: </span>
                {shadowHeard}
              </div>
            )}
          </div>
        )}

        {mode === 'dictation' && (
          <div className="mt-2 space-y-3">
            <button className="btn-primary" onClick={() => speak(sentence.ru, rate)}>
              🔊 Play sentence
            </button>
            <input
              className="input"
              lang="ru"
              placeholder="Напиши́те, что слы́шите…"
              value={dictationInput}
              onChange={(e) => setDictationInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && checkDictation()}
              aria-label="Dictation answer"
            />
            <button className="btn-secondary" onClick={checkDictation}>
              Проверить · Check
            </button>
            {dictationResult && (
              <div
                className={`rounded-lg p-3 text-sm ${
                  dictationResult.overall_score >= 90
                    ? 'bg-emerald-50 text-emerald-900'
                    : 'bg-amber-50 text-amber-900'
                }`}
              >
                <div className="font-medium">{dictationResult.overall_score}%</div>
                {dictationResult.overall_score < 100 && (
                  <>
                    <div className="mt-1">Target: {dictationResult.target}</div>
                    <ul className="mt-1 list-inside list-disc">
                      {dictationResult.feedback.slice(0, 4).map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <button className="btn-secondary" onClick={() => goTo(current - 1)} disabled={current === 0}>
          ← Previous
        </button>
        <button
          className="btn-primary"
          onClick={() => goTo(current + 1)}
          disabled={current === text.sentences.length - 1}
        >
          Next →
        </button>
      </div>

      {popup && (
        <div
          className="fixed inset-0 z-10 flex items-end justify-center bg-black/30 p-4 sm:items-center"
          onClick={() => setPopup(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-2xl font-bold">{popup.entry.stressed}</div>
                <div className="text-sm text-slate-500">
                  {popup.entry.translation} · {popup.entry.part_of_speech}
                </div>
              </div>
              <button className="btn-secondary px-2 py-1" onClick={() => speak(popup.entry.stressed)}>
                🔊
              </button>
            </div>
            <div className="mt-4 flex gap-2">
              {popup.entry.in_srs ? (
                <span className="badge bg-emerald-100 text-emerald-700">✓ In your review deck</span>
              ) : (
                <button className="btn-primary" onClick={() => addToSrs(popup.entry, popup.word)}>
                  + Add to reviews
                </button>
              )}
              <button className="btn-secondary" onClick={() => setPopup(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
