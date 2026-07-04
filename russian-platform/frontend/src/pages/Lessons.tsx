import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { useAuth } from '../App';
import { t } from '../lib/i18n';
import type { CourseInfo } from '../types';

const TRACKS: { key: string; title: string; icon: string }[] = [
  { key: 'core', title: 'Core Path', icon: '🎓' },
  { key: 'grammar', title: 'Grammar Mastery', icon: '🧩' },
  { key: 'skills', title: 'Skill Workshops', icon: '🏋️' },
  { key: 'sentences', title: 'Sentence Lab', icon: '🧱' },
  { key: 'listening', title: 'Listening', icon: '🎧' },
  { key: 'phonetics', title: 'Phonetics', icon: '🔤' },
];

export default function Lessons() {
  const [courses, setCourses] = useState<CourseInfo[]>([]);
  const [openCourse, setOpenCourse] = useState<string | null>(null);
  const { user } = useAuth();
  const ratio = user?.ui_immersion_ratio ?? 0;

  useEffect(() => {
    api.get<CourseInfo[]>('/lessons/courses').then((data) => {
      setCourses(data);
      // Open the first course with an unlocked, unpassed lesson.
      const active = data.find((c) =>
        c.lessons.some((l) => l.unlocked && !l.passed),
      );
      setOpenCourse(active?.slug ?? data[0]?.slug ?? null);
    }).catch(() => {});
  }, []);

  const byTrack = useMemo(
    () =>
      TRACKS.map((track) => ({
        ...track,
        courses: courses.filter((c) => c.track === track.key),
      })).filter((track) => track.courses.length > 0),
    [courses],
  );

  const totalLessons = courses.reduce((sum, c) => sum + c.lessons.length, 0);
  const passedLessons = courses.reduce(
    (sum, c) => sum + c.lessons.filter((l) => l.passed).length,
    0,
  );

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">Уроки · {t('lessons', ratio)}</h1>
        <span className="text-sm text-slate-400">
          {passedLessons}/{totalLessons} {t('passed', ratio).toLowerCase()}
        </span>
      </div>

      {byTrack.map((track) => (
        <section key={track.key}>
          <h2 className="mb-3 text-lg font-semibold">
            {track.icon} {track.title}
          </h2>
          <div className="space-y-3">
            {track.courses.map((course) => {
              const done = course.lessons.filter((l) => l.passed).length;
              const unlocked = course.lessons.some((l) => l.unlocked);
              const open = openCourse === course.slug;
              return (
                <div key={course.slug} className={`card ${unlocked ? '' : 'opacity-60'}`}>
                  <button
                    className="flex w-full items-center justify-between text-left"
                    onClick={() => setOpenCourse(open ? null : course.slug)}
                    aria-expanded={open}
                  >
                    <div>
                      <span className="font-medium">{course.title}</span>
                      <span className="badge ml-2 bg-emerald-50 text-emerald-700">
                        {course.cefr_level}
                      </span>
                      {!unlocked && course.prerequisite_slug && (
                        <span className="badge ml-2 bg-slate-100 text-slate-500">
                          🔒 requires {course.prerequisite_slug}
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-slate-400">
                      {done}/{course.lessons.length} {open ? '▾' : '▸'}
                    </span>
                  </button>
                  <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                    <div
                      className="h-1.5 rounded-full bg-brand-500"
                      style={{ width: `${(done / course.lessons.length) * 100}%` }}
                    />
                  </div>
                  {open && (
                    <>
                      <p className="mt-2 text-sm text-slate-500">{course.description}</p>
                      <div className="mt-3 grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                        {course.lessons.map((lesson) => (
                          <div
                            key={lesson.slug}
                            className={`rounded-lg border border-slate-200 p-3 ${
                              lesson.unlocked ? '' : 'opacity-50'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2 text-sm">
                              <span className="font-medium">
                                {lesson.order_index}. {lesson.title}
                              </span>
                              {lesson.passed ? (
                                <span className="text-emerald-600">✓</span>
                              ) : !lesson.unlocked ? (
                                <span>🔒</span>
                              ) : null}
                            </div>
                            {lesson.unlocked && (
                              <Link
                                to={`/lessons/${lesson.slug}`}
                                className="mt-2 inline-block text-xs font-medium text-brand-600 hover:underline"
                              >
                                {lesson.passed ? '↻ ' : ''}
                                {t('start', ratio)} →
                              </Link>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
