import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { useAuth } from '../App';
import type { Dashboard as DashboardData, ForecastDay, Quest } from '../types';

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
  const [quests, setQuests] = useState<Quest[]>([]);
  const [forecast, setForecast] = useState<ForecastDay[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { refreshUser } = useAuth();

  const load = useCallback(() => {
    api.get<DashboardData>('/analytics/dashboard').then(setData).catch((e) => setError(e.message));
    api.get<Quest[]>('/gamification/quests').then(setQuests).catch(() => {});
    api
      .get<{ forecast: ForecastDay[] }>('/reviews/forecast?days=14')
      .then((r) => setForecast(r.forecast))
      .catch(() => {});
  }, []);

  useEffect(load, [load]);

  const claimQuest = async (slug: string) => {
    await api.post(`/gamification/quests/${slug}/claim`);
    load();
    refreshUser();
  };

  if (error) return <div className="card text-red-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Загрузка…</div>;

  const maxDue = Math.max(1, ...forecast.map((d) => d.due));

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

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Daily quests · Задания дня</h2>
          <div className="mt-3 space-y-2">
            {quests.map((quest) => (
              <div key={quest.slug} className="flex items-center gap-3 text-sm">
                <span aria-hidden>{quest.icon}</span>
                <div className="flex-1">
                  <div className="font-medium">{quest.title}</div>
                  <div className="text-xs text-slate-400">
                    {quest.description} · {quest.progress}/{quest.target}
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-slate-100">
                    <div
                      className="h-1.5 rounded-full bg-brand-500"
                      style={{ width: `${(quest.progress / quest.target) * 100}%` }}
                    />
                  </div>
                </div>
                {quest.claimed ? (
                  <span className="badge bg-emerald-100 text-emerald-700">✓</span>
                ) : quest.complete ? (
                  <button
                    className="btn-primary px-3 py-1 text-xs"
                    onClick={() => claimQuest(quest.slug)}
                  >
                    +{quest.xp} XP
                  </button>
                ) : (
                  <span className="text-xs text-slate-300">{quest.xp} XP</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="font-semibold">Review forecast · Прогноз повторений</h2>
          <p className="mt-1 text-xs text-slate-400">Due cards per day, next 2 weeks</p>
          <div className="mt-3 flex h-24 items-end gap-1" role="img"
               aria-label="Review forecast bar chart">
            {forecast.map((day) => (
              <div key={day.date} className="group relative flex-1">
                <div
                  className="rounded-t bg-brand-200 transition-colors group-hover:bg-brand-500"
                  style={{ height: `${Math.max(4, (day.due / maxDue) * 88)}px` }}
                />
                <div className="pointer-events-none absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-white group-hover:block">
                  {day.date.slice(5)}: {day.due}
                </div>
              </div>
            ))}
          </div>
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
