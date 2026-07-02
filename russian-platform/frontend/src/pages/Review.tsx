import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { useAuth } from '../App';
import { t } from '../lib/i18n';
import type { ReviewCard } from '../types';

function speak(text: string) {
  const u = new SpeechSynthesisUtterance(text.replace(/́/g, ''));
  u.lang = 'ru-RU';
  u.rate = 0.85;
  window.speechSynthesis.speak(u);
}

export default function Review() {
  const [queue, setQueue] = useState<ReviewCard[]>([]);
  const [totalDue, setTotalDue] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [done, setDone] = useState(0);
  const { user, refreshUser } = useAuth();
  const ratio = user?.ui_immersion_ratio ?? 0;

  const load = useCallback(() => {
    api
      .get<{ total_due: number; cards: ReviewCard[] }>('/reviews/queue')
      .then((r) => {
        setQueue(r.cards);
        setTotalDue(r.total_due);
      })
      .catch(() => {});
  }, []);

  useEffect(load, [load]);

  const card = queue[0];

  const rate = async (rating: number) => {
    if (!card) return;
    setRevealed(false);
    await api.post(`/reviews/${card.card_id}`, { rating });
    setDone((d) => d + 1);
    if (queue.length <= 1) {
      load();
      refreshUser();
    } else {
      setQueue((q) => q.slice(1));
      setTotalDue((n) => n - 1);
    }
  };

  if (!card) {
    return (
      <div className="mx-auto max-w-xl space-y-4 text-center">
        <h1 className="text-2xl font-bold">Повторение · {t('review', ratio)}</h1>
        <div className="card">
          <div className="text-5xl">🎉</div>
          <p className="mt-3 font-medium">
            {done > 0 ? `Great session — ${done} cards reviewed!` : 'Nothing due right now.'}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            New words join the queue when you pass lessons.
          </p>
          <Link to="/lessons" className="btn-primary mt-4">
            {t('lessons', ratio)} →
          </Link>
        </div>
      </div>
    );
  }

  const lexeme = card.lexeme;

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">Повторение · {t('review', ratio)}</h1>
        <span className="text-sm text-slate-500">
          {totalDue} {t('due_now', ratio)}
        </span>
      </div>

      <div className="card min-h-[280px] text-center">
        <div className="text-xs uppercase tracking-wide text-slate-400">{card.state}</div>
        <button className="mt-6 text-4xl font-bold hover:text-brand-700" onClick={() => speak(lexeme.lemma)}>
          {lexeme.stressed} 🔊
        </button>
        <div className="mt-1 text-sm text-slate-400">{lexeme.ipa}</div>

        {revealed ? (
          <div className="mt-6 space-y-3 border-t border-slate-100 pt-4 text-left">
            <div className="text-center text-xl font-semibold text-brand-700">{lexeme.translation}</div>
            <div className="text-center text-sm text-slate-400">
              {lexeme.transliteration} · {lexeme.part_of_speech}
            </div>
            {lexeme.mnemonic && (
              <div className="rounded-lg bg-violet-50 p-2 text-sm text-violet-900">💡 {lexeme.mnemonic}</div>
            )}
            {lexeme.examples.map((example) => (
              <div key={example.text} className="text-sm">
                <div>{example.text}</div>
                <div className="text-slate-400">{example.translation}</div>
              </div>
            ))}
          </div>
        ) : (
          <button className="btn-secondary mt-8" onClick={() => setRevealed(true)}>
            {t('show_answer', ratio)}
          </button>
        )}
      </div>

      {revealed && (
        <div className="grid grid-cols-4 gap-2">
          <button className="btn bg-red-100 text-red-700 hover:bg-red-200" onClick={() => rate(1)}>
            {t('again', ratio)}
          </button>
          <button className="btn bg-amber-100 text-amber-700 hover:bg-amber-200" onClick={() => rate(2)}>
            {t('hard', ratio)}
          </button>
          <button className="btn bg-emerald-100 text-emerald-700 hover:bg-emerald-200" onClick={() => rate(3)}>
            {t('good', ratio)}
          </button>
          <button className="btn bg-sky-100 text-sky-700 hover:bg-sky-200" onClick={() => rate(4)}>
            {t('easy', ratio)}
          </button>
        </div>
      )}
    </div>
  );
}
