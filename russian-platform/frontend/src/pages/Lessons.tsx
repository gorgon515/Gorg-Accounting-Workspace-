import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { useAuth } from '../App';
import { t } from '../lib/i18n';
import type { CourseInfo } from '../types';

export default function Lessons() {
  const [courses, setCourses] = useState<CourseInfo[]>([]);
  const { user } = useAuth();
  const ratio = user?.ui_immersion_ratio ?? 0;

  useEffect(() => {
    api.get<CourseInfo[]>('/lessons/courses').then(setCourses).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Уроки · {t('lessons', ratio)}</h1>
      {courses.map((course) => (
        <section key={course.slug}>
          <div className="flex items-baseline gap-3">
            <h2 className="text-lg font-semibold">{course.title}</h2>
            <span className="badge bg-emerald-50 text-emerald-700">{course.cefr_level}</span>
          </div>
          <p className="mt-1 text-sm text-slate-500">{course.description}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {course.lessons.map((lesson) => (
              <div
                key={lesson.slug}
                className={`card ${lesson.unlocked ? '' : 'opacity-60'}`}
              >
                <div className="flex items-start justify-between">
                  <div className="font-medium">
                    {lesson.order_index}. {lesson.title}
                  </div>
                  {lesson.passed ? (
                    <span className="badge bg-emerald-100 text-emerald-700">✓ {t('passed', ratio)}</span>
                  ) : !lesson.unlocked ? (
                    <span className="badge bg-slate-100 text-slate-500">🔒 {t('locked', ratio)}</span>
                  ) : null}
                </div>
                <ul className="mt-2 space-y-1 text-xs text-slate-500">
                  {lesson.objectives.slice(0, 2).map((objective) => (
                    <li key={objective}>• {objective}</li>
                  ))}
                </ul>
                {lesson.unlocked && (
                  <Link to={`/lessons/${lesson.slug}`} className="btn-primary mt-3">
                    {lesson.passed ? '↻' : ''} {t('start', ratio)}
                  </Link>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
