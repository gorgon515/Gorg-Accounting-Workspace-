import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '../api/client';

interface LessonData {
  slug: string;
  title: string;
  objectives: string[];
  blocks: Record<string, any>[];
  vocabulary: { id: number; lemma: string; stressed: string; translation: string; transliteration: string }[];
  grammar_slugs: string[];
  mastery_threshold: number;
}

interface CompletionResult {
  score: number;
  passed: boolean;
  threshold: number;
  results: { id: string; correct: boolean; expected: string; submitted: string }[];
  new_srs_cards: number;
  achievements: { slug: string; title: string; icon: string }[];
}

function speak(text: string) {
  const u = new SpeechSynthesisUtterance(text.replace(/́/g, ''));
  u.lang = 'ru-RU';
  u.rate = 0.85;
  window.speechSynthesis.speak(u);
}

export default function LessonPlayer() {
  const { slug } = useParams<{ slug: string }>();
  const [lesson, setLesson] = useState<LessonData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<CompletionResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!slug) return;
    api.get<LessonData>(`/lessons/${slug}`).then(setLesson).catch((e) => setError(e.message));
  }, [slug]);

  const submit = async () => {
    if (!slug) return;
    setBusy(true);
    try {
      setResult(await api.post<CompletionResult>(`/lessons/${slug}/complete`, { answers }));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Submission failed');
    } finally {
      setBusy(false);
    }
  };

  if (error) return <div className="card text-red-600">{error}</div>;
  if (!lesson) return <div className="text-slate-400">Загрузка…</div>;

  const verdictFor = (id: string) => result?.results.find((r) => r.id === id);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/lessons" className="text-sm text-brand-600 hover:underline">
        ← All lessons
      </Link>
      <h1 className="text-2xl font-bold">{lesson.title}</h1>
      <ul className="text-sm text-slate-500">
        {lesson.objectives.map((objective) => (
          <li key={objective}>🎯 {objective}</li>
        ))}
      </ul>

      {result && (
        <div
          className={`card ${result.passed ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'}`}
        >
          <div className="text-lg font-semibold">
            {result.passed ? '🎉 Пройдено! Passed' : 'Not yet — try again'} ·{' '}
            {Math.round(result.score * 100)}% (need {Math.round(result.threshold * 100)}%)
          </div>
          {result.passed && result.new_srs_cards > 0 && (
            <p className="mt-1 text-sm">
              {result.new_srs_cards} new words added to your review queue.{' '}
              <Link to="/review" className="text-brand-600 underline">
                Review now →
              </Link>
            </p>
          )}
          {result.achievements.map((a) => (
            <span key={a.slug} className="badge mt-2 mr-2 bg-amber-100 text-amber-800">
              {a.icon} {a.title}
            </span>
          ))}
        </div>
      )}

      {lesson.vocabulary.length > 0 && (
        <div className="card">
          <h2 className="font-semibold">Новые слова · New words</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {lesson.vocabulary.map((word) => (
              <div key={word.id} className="flex items-center justify-between rounded-lg bg-slate-50 p-2">
                <div>
                  <div className="font-medium">{word.stressed}</div>
                  <div className="text-xs text-slate-500">
                    {word.transliteration} — {word.translation}
                  </div>
                </div>
                <button className="btn-secondary px-2 py-1" onClick={() => speak(word.lemma)}>
                  🔊
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {lesson.blocks.map((block, index) => {
        switch (block.type) {
          case 'grammar_ref':
            return (
              <div key={index} className="card border-brand-200 bg-brand-50">
                📘 Grammar for this lesson:{' '}
                <Link to={`/grammar/${block.slug}`} className="font-medium text-brand-700 underline">
                  {String(block.slug).replace(/-/g, ' ')}
                </Link>
              </div>
            );
          case 'reading':
            return (
              <div key={index} className="card">
                <h2 className="font-semibold">📖 {String(block.title)}</h2>
                <p className="mt-2 text-lg leading-relaxed">{String(block.text)}</p>
                <button className="btn-secondary mt-2" onClick={() => speak(String(block.text))}>
                  🔊 Listen
                </button>
                <p className="mt-2 text-sm text-slate-400">{String(block.translation)}</p>
              </div>
            );
          case 'dialogue':
            return (
              <div key={index} className="card">
                <h2 className="font-semibold">💬 {String(block.title)}</h2>
                <div className="mt-3 space-y-2">
                  {(block.lines as { speaker: string; text: string; translation: string }[]).map(
                    (line, li) => (
                      <div key={li} className="flex items-start gap-3">
                        <span className="w-20 shrink-0 text-xs font-medium text-slate-400">
                          {line.speaker}
                        </span>
                        <div className="flex-1">
                          <button
                            className="text-left hover:text-brand-700"
                            onClick={() => speak(line.text)}
                            title="Click to listen"
                          >
                            {line.text}
                          </button>
                          <div className="text-xs text-slate-400">{line.translation}</div>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>
            );
          case 'culture':
            return (
              <div key={index} className="card border-amber-200 bg-amber-50">
                <h2 className="font-semibold">🏛️ {String(block.title)}</h2>
                <p className="mt-2 text-sm">{String(block.body)}</p>
              </div>
            );
          case 'exercise':
          case 'mastery_test': {
            const isTest = block.type === 'mastery_test';
            return (
              <div key={index} className={`card ${isTest ? 'border-violet-300' : ''}`}>
                <h2 className="font-semibold">{isTest ? '🏆 Mastery test' : '✏️ Practice'}</h2>
                <div className="mt-3 space-y-3">
                  {(block.questions as { id: string; prompt: string }[]).map((q) => {
                    const verdict = verdictFor(q.id);
                    return (
                      <div key={q.id}>
                        <label className="text-sm" htmlFor={q.id}>
                          {q.prompt}
                        </label>
                        <input
                          id={q.id}
                          className={`input mt-1 ${
                            verdict ? (verdict.correct ? 'border-emerald-400' : 'border-red-400') : ''
                          }`}
                          value={answers[q.id] ?? ''}
                          onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                          lang="ru"
                          autoComplete="off"
                        />
                        {verdict && !verdict.correct && (
                          <div className="mt-1 text-xs text-red-600">Correct: {verdict.expected}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }
          default:
            return null;
        }
      })}

      <button className="btn-primary w-full" onClick={submit} disabled={busy}>
        {busy ? '…' : 'Проверить · Check & complete lesson'}
      </button>
    </div>
  );
}
