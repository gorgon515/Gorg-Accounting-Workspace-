import { useEffect, useState } from 'react';

import { api } from '../api/client';

interface WritingPrompt {
  kind: string;
  prompt: string;
}

interface Analysis {
  word_count: number;
  sentence_count: number;
  avg_sentence_length: number;
  dictionary_coverage: number;
  unknown_words: { word: string; suggestion: string | null }[];
  repetition: { lemma: string; count: number; synonyms: string[] }[];
  register_notes: string[];
  structure_notes: string[];
  srs_candidates: { lexeme_id: number; lemma: string; translation: string }[];
  llm_corrections: { error: string; correction: string; explanation: string }[];
  llm_feedback_available: boolean;
}

interface History {
  submissions: { id: number; prompt: string; word_count: number;
                 quality_score: number | null; created_at: string }[];
  recurring_mistakes: { word: string; times: number }[];
  total_words_written: number;
}

export default function Writing() {
  const [prompts, setPrompts] = useState<WritingPrompt[]>([]);
  const [kind, setKind] = useState('journal');
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState<Set<number>>(new Set());

  const loadHistory = () =>
    api.get<History>('/writing/history').then(setHistory).catch(() => {});

  useEffect(() => {
    api.get<WritingPrompt[]>('/writing/prompts').then(setPrompts).catch(() => {});
    loadHistory();
  }, []);

  const activePrompt = prompts.find((p) => p.kind === kind)?.prompt ?? '';

  const analyze = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      setAnalysis(await api.post<Analysis>('/writing/analyze', { kind, text }));
      loadHistory();
    } finally {
      setBusy(false);
    }
  };

  const addToSrs = async (lexemeId: number) => {
    await api.post('/library/add-word', { lexeme_id: lexemeId });
    setAdded(new Set([...added, lexemeId]));
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Письмо́ · Writing Coach</h1>

      <div className="card space-y-3">
        <div className="flex flex-wrap gap-2">
          {prompts.map((p) => (
            <button
              key={p.kind}
              className={`btn ${kind === p.kind ? 'bg-brand-600 text-white' : 'btn-secondary'}`}
              onClick={() => setKind(p.kind)}
            >
              {p.kind}
            </button>
          ))}
        </div>
        <p className="text-sm text-slate-500">{activePrompt}</p>
        <textarea
          className="input min-h-[160px]"
          lang="ru"
          placeholder="Пиши́те по-ру́сски…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="Writing area"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">
            {text.trim() ? text.trim().split(/\s+/).length : 0} words
          </span>
          <button className="btn-primary" onClick={analyze} disabled={busy || !text.trim()}>
            {busy ? '…' : 'Проверить · Analyze'}
          </button>
        </div>
      </div>

      {analysis && (
        <div className="space-y-4">
          <div className="card">
            <h2 className="font-semibold">Analysis</h2>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <div><span className="text-slate-400">Words</span><div className="font-medium">{analysis.word_count}</div></div>
              <div><span className="text-slate-400">Sentences</span><div className="font-medium">{analysis.sentence_count}</div></div>
              <div><span className="text-slate-400">Avg length</span><div className="font-medium">{analysis.avg_sentence_length}</div></div>
              <div><span className="text-slate-400">Dictionary</span><div className="font-medium">{Math.round(analysis.dictionary_coverage * 100)}%</div></div>
            </div>
          </div>

          {analysis.unknown_words.length > 0 && (
            <div className="card border-amber-200 bg-amber-50">
              <h3 className="text-sm font-semibold">⚠️ Possibly misspelled</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {analysis.unknown_words.map((u) => (
                  <li key={u.word}>
                    «{u.word}»{u.suggestion && <> — did you mean <strong>{u.suggestion}</strong>?</>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis.repetition.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold">🔁 Repetition</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {analysis.repetition.map((r) => (
                  <li key={r.lemma}>
                    «{r.lemma}» ×{r.count}
                    {r.synonyms.length > 0 && <> — try: {r.synonyms.join(', ')}</>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {[...analysis.register_notes, ...analysis.structure_notes].map((note) => (
            <div key={note} className="card bg-sky-50 text-sm text-sky-900">ℹ️ {note}</div>
          ))}

          {analysis.llm_corrections.length > 0 && (
            <div className="card border-violet-200">
              <h3 className="text-sm font-semibold">✏️ Tutor corrections</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {analysis.llm_corrections.map((c, i) => (
                  <li key={i}>
                    <s className="text-red-500">{c.error}</s> → <strong>{c.correction}</strong>
                    <div className="text-slate-500">{c.explanation}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis.srs_candidates.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold">📇 Words you used — add to reviews</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {analysis.srs_candidates.map((c) => (
                  <button
                    key={c.lexeme_id}
                    className={`badge ${added.has(c.lexeme_id)
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-brand-50 text-brand-700 hover:bg-brand-100'}`}
                    onClick={() => addToSrs(c.lexeme_id)}
                    disabled={added.has(c.lexeme_id)}
                  >
                    {added.has(c.lexeme_id) ? '✓ ' : '+ '}{c.lemma}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {history && history.submissions.length > 0 && (
        <div className="card">
          <h2 className="font-semibold">History · {history.total_words_written} words written</h2>
          {history.recurring_mistakes.length > 0 && (
            <p className="mt-1 text-sm text-amber-700">
              Recurring: {history.recurring_mistakes.map((m) => `«${m.word}» ×${m.times}`).join(', ')}
            </p>
          )}
          <ul className="mt-2 space-y-1 text-sm text-slate-500">
            {history.submissions.slice(0, 8).map((s) => (
              <li key={s.id} className="flex justify-between">
                <span className="truncate">{s.prompt}</span>
                <span className="ml-2 shrink-0">
                  {s.word_count}w · {s.created_at.slice(0, 10)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
