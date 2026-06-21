import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage } from './_langpicker';

// Language Academy home — CEFR curriculum overview and the Daily Coach plan.
export function LanguageAcademy() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Language Academy." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const curriculum = useAsync(() => helios.languageAcademy.curriculum(lang), [lang]);
  const stats = useAsync(() => helios.languageAcademy.stats(), []);
  const [plan, setPlan] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const levels: any[] = Array.isArray(curriculum.data) ? curriculum.data : (curriculum.data?.levels ?? []);
  const s = stats.data ?? ({} as any);

  async function coach() {
    setBusy(true);
    try { setPlan(await helios.languageAcademy.coachToday(lang)); }
    finally { setBusy(false); }
  }

  return (
    <Page title="Language Academy" subtitle="CEFR curriculum · lessons · vocabulary · grammar · assessments"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid gap-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Languages" value={s.languages ?? (langs.length || '—')} accent />
          <MetricCard label="Lessons" value={s.lessons?.catalog_size ?? s.lessons ?? '—'} sub="generated catalog" />
          <MetricCard label="Vocabulary" value={s.vocabulary?.total_entries ?? s.vocabulary ?? '—'} sub="entries" />
          <MetricCard label="Grammar rules" value={s.grammar_rules ?? s.grammar?.total ?? '—'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Panel title="CEFR Curriculum" subtitle={`${lang} · A1 → C2`}>
            {curriculum.loading ? <Loading /> : levels.length === 0 ? (
              <EmptyState message="Curriculum unavailable." />
            ) : (
              <div className="grid gap-2 max-h-[460px] overflow-y-auto scroll-thin">
                {levels.map((lv: any) => (
                  <div key={lv.level} className="rounded-lg border border-hairline p-2.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="mono text-[12px] text-gold">{lv.level}</span>
                      <span className="text-[12px] font-medium">{lv.label}</span>
                      {lv.target_word_count != null && (
                        <span className="mono text-[10px] text-warmgray ml-auto">~{lv.target_word_count} words</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {(lv.can_do_statements ?? lv.goals ?? []).slice(0, 5).map((g: string, n: number) => (
                        <span key={n} className="text-[10px] text-warmgray bg-ivory/5 rounded px-1.5 py-0.5">{g}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Daily Coach" subtitle={plan?.date ? `plan for ${plan.date}` : "today's plan"}
            actions={<Button size="sm" variant="gold" onClick={coach} disabled={busy}>{busy ? '…' : "Generate Today"}</Button>}>
            {!plan ? (
              <EmptyState message="Generate today's plan: a lesson, new words, reviews, a conversation, a listening clip and a quiz." />
            ) : (
              <div className="grid gap-2">
                <CoachRow icon="📘" label="Lesson" value={plan.lesson?.title ?? plan.lesson?.topic ?? '—'} />
                <CoachRow icon="🔤" label="New vocabulary" value={`${(plan.vocabulary ?? []).length} words`} />
                <CoachRow icon="🔁" label="Review due" value={`${(plan.review ?? []).length} cards`} />
                <CoachRow icon="💬" label="Conversation" value={plan.conversation?.title ?? plan.conversation?.scenario ?? '—'} />
                <CoachRow icon="🎧" label="Listening" value={plan.listening?.title ?? '—'} />
                <CoachRow icon="📝" label="Assessment" value={plan.assessment?.title ?? `${(plan.assessment?.questions ?? []).length} questions`} />
              </div>
            )}
          </Panel>
        </div>
      </div>
    </Page>
  );
}

function CoachRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg border border-hairline">
      <span className="text-[14px]">{icon}</span>
      <span className="mono text-[10px] uppercase text-warmgray w-28">{label}</span>
      <span className="text-[12px] flex-1 truncate">{value}</span>
    </div>
  );
}
