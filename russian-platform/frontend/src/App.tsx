import {
  Suspense,
  createContext,
  lazy,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';

import { api, getToken, setToken } from './api/client';
import { t } from './lib/i18n';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import type { User } from './types';

// Route-level code splitting: only the dashboard ships in the main bundle.
const Alphabet = lazy(() => import('./pages/Alphabet'));
const Conversation = lazy(() => import('./pages/Conversation'));
const Grammar = lazy(() => import('./pages/Grammar'));
const GrammarTopicPage = lazy(() => import('./pages/GrammarTopic'));
const LessonPlayer = lazy(() => import('./pages/LessonPlayer'));
const Lessons = lazy(() => import('./pages/Lessons'));
const Library = lazy(() => import('./pages/Library'));
const Review = lazy(() => import('./pages/Review'));
const Settings = lazy(() => import('./pages/Settings'));
const Vocabulary = lazy(() => import('./pages/Vocabulary'));

interface AuthContextValue {
  user: User | null;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  refreshUser: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

const NAV: { to: string; key: Parameters<typeof t>[0]; icon: string }[] = [
  { to: '/', key: 'dashboard', icon: '📊' },
  { to: '/lessons', key: 'lessons', icon: '🎓' },
  { to: '/review', key: 'review', icon: '🔁' },
  { to: '/library', key: 'library', icon: '📚' },
  { to: '/vocabulary', key: 'vocabulary', icon: '📖' },
  { to: '/grammar', key: 'grammar', icon: '🧩' },
  { to: '/conversation', key: 'conversation', icon: '💬' },
  { to: '/alphabet', key: 'alphabet', icon: '🔤' },
  { to: '/settings', key: 'settings', icon: '⚙️' },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api.get<User>('/auth/me'));
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
    const onLogout = () => setUser(null);
    window.addEventListener('rli:logout', onLogout);
    return () => window.removeEventListener('rli:logout', onLogout);
  }, [refreshUser]);

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Загрузка…</div>;
  }

  if (!user) {
    return <Login onLoggedIn={refreshUser} />;
  }

  const ratio = user.ui_immersion_ratio;
  const preferences = user.preferences ?? {};
  const rootClasses = [
    'flex min-h-screen bg-slate-50',
    preferences.high_contrast ? 'high-contrast' : '',
    preferences.dyslexia_font ? 'dyslexia-font' : '',
    preferences.reduced_motion ? 'reduced-motion' : '',
  ]
    .filter(Boolean)
    .join(' ');
  const fontScale = Number(preferences.font_scale ?? 1);

  return (
    <AuthContext.Provider value={{ user, refreshUser, logout }}>
      <div className={rootClasses} style={{ fontSize: `${fontScale}rem` }}>
        <aside className="flex w-60 flex-col border-r border-slate-200 bg-white">
          <div className="border-b border-slate-100 p-4">
            <div className="text-lg font-bold text-brand-700">Русский Институт</div>
            <div className="text-xs text-slate-400">Russian Language Institute</div>
          </div>
          <nav className="flex-1 space-y-1 p-3" aria-label="Main navigation">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                <span aria-hidden>{item.icon}</span>
                {t(item.key, ratio)}
              </NavLink>
            ))}
          </nav>
          <div className="border-t border-slate-100 p-4 text-sm">
            <div className="font-medium">{user.display_name}</div>
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
              <span className="badge bg-amber-100 text-amber-800">🔥 {user.streak_days}</span>
              <span className="badge bg-brand-100 text-brand-700">Lv {user.level}</span>
              <span className="badge bg-emerald-100 text-emerald-700">{user.cefr_estimate}</span>
            </div>
            <button onClick={logout} className="mt-3 text-xs text-slate-400 hover:text-slate-600">
              {t('logout', ratio)}
            </button>
          </div>
        </aside>
        <main className="flex-1 overflow-y-auto p-6" key={location.pathname}>
          <Suspense fallback={<div className="text-slate-400">Загрузка…</div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/lessons" element={<Lessons />} />
              <Route path="/lessons/:slug" element={<LessonPlayer />} />
              <Route path="/review" element={<Review />} />
              <Route path="/library" element={<Library />} />
              <Route path="/vocabulary" element={<Vocabulary />} />
              <Route path="/grammar" element={<Grammar />} />
              <Route path="/grammar/:slug" element={<GrammarTopicPage />} />
              <Route path="/conversation" element={<Conversation />} />
              <Route path="/alphabet" element={<Alphabet />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </AuthContext.Provider>
  );
}
