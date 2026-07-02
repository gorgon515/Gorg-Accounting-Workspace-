import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import type { GrammarTopicSummary } from '../types';

const LEVEL_ORDER = ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export default function Grammar() {
  const [topics, setTopics] = useState<GrammarTopicSummary[]>([]);

  useEffect(() => {
    api.get<GrammarTopicSummary[]>('/grammar/topics').then(setTopics).catch(() => {});
  }, []);

  const byLevel = LEVEL_ORDER.map((level) => ({
    level,
    topics: topics.filter((topic) => topic.cefr_level === level),
  })).filter((group) => group.topics.length > 0);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Грамматика · Grammar Encyclopedia</h1>
      {byLevel.map((group) => (
        <section key={group.level}>
          <h2 className="mb-3 text-lg font-semibold">
            <span className="badge mr-2 bg-emerald-50 text-emerald-700">{group.level}</span>
          </h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {group.topics.map((topic) => (
              <Link
                key={topic.slug}
                to={`/grammar/${topic.slug}`}
                className={`card block hover:border-brand-300 ${topic.has_content ? '' : 'opacity-70'}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium">{topic.title}</div>
                  {topic.mastery > 0 && (
                    <span
                      className={`badge ${
                        topic.mastery >= 0.7
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {Math.round(topic.mastery * 100)}%
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400">{topic.title_native}</div>
                <p className="mt-2 text-sm text-slate-500">{topic.summary}</p>
                <div className="mt-2 text-xs text-slate-400">
                  {topic.has_content
                    ? `${topic.drill_count} drills`
                    : 'Outline — full content coming in a content sprint'}
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
