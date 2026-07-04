import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import { useAuth } from '../App';
import { speak } from '../lib/speech';

interface LevelInfo {
  level: string;
  time_limit_minutes: number;
  best: { score: number; passed: boolean } | null;
}

interface ExamQuestion {
  id: string;
  type: 'choice' | 'text' | 'dictation';
  prompt: string;
  options?: string[];
  speak?: string;
}

interface Exam {
  level: string;
  seed: string;
  time_limit_minutes: number;
  sections: Record<string, ExamQuestion[]>;
}

interface ExamResultData {
  score: number;
  passed: boolean;
  sections: Record<string, { correct: number; total: number; score: number }>;
  worst_section: string | null;
  recommended_lessons: string[];
  result_id: number;
}

interface Certificate {
  certificate_id: string;
  holder: string;
  level: string;
  score_percent: number;
  issued_at: string;
  title: string;
}

export default function Exams() {
  const [levels, setLevels] = useState<LevelInfo[]>([]);
  const [exam, setExam] = useState<Exam | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ExamResultData | null>(null);
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [busy, setBusy] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { refreshUser } = useAuth();

  const loadLevels = () =>
    api.get<LevelInfo[]>('/exams/levels').then(setLevels).catch(() => {});

  useEffect(() => {
    loadLevels();
    return () => stopTimer();
  }, []);

  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const startExam = async (level: string) => {
    const data = await api.get<Exam>(`/exams/level/${level}`);
    setExam(data);
    setAnswers({});
    setResult(null);
    setCertificate(null);
    setSecondsLeft(data.time_limit_minutes * 60);
    stopTimer();
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          submit(data); // time's up — auto submit
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  const submit = async (target?: Exam) => {
    const current = target ?? exam;
    if (!current || busy) return;
    setBusy(true);
    stopTimer();
    try {
      const graded = await api.post<ExamResultData>(
        `/exams/level/${current.level}/submit`,
        { seed: current.seed, answers },
      );
      setResult(graded);
      refreshUser();
      loadLevels();
      if (graded.passed) {
        const cert = await api.get<Certificate>(`/exams/certificates/${graded.result_id}`);
        setCertificate(cert);
      }
    } finally {
      setBusy(false);
    }
  };

  // ---------------------------------------------------------- result view
  if (result && exam) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-2xl font-bold">Экза́мен {exam.level} — результат</h1>
        <div className={`card ${result.passed ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'}`}>
          <div className="text-3xl font-bold">
            {result.passed ? '🎓 Passed' : 'Not passed'} · {Math.round(result.score * 100)}%
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            {Object.entries(result.sections).map(([name, section]) => (
              <div key={name} className="rounded-lg bg-white/70 p-2">
                <div className="font-medium capitalize">{name}</div>
                <div>{section.correct}/{section.total}</div>
              </div>
            ))}
          </div>
          {!result.passed && result.worst_section && (
            <p className="mt-3 text-sm">
              Weakest section: <strong>{result.worst_section}</strong>.
              {result.recommended_lessons.length > 0 &&
                ` Recommended: ${result.recommended_lessons.join(', ')}`}
            </p>
          )}
        </div>

        {certificate && (
          <div className="card border-4 border-double border-brand-700 bg-gradient-to-br from-amber-50 to-white text-center">
            <div className="text-xs uppercase tracking-[0.3em] text-brand-700">
              {certificate.title}
            </div>
            <div className="mt-4 text-3xl font-bold">{certificate.holder}</div>
            <p className="mt-2 text-sm text-slate-600">
              has demonstrated CEFR <strong>{certificate.level}</strong> proficiency in Russian
              with a score of <strong>{certificate.score_percent}%</strong>
            </p>
            <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
              <span>{certificate.certificate_id}</span>
              <span>{certificate.issued_at}</span>
            </div>
            <button className="btn-secondary mt-4" onClick={() => window.print()}>
              🖨 Print certificate
            </button>
          </div>
        )}
        <button className="btn-primary" onClick={() => { setExam(null); setResult(null); }}>
          ← Back to exams
        </button>
      </div>
    );
  }

  // ------------------------------------------------------------ exam view
  if (exam) {
    const minutes = Math.floor(secondsLeft / 60);
    const seconds = String(secondsLeft % 60).padStart(2, '0');
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="sticky top-0 z-10 flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3">
          <h1 className="text-lg font-bold">Экза́мен {exam.level}</h1>
          <span className={`font-mono text-lg ${secondsLeft < 60 ? 'text-red-600' : ''}`}>
            ⏱ {minutes}:{seconds}
          </span>
        </div>

        {Object.entries(exam.sections).map(([name, questions]) => (
          <section key={name} className="card">
            <h2 className="font-semibold capitalize">{name}</h2>
            <div className="mt-3 space-y-4">
              {questions.map((q) => (
                <div key={q.id}>
                  <div className="flex items-start gap-2 text-sm">
                    {q.type === 'dictation' && q.speak && (
                      <button className="btn-secondary px-2 py-1" onClick={() => speak(q.speak!)}>
                        🔊
                      </button>
                    )}
                    <label htmlFor={`${name}-${q.id}`}>{q.prompt}</label>
                  </div>
                  {q.type === 'choice' && q.options ? (
                    <div className="mt-2 grid gap-1 sm:grid-cols-2">
                      {q.options.map((option) => (
                        <label
                          key={option}
                          className={`cursor-pointer rounded-lg border p-2 text-sm ${
                            answers[q.id] === option
                              ? 'border-brand-500 bg-brand-50'
                              : 'border-slate-200 hover:bg-slate-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={q.id}
                            className="mr-2"
                            checked={answers[q.id] === option}
                            onChange={() => setAnswers({ ...answers, [q.id]: option })}
                          />
                          {option}
                        </label>
                      ))}
                    </div>
                  ) : (
                    <input
                      id={`${name}-${q.id}`}
                      className="input mt-1"
                      lang="ru"
                      autoComplete="off"
                      value={answers[q.id] ?? ''}
                      onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}
        <button className="btn-primary w-full" onClick={() => submit()} disabled={busy}>
          {busy ? '…' : 'Сдать экза́мен · Submit'}
        </button>
      </div>
    );
  }

  // ------------------------------------------------------------ list view
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Экза́мены · CEFR Exams</h1>
      <p className="text-sm text-slate-500">
        Timed mock exams for every CEFR level: vocabulary, grammar, reading, and listening.
        Passing lifts your official level estimate and issues a certificate.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {levels.map((info) => (
          <div key={info.level} className="card">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{info.level}</span>
              {info.best && (
                <span
                  className={`badge ${
                    info.best.passed
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  best {Math.round(info.best.score * 100)}%
                  {info.best.passed && ' ✓'}
                </span>
              )}
            </div>
            <div className="mt-1 text-xs text-slate-400">⏱ {info.time_limit_minutes} minutes</div>
            <button className="btn-primary mt-3 w-full" onClick={() => startExam(info.level)}>
              Start
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
