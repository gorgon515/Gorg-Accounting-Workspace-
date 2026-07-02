import { FormEvent, useState } from 'react';

import { api, setToken } from '../api/client';

export default function Login({ onLoggedIn }: { onLoggedIn: () => Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result =
        mode === 'login'
          ? await api.loginForm(email, password)
          : await api.post<{ access_token: string }>('/auth/register', {
              email,
              password,
              display_name: displayName || email.split('@')[0],
            });
      setToken(result.access_token);
      await onLoggedIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-900 to-brand-600 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-brand-900">Русский Институт</h1>
        <p className="mt-1 text-sm text-slate-500">
          Your AI-powered path from zero to fluent Russian.
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === 'register' && (
            <input
              className="input"
              placeholder="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              aria-label="Display name"
            />
          )}
          <input
            className="input"
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-label="Email"
          />
          <input
            className="input"
            type="password"
            required
            minLength={8}
            placeholder="Password (8+ characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-label="Password"
          />
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? '…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>
        <button
          className="mt-4 w-full text-center text-sm text-brand-600 hover:underline"
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
        >
          {mode === 'login' ? 'New here? Create an account' : 'Have an account? Log in'}
        </button>
      </div>
    </div>
  );
}
