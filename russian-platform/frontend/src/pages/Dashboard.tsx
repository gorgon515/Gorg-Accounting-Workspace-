import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import type { Dashboard as DashboardData } from '../types';

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<DashboardData>('/analytics/dashboard').then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card text-red-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Загрузка…</div>;

  const retention = data.vocabulary.predicted_retention;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Панель обучения · Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat
          label="CEFR level"
          value={data.cefr.level}
          sub={`${Math.round(data.cefr.progress_to_next * 100)}% to next level`}
        />
        <Stat label="Known words" value={String(data.vocabulary.known_words)} sub="stability ≥ 7 days" />
        <Stat label="Streak" value={`🔥 ${data.streak_days}`} sub="days in a row" />
        <Stat
          label="Level"
          value={`Lv ${data.xp.level}`}
          sub={`${data.xp.xp_in_level}/${data.xp.xp_for_next} XP`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Memory · Память</h2>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Cards due now</span>
              <span className="font-medium">{data.vocabulary.due_now}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Predicted retention</span>
              <span className="font-medium">
                {retention === null ? '—' : `${Math.round(retention * 100)}%`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Reviews (7 days)</span>
              <span className="font-medium">
                {data.reviews_7d.total}
                {data.reviews_7d.accuracy !== null &&
                  ` · ${Math.round(data.reviews_7d.accuracy * 100)}% accuracy`}
              </span>
            </div>
          </div>
          {data.vocabulary.due_now > 0 && (
            <Link to="/review" className="btn-primary mt-4">
              Review {data.vocabulary.due_now} cards →
            </Link>
          )}
        </div>

        <div className="card">
          <h2 className="font-semibold">Weak grammar · Слабые места</h2>
          {data.weak_grammar.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No weak topics detected yet — do some grammar drills to build your profile.
            </p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {data.weak_grammar.map((g) => (
                <li key={g.slug} className="flex items-center justify-between">
                  <Link to={`/grammar/${g.slug}`} className="text-brand-600 hover:underline">
                    {g.title}
                  </Link>
                  <span className="text-slate-400">{Math.round(g.mastery * 100)}%</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold">Achievements · Достижения</h2>
        {data.achievements.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Pass your first lesson to start earning badges.</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {data.achievements.map((a) => (
              <span key={a.slug} className="badge bg-amber-50 text-amber-800" title={a.earned_at}>
                {a.icon} {a.title}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
