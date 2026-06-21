import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';
import { LanguagePicker, useAcademyLanguage, LEVELS } from './_langpicker';

// Conversation Lab — AI roleplay scenarios with turn-by-turn feedback.
export function ConversationLab() {
  if (!helios.hasBridge()) return <EmptyState message="Open in the desktop app for the Conversation Lab." />;
  const [lang, setLang, langs] = useAcademyLanguage();
  const [level, setLevel] = useState('A2');
  const scenarios = useAsync(() => helios.languageAcademy.scenarios(), []);
  const [session, setSession] = useState<any>(null);
  const [turns, setTurns] = useState<any[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const list: any[] = Array.isArray(scenarios.data) ? scenarios.data : (scenarios.data?.scenarios ?? []);

  async function start(scenarioId: string) {
    setBusy(true);
    try {
      const s = await helios.languageAcademy.startConversation({ language: lang, scenario: scenarioId, level });
      setSession(s);
      setTurns(s.opening_line ? [{ role: 'assistant', text: s.opening_line }] : []);
    } finally { setBusy(false); }
  }

  async function send() {
    if (!text.trim() || !session) return;
    const mine = text.trim();
    setTurns((t) => [...t, { role: 'user', text: mine }]);
    setText(''); setBusy(true);
    try {
      const r = await helios.languageAcademy.respond({ session_id: session.session_id ?? session.id, text: mine });
      setTurns((t) => [...t, { role: 'assistant', text: r.ai_response ?? r.reply ?? r.text ?? r.message, feedback: r.feedback, corrections: r.corrections }]);
    } finally { setBusy(false); }
  }

  return (
    <Page title="Conversation Lab" subtitle="restaurant · interview · tax consultation · investment pitch · more"
      actions={<LanguagePicker lang={lang} set={setLang} langs={langs} />}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title="Scenarios" className="lg:col-span-1">
          <div className="flex gap-1 mb-2">
            {LEVELS.map((lv) => (
              <button key={lv} onClick={() => setLevel(lv)}
                className={cls('px-2 py-0.5 rounded border text-[10px] mono',
                  level === lv ? 'border-gold/40 text-gold' : 'border-hairline text-warmgray')}>{lv}</button>
            ))}
          </div>
          {scenarios.loading ? <Loading /> : (
            <div className="grid gap-1.5 max-h-[460px] overflow-y-auto scroll-thin">
              {(list.length ? list : []).map((s: any) => {
                const id = s.id ?? s;
                return (
                  <button key={id} onClick={() => start(id)} disabled={busy}
                    className={cls('text-left px-2.5 py-2 rounded border text-[12px] hover:bg-ivory/5',
                      session?.scenario === id ? 'border-gold/40 bg-gold/5 text-gold' : 'border-hairline')}>
                    {s.title ?? id}
                    {s.setup && <p className="text-[10px] text-warmgray mt-0.5 truncate">{s.setup}</p>}
                  </button>
                );
              })}
            </div>
          )}
        </Panel>

        <Panel title={session ? (session.scenario ?? 'Conversation') : 'Conversation'}
          subtitle={session ? `${lang} · ${level}` : 'pick a scenario to begin'} className="lg:col-span-2">
          {!session ? (
            <EmptyState message="Choose a scenario on the left to start a roleplay." />
          ) : (
            <div className="grid gap-3">
              {session.instructions && <p className="text-[11px] text-warmgray italic">{session.instructions}</p>}
              <div className="grid gap-2 max-h-[380px] overflow-y-auto scroll-thin">
                {turns.map((t, n) => (
                  <div key={n} className={cls('max-w-[85%] px-3 py-2 rounded-lg text-[12px]',
                    t.role === 'user' ? 'ml-auto bg-gold/10 border border-gold/30' : 'bg-ivory/5 border border-hairline')}>
                    <p className={t.role === 'user' ? 'text-gold' : 'text-ivory/90'}>{t.text}</p>
                    {t.corrections?.found?.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-hairline/60">
                        {t.corrections.found.map((c: any, k: number) => (
                          <p key={k} className="text-[10px]">
                            <span className="text-helred line-through">{c.wrong}</span>
                            <span className="text-warmgray mx-1">→</span>
                            <span className="text-helgreen">{c.right}</span>
                          </p>
                        ))}
                      </div>
                    )}
                    {t.feedback && (
                      <p className="text-[10px] text-warmgray mt-1">
                        {typeof t.feedback === 'string' ? t.feedback
                          : [t.feedback.score != null ? `score ${t.feedback.score}` : '', ...(t.feedback.notes ?? [])].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input className="flex-1 bg-obsidian border border-hairline rounded px-3 py-2 text-sm"
                  placeholder={`Reply in ${lang}…`} value={text}
                  onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} />
                <Button size="sm" variant="gold" onClick={send} disabled={busy}>Send</Button>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}
