import { useState } from 'react';

import { api } from '../api/client';
import { useAuth } from '../App';
import { immersionCoverage } from '../lib/i18n';
import type { User } from '../types';

const IMMERSION_STOPS = [0, 0.25, 0.5, 0.75, 1];

export default function Settings() {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  if (!user) return null;

  const preferences = user.preferences ?? {};

  const update = async (payload: Record<string, unknown>) => {
    setSaving(true);
    setSaved(false);
    try {
      await api.patch<User>('/auth/me', payload);
      await refreshUser();
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  const setPreference = (key: string, value: unknown) =>
    update({ preferences: { [key]: value } });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Настро́йки · Settings</h1>
      {saved && (
        <div className="rounded-lg bg-emerald-50 p-2 text-sm text-emerald-800">Saved ✓</div>
      )}

      <section className="card">
        <h2 className="font-semibold">🇷🇺 Immersion mode · Погружение</h2>
        <p className="mt-1 text-sm text-slate-500">
          The interface gradually switches to Russian as you raise this. Easier words flip first.
        </p>
        <div className="mt-4 flex gap-2">
          {IMMERSION_STOPS.map((stop) => (
            <button
              key={stop}
              className={`btn flex-1 ${
                Math.abs(user.ui_immersion_ratio - stop) < 0.01
                  ? 'bg-brand-600 text-white'
                  : 'btn-secondary'
              }`}
              onClick={() => update({ ui_immersion_ratio: stop })}
              disabled={saving}
            >
              {Math.round(stop * 100)}%
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Currently {Math.round(immersionCoverage(user.ui_immersion_ratio) * 100)}% of interface
          strings show in Russian.
        </p>
      </section>

      <section className="card">
        <h2 className="font-semibold">♿ Accessibility · Доступность</h2>
        <div className="mt-3 space-y-4 text-sm">
          <label className="flex items-center justify-between">
            <span>Font size</span>
            <select
              className="input w-36"
              value={String(preferences.font_scale ?? 1)}
              onChange={(e) => setPreference('font_scale', Number(e.target.value))}
              disabled={saving}
            >
              <option value="0.9">Small</option>
              <option value="1">Normal</option>
              <option value="1.15">Large</option>
              <option value="1.3">Extra large</option>
            </select>
          </label>
          {(
            [
              ['high_contrast', 'High contrast'],
              ['dyslexia_font', 'Dyslexia-friendly font'],
              ['reduced_motion', 'Reduced motion'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center justify-between">
              <span>{label}</span>
              <input
                type="checkbox"
                className="h-5 w-5 accent-brand-600"
                checked={Boolean(preferences[key])}
                onChange={(e) => setPreference(key, e.target.checked)}
                disabled={saving}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="font-semibold">🎯 Learning · Обучение</h2>
        <label className="mt-3 flex items-center justify-between text-sm">
          <span>Daily goal (minutes)</span>
          <select
            className="input w-36"
            value={String(user.daily_goal_minutes)}
            onChange={(e) => update({ daily_goal_minutes: Number(e.target.value) })}
            disabled={saving}
          >
            {[15, 30, 60, 90, 120].map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes}
              </option>
            ))}
          </select>
        </label>
      </section>
    </div>
  );
}
