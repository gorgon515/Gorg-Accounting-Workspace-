import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '../api/client';

interface TopicDetail {
  slug: string;
  title: string;
  title_native: string;
  cefr_level: string;
  summary: string;
  content: { type: string; title: string; body: string }[];
  drills: { id: string; prompt: string }[];
  prerequisites: string[];
  mastery: number;
}

interface DrillResult {
  results: { id: string; correct: boolean; expected: string; explanation: string }[];
  mastery: number;
}

/** Minimal markdown: bold, tables, and paragraphs (content is trusted seed data). */
function Markdown({ body }: { body: string }) {
  const paragraphs = body.split('\n\n');
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {paragraphs.map((paragraph, index) => {
        if (paragraph.trimStart().startsWith('|')) {
          const rows = paragraph.trim().split('\n').filter((r) => !/^\|[\s\-|]+\|$/.test(r));
          return (
            <table key={index} className="w-full border-collapse text-left">
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri} className={ri === 0 ? 'border-b border-slate-300 font-medium' : 'border-b border-slate-100'}>
                    {row.split('|').filter(Boolean).map((cell, ci) => (
                      <td key={ci} className="px-2 py-1.5">
                        <Bold text={cell.trim()} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        }
        return (
          <p key={index}>
            <Bold text={paragraph} />
          </p>
        );
      })}
    </div>
  );
}

function Bold({ text }: { text: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 ? <strong key={index}>{part}</strong> : <span key={index}>{part}</span>,
      )}
    </>
  );
}

export default function GrammarTopicPage() {
  const { slug } = useParams<{ slug: string }>();
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<DrillResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setTopic(null);
    setResult(null);
    setAnswers({});
    api.get<TopicDetail>(`/grammar/topics/${slug}`).then(setTopic).catch(() => {});
  }, [slug]);

  const submit = async () => {
    if (!slug) return;
    setBusy(true);
    try {
      setResult(await api.post<DrillResult>(`/grammar/topics/${slug}/drills`, { answers }));
    } finally {
      setBusy(false);
    }
  };

  if (!topic) return <div className="text-slate-400">Загрузка…</div>;

  const verdictFor = (id: string) => result?.results.find((r) => r.id === id);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/grammar" className="text-sm text-brand-600 hover:underline">
        ← Grammar encyclopedia
      </Link>
      <div>
        <h1 className="text-2xl font-bold">{topic.title}</h1>
        <div className="mt-1 text-sm text-slate-400">
          {topic.title_native} · {topic.cefr_level}
          {topic.mastery > 0 && ` · mastery ${Math.round(topic.mastery * 100)}%`}
        </div>
      </div>

      {topic.prerequisites.length > 0 && (
        <div className="text-xs text-slate-500">
          Prerequisites:{' '}
          {topic.prerequisites.map((prerequisite, index) => (
            <span key={prerequisite}>
              {index > 0 && ' · '}
              <Link className="text-brand-600 hover:underline" to={`/grammar/${prerequisite}`}>
                {prerequisite.replace(/-/g, ' ')}
              </Link>
            </span>
          ))}
        </div>
      )}

      {topic.content.length === 0 ? (
        <div className="card bg-slate-50 text-sm text-slate-600">
          <p className="font-medium">{topic.summary}</p>
          <p className="mt-2">
            This topic is part of the full curriculum; its interactive content ships in an upcoming
            content sprint. The catalog position, prerequisites, and mastery tracking are already live.
          </p>
        </div>
      ) : (
        topic.content.map((section) => (
          <div key={section.title} className="card">
            <h2 className="mb-2 font-semibold">{section.title}</h2>
            <Markdown body={section.body} />
          </div>
        ))
      )}

      {topic.drills.length > 0 && (
        <div className="card border-violet-200">
          <h2 className="font-semibold">✏️ Drills</h2>
          {result && (
            <div className="mt-2 rounded-lg bg-violet-50 p-2 text-sm text-violet-900">
              {result.results.filter((r) => r.correct).length}/{result.results.length} correct ·
              mastery {Math.round(result.mastery * 100)}%
            </div>
          )}
          <div className="mt-3 space-y-3">
            {topic.drills.map((drill) => {
              const verdict = verdictFor(drill.id);
              return (
                <div key={drill.id}>
                  <label className="text-sm" htmlFor={drill.id}>
                    {drill.prompt}
                  </label>
                  <input
                    id={drill.id}
                    className={`input mt-1 ${
                      verdict ? (verdict.correct ? 'border-emerald-400' : 'border-red-400') : ''
                    }`}
                    value={answers[drill.id] ?? ''}
                    onChange={(e) => setAnswers({ ...answers, [drill.id]: e.target.value })}
                    lang="ru"
                    autoComplete="off"
                  />
                  {verdict && !verdict.correct && (
                    <div className="mt-1 text-xs text-red-600">
                      Correct: {verdict.expected}
                      {verdict.explanation && ` — ${verdict.explanation}`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <button className="btn-primary mt-4" onClick={submit} disabled={busy}>
            {busy ? '…' : 'Проверить · Check'}
          </button>
        </div>
      )}
    </div>
  );
}
