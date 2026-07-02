import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { LexemeDetail, LexemeSummary } from '../types';

export default function Vocabulary() {
  const [query, setQuery] = useState('');
  const [pos, setPos] = useState('');
  const [items, setItems] = useState<LexemeSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<LexemeDetail | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (pos) params.set('pos', pos);
    const handle = setTimeout(() => {
      api
        .get<{ total: number; items: LexemeSummary[] }>(`/vocabulary?${params}`)
        .then((r) => {
          setItems(r.items);
          setTotal(r.total);
        })
        .catch(() => {});
    }, 200);
    return () => clearTimeout(handle);
  }, [query, pos]);

  const openDetail = (id: number) =>
    api.get<LexemeDetail>(`/vocabulary/${id}`).then(setDetail).catch(() => {});

  const speak = (text: string) => {
    const u = new SpeechSynthesisUtterance(text.replace(/́/g, ''));
    u.lang = 'ru-RU';
    u.rate = 0.85;
    window.speechSynthesis.speak(u);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Словарь · Vocabulary</h1>
      <div className="flex gap-3">
        <input
          className="input max-w-md"
          placeholder="Search Russian or English… (вода / water)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search vocabulary"
        />
        <select className="input w-44" value={pos} onChange={(e) => setPos(e.target.value)} aria-label="Part of speech">
          <option value="">All parts of speech</option>
          {['noun', 'verb', 'adjective', 'adverb', 'pronoun', 'numeral', 'preposition', 'conjunction', 'particle', 'phrase'].map(
            (p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ),
          )}
        </select>
      </div>
      <div className="text-xs text-slate-400">{total} entries</div>

      <div className="grid gap-2">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => openDetail(item.id)}
            className="card flex items-center justify-between py-3 text-left hover:border-brand-300"
          >
            <div>
              <span className="text-lg font-semibold">{item.stressed}</span>
              <span className="ml-3 text-sm text-slate-500">{item.translation}</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="badge bg-slate-100 text-slate-600">{item.part_of_speech}</span>
              <span className="badge bg-emerald-50 text-emerald-700">{item.cefr_level}</span>
              {item.frequency_rank && (
                <span className="badge bg-brand-50 text-brand-700">#{item.frequency_rank}</span>
              )}
            </div>
          </button>
        ))}
      </div>

      {detail && (
        <div
          className="fixed inset-0 z-10 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setDetail(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold">{detail.stressed}</div>
                <div className="mt-1 text-sm text-slate-500">
                  {detail.ipa} · {detail.transliteration} · {detail.part_of_speech}
                  {detail.gender && ` · ${detail.gender}.`}
                  {detail.aspect && ` · ${detail.aspect}`}
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn-secondary" onClick={() => speak(detail.lemma)}>
                  🔊
                </button>
                <button className="btn-secondary" onClick={() => setDetail(null)} aria-label="Close">
                  ✕
                </button>
              </div>
            </div>

            <div className="mt-4 space-y-4 text-sm">
              <div>
                <span className="font-semibold">{detail.translation}</span>
                {detail.literal_translation && (
                  <span className="ml-2 text-slate-400">lit. “{detail.literal_translation}”</span>
                )}
              </div>
              {detail.aspect_partner && (
                <div>
                  <span className="text-slate-400">Aspect partner:</span> {detail.aspect_partner}
                </div>
              )}
              {Object.entries(detail.inflections).map(([table, forms]) => (
                <div key={table}>
                  <div className="mb-1 font-medium capitalize text-slate-600">{table}</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(forms).map(([k, v]) => (
                      <span key={k} className="badge bg-slate-100 text-slate-700">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {detail.mnemonic && (
                <div className="rounded-lg bg-violet-50 p-3 text-violet-900">💡 {detail.mnemonic}</div>
              )}
              {detail.usage_notes && (
                <div className="rounded-lg bg-sky-50 p-3 text-sky-900">ℹ️ {detail.usage_notes}</div>
              )}
              {detail.cultural_notes && (
                <div className="rounded-lg bg-amber-50 p-3 text-amber-900">🏛️ {detail.cultural_notes}</div>
              )}
              {detail.common_mistakes.length > 0 && (
                <div className="rounded-lg bg-red-50 p-3 text-red-900">
                  ⚠️ {detail.common_mistakes.join(' · ')}
                </div>
              )}
              {detail.examples.length > 0 && (
                <div>
                  <div className="mb-1 font-medium text-slate-600">Examples</div>
                  <ul className="space-y-2">
                    {detail.examples.map((ex) => (
                      <li key={ex.text} className="flex items-start justify-between gap-2">
                        <div>
                          <div>{ex.text}</div>
                          <div className="text-slate-400">{ex.translation}</div>
                        </div>
                        <button className="btn-secondary shrink-0 px-2 py-1" onClick={() => speak(ex.text)}>
                          🔊
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.relations.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {detail.relations.map((rel) => (
                    <span key={`${rel.type}-${rel.target}`} className="badge bg-slate-100 text-slate-600">
                      {rel.type}: {rel.target}
                      {rel.note ? ` (${rel.note})` : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
