import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { AlphabetLetter } from '../types';

interface LanguageInfo {
  name_native: string;
  alphabet: AlphabetLetter[];
  pronunciation_rules: { rule: string; detail: string }[];
}

const TYPE_COLORS: Record<string, string> = {
  vowel: 'bg-rose-50 border-rose-200',
  consonant: 'bg-sky-50 border-sky-200',
  sign: 'bg-amber-50 border-amber-200',
};

export default function Alphabet() {
  const [info, setInfo] = useState<LanguageInfo | null>(null);
  const [selected, setSelected] = useState<AlphabetLetter | null>(null);

  useEffect(() => {
    api.get<LanguageInfo>('/vocabulary/language/ru').then(setInfo).catch(() => {});
  }, []);

  const speak = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ru-RU';
    utterance.rate = 0.8;
    window.speechSynthesis.speak(utterance);
  };

  if (!info) return <div className="text-slate-400">Загрузка…</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Алфавит · The Cyrillic Alphabet</h1>

      <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-11">
        {info.alphabet.map((letter) => (
          <button
            key={letter.letter}
            onClick={() => {
              setSelected(letter);
              speak(letter.letter.split(' ')[0]);
            }}
            className={`rounded-lg border p-2 text-center transition hover:shadow ${
              TYPE_COLORS[letter.type] ?? 'bg-white border-slate-200'
            } ${selected?.letter === letter.letter ? 'ring-2 ring-brand-500' : ''}`}
            aria-label={`Letter ${letter.letter}`}
          >
            <div className="text-xl font-bold">{letter.letter.split(' ')[0]}</div>
            <div className="text-[10px] text-slate-500">{letter.translit}</div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-4xl font-bold">{selected.letter}</div>
              <div className="mt-1 text-sm text-slate-500">
                name: «{selected.name}» · {selected.ipa} · {selected.type}
              </div>
            </div>
            <button className="btn-secondary" onClick={() => speak(selected.example.word)}>
              🔊 {selected.example.word}
            </button>
          </div>
          <p className="mt-3 text-sm">{selected.note}</p>
          <p className="mt-2 text-sm text-slate-500">
            Example: <span className="font-medium text-slate-800">{selected.example.word}</span> —{' '}
            {selected.example.translation}
          </p>
        </div>
      )}

      <div className="card">
        <h2 className="font-semibold">Pronunciation rules · Правила произношения</h2>
        <dl className="mt-3 space-y-3">
          {info.pronunciation_rules.map((rule) => (
            <div key={rule.rule}>
              <dt className="text-sm font-medium">{rule.rule}</dt>
              <dd className="text-sm text-slate-500">{rule.detail}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
