import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';

interface SearchResults {
  words?: { id: number; lemma: string; stressed: string; translation: string; match: string }[];
  grammar?: { slug: string; title: string; cefr_level: string; summary: string }[];
  lessons?: { slug: string; title: string; course: string }[];
  texts?: { slug: string; title: string; cefr_level: string; kind: string; bookmarked: boolean }[];
  scenarios?: { slug: string; title: string; cefr_level: string }[];
}

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults>({});
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => inputRef.current?.focus(), []);

  useEffect(() => {
    if (!query.trim()) {
      setResults({});
      setSearched(false);
      return;
    }
    const handle = setTimeout(() => {
      api
        .get<{ results: SearchResults }>(`/account/search?q=${encodeURIComponent(query)}`)
        .then((r) => {
          setResults(r.results);
          setSearched(true);
        })
        .catch(() => {});
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  const empty = searched && Object.keys(results).length === 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">По́иск · Search</h1>
      <input
        ref={inputRef}
        className="input text-lg"
        placeholder="Search everything: живу, книгу, aspect, кнега, погода…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Global search"
      />
      <p className="text-xs text-slate-400">
        Searches the dictionary (including declined and conjugated forms, typo-tolerant),
        grammar, lessons, texts, and scenarios. Press <kbd className="rounded border px-1">/</kbd>{' '}
        anywhere to jump here.
      </p>

      {empty && (
        <div className="card text-center text-slate-500">
          Ничего́ не на́йдено · Nothing found for «{query}»
        </div>
      )}

      {results.words && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Words</h2>
          <ul className="mt-2 divide-y divide-slate-100">
            {results.words.map((w) => (
              <li key={w.id} className="flex items-center justify-between py-2">
                <Link to="/vocabulary" className="hover:text-brand-700">
                  <span className="font-medium">{w.stressed}</span>
                  <span className="ml-2 text-sm text-slate-500">{w.translation}</span>
                </Link>
                {w.match !== 'literal' && (
                  <span className="badge bg-violet-50 text-violet-700">{w.match}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.grammar && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Grammar</h2>
          <ul className="mt-2 space-y-2">
            {results.grammar.map((g) => (
              <li key={g.slug}>
                <Link to={`/grammar/${g.slug}`} className="font-medium text-brand-600 hover:underline">
                  {g.title} <span className="badge bg-emerald-50 text-emerald-700">{g.cefr_level}</span>
                </Link>
                <p className="text-sm text-slate-500">{g.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.lessons && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Lessons</h2>
          <ul className="mt-2 space-y-1">
            {results.lessons.map((l) => (
              <li key={l.slug}>
                <Link to={`/lessons/${l.slug}`} className="text-brand-600 hover:underline">
                  {l.title}
                </Link>
                <span className="ml-2 text-xs text-slate-400">{l.course}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.texts && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Library</h2>
          <ul className="mt-2 space-y-1">
            {results.texts.map((t) => (
              <li key={t.slug} className="flex items-center gap-2">
                <Link to="/library" className="text-brand-600 hover:underline">{t.title}</Link>
                <span className="badge bg-emerald-50 text-emerald-700">{t.cefr_level}</span>
                {t.bookmarked && <span title="Bookmarked">🔖</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {results.scenarios && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Conversation
          </h2>
          <ul className="mt-2 space-y-1">
            {results.scenarios.map((s) => (
              <li key={s.slug}>
                <Link to="/conversation" className="text-brand-600 hover:underline">{s.title}</Link>
                <span className="badge ml-2 bg-emerald-50 text-emerald-700">{s.cefr_level}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
