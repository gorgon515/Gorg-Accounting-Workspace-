import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';

interface Report {
  period: string;
  reviews: { total: number; lapses: number; accuracy: number | null };
  forgotten_words: { lemma: string; stressed: string; translation: string; lapses: number }[];
  weak_grammar: { slug: string; title: string; mastery: number }[];
  pronunciation_avg: number | null;
  study_minutes: number;
  activity_events: number;
  recommendations: { kind: string; action: string; lesson_slug: string | null }[];
}

interface Trends {
  heatmap: Record<string, number>;
  velocity: { week: string; new_words: number }[];
  skills: Record<string, number | null>;
  strongest_skill: string | null;
  weakest_skill: string | null;
  fluency_estimate: {
    target_level: string;
    words_remaining: number;
    words_per_week: number;
    estimated_date: string;
  } | null;
}

interface ExamRow {
  id: number;
  kind: string;
  level: string;
  score: number;
  passed: boolean;
  taken_at: string;
}

function heatColor(count: number): string {
  if (count === 0) return 'bg-slate-100';
  if (count < 5) return 'bg-brand-100';
  if (count < 15) return 'bg-brand-300';
  if (count < 30) return 'bg-brand-500';
  return 'bg-brand-700';
}

export default function Progress() {
  const [period, setPeriod] = useState<'week' | 'month'>('week');
  const [report, setReport] = useState<Report | null>(null);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [exams, setExams] = useState<ExamRow[]>([]);

  useEffect(() => {
    api.get<Report>(`/analytics/report?period=${period}`).then(setReport).catch(() => {});
  }, [period]);

  useEffect(() => {
    api.get<Trends>('/analytics/trends').then(setTrends).catch(() => {});
    api.get<ExamRow[]>('/exams/results').then(setExams).catch(() => {});
  }, []);

  // 13 weeks × 7 days grid ending today.
  const days: string[] = [];
  const today = new Date();
  for (let i = 90; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Прогре́сс · Progress Report</h1>
        <div className="flex gap-2">
          {(['week', 'month'] as const).map((p) => (
            <button
              key={p}
              className={`btn ${period === p ? 'bg-brand-600 text-white' : 'btn-secondary'}`}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {trends && (
        <div className="card">
          <h2 className="font-semibold">Activity — last 13 weeks</h2>
          <div className="mt-3 grid grid-flow-col grid-rows-7 gap-1 overflow-x-auto"
               role="img" aria-label="Study activity heatmap">
            {days.map((day) => (
              <div
                key={day}
                title={`${day}: ${trends.heatmap[day] ?? 0} activities`}
                className={`h-3 w-3 rounded-sm ${heatColor(trends.heatmap[day] ?? 0)}`}
              />
            ))}
          </div>
        </div>
      )}

      {report && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold">This {report.period}</h2>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-slate-400">Reviews</span>
                <div className="text-xl font-bold">{report.reviews.total}</div></div>
              <div><span className="text-slate-400">Accuracy</span>
                <div className="text-xl font-bold">
                  {report.reviews.accuracy === null ? '—'
                    : `${Math.round(report.reviews.accuracy * 100)}%`}
                </div></div>
              <div><span className="text-slate-400">Study time</span>
                <div className="text-xl font-bold">{report.study_minutes}м</div></div>
              <div><span className="text-slate-400">Activities</span>
                <div className="text-xl font-bold">{report.activity_events}</div></div>
            </div>
          </div>

          <div className="card">
            <h2 className="font-semibold">Recommendations</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {report.recommendations.map((r) => (
                <li key={r.action} className="flex items-start gap-2">
                  <span>→</span>
                  <span>
                    {r.action}
                    {r.lesson_slug && (
                      <> · <Link className="text-brand-600 underline"
                                 to={`/lessons/${r.lesson_slug}`}>open lesson</Link></>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {report.forgotten_words.length > 0 && (
            <div className="card">
              <h2 className="font-semibold">Most forgotten words</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {report.forgotten_words.map((w) => (
                  <li key={w.lemma} className="flex justify-between">
                    <span>{w.stressed} — {w.translation}</span>
                    <span className="text-red-500">×{w.lapses}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {trends && (
            <div className="card">
              <h2 className="font-semibold">Skills</h2>
              <div className="mt-3 space-y-2">
                {Object.entries(trends.skills).map(([skill, value]) => (
                  <div key={skill} className="flex items-center gap-2 text-sm">
                    <span className="w-24 capitalize">{skill}</span>
                    <div className="h-2 flex-1 rounded-full bg-slate-100">
                      <div
                        className={`h-2 rounded-full ${
                          skill === trends.weakest_skill ? 'bg-amber-400' : 'bg-brand-500'
                        }`}
                        style={{ width: `${(value ?? 0) * 100}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-slate-400">
                      {value === null ? '—' : `${Math.round(value * 100)}%`}
                    </span>
                  </div>
                ))}
              </div>
              {trends.fluency_estimate && (
                <p className="mt-3 text-xs text-slate-500">
                  At {trends.fluency_estimate.words_per_week} words/week you reach{' '}
                  {trends.fluency_estimate.target_level} vocabulary around{' '}
                  <strong>{trends.fluency_estimate.estimated_date}</strong>.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {exams.length > 0 && (
        <div className="card">
          <h2 className="font-semibold">Exam history</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {exams.slice(0, 10).map((e) => (
              <li key={e.id} className="flex justify-between">
                <span>{e.kind === 'placement' ? '🎯 Placement' : `📝 ${e.level}`}</span>
                <span className={e.passed ? 'text-emerald-600' : 'text-slate-400'}>
                  {Math.round(e.score * 100)}% · {e.taken_at.slice(0, 10)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
