import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import type { PartnerReply, Scenario } from '../types';

interface Turn {
  role: 'user' | 'partner';
  text: string;
  translation?: string | null;
  corrections?: PartnerReply['corrections'];
}

function speak(text: string) {
  const u = new SpeechSynthesisUtterance(text.replace(/́/g, ''));
  u.lang = 'ru-RU';
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
}

/** Browser speech recognition (Web Speech API) where available. */
function useSpeechInput(onResult: (text: string) => void) {
  const recognitionRef = useRef<any>(null);
  const [listening, setListening] = useState(false);
  const Recognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  const start = () => {
    if (!Recognition) return;
    const recognition = new Recognition();
    recognition.lang = 'ru-RU';
    recognition.interimResults = false;
    recognition.onresult = (event: any) => {
      onResult(event.results[0][0].transcript);
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  return { supported: Boolean(Recognition), listening, start };
}

export default function Conversation() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [active, setActive] = useState<Scenario | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [hints, setHints] = useState<string[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [completed, setCompleted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { supported: speechSupported, listening, start: startListening } = useSpeechInput(
    (text) => setInput(text),
  );

  useEffect(() => {
    api.get<Scenario[]>('/conversation/scenarios').then(setScenarios).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const startScenario = async (scenario: Scenario) => {
    const result = await api.post<{ session_id: number; opening: PartnerReply }>(
      `/conversation/sessions/${scenario.slug}`,
    );
    setActive(scenario);
    setSessionId(result.session_id);
    setTurns([
      { role: 'partner', text: result.opening.text, translation: result.opening.translation },
    ]);
    setHints(result.opening.hints);
    setCompleted(false);
    speak(result.opening.text);
  };

  const send = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || sessionId === null) return;
    setInput('');
    setTurns((t) => [...t, { role: 'user', text: message }]);
    setBusy(true);
    try {
      const reply = await api.post<PartnerReply>(
        `/conversation/sessions/${sessionId}/messages`,
        { text: message },
      );
      setTurns((t) => [
        ...t,
        {
          role: 'partner',
          text: reply.text,
          translation: reply.translation,
          corrections: reply.corrections,
        },
      ]);
      setHints(reply.hints);
      setCompleted(Boolean(reply.completed));
      speak(reply.text);
    } finally {
      setBusy(false);
    }
  };

  if (!active) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Разговор · AI Conversation Partner</h1>
        <p className="text-sm text-slate-500">
          Pick a scenario and speak (or type) Russian. The partner replies with voice, gentle
          corrections, and hints.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {scenarios.map((scenario) => (
            <button
              key={scenario.slug}
              className="card text-left hover:border-brand-300"
              onClick={() => startScenario(scenario)}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{scenario.title}</span>
                <span className="badge bg-emerald-50 text-emerald-700">{scenario.cefr_level}</span>
              </div>
              <p className="mt-1 text-sm text-slate-500">{scenario.description}</p>
              <div className="mt-2 text-xs text-slate-400">
                🎭 {scenario.persona} · 📍 {scenario.setting}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-3rem)] max-w-2xl flex-col">
      <div className="flex items-center justify-between pb-3">
        <div>
          <h1 className="text-xl font-bold">{active.title}</h1>
          <div className="text-xs text-slate-400">
            🎭 {active.persona} · you can always ask to repeat: «Повтори́те, пожа́луйста»
          </div>
        </div>
        <button className="btn-secondary" onClick={() => setActive(null)}>
          ✕ End
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
        {turns.map((turn, index) => (
          <div key={index} className={turn.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                turn.role === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-100'
              }`}
            >
              <button
                className="text-left"
                onClick={() => turn.role === 'partner' && speak(turn.text)}
                title={turn.role === 'partner' ? 'Click to listen' : undefined}
              >
                {turn.text}
              </button>
              {turn.translation && (
                <div className="mt-1 text-xs opacity-70">{turn.translation}</div>
              )}
              {turn.corrections && turn.corrections.length > 0 && (
                <div className="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">
                  {turn.corrections.map((correction, ci) => (
                    <div key={ci}>
                      ✏️ {correction.correction && <strong>{correction.correction}</strong>}{' '}
                      {correction.explanation}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {completed && (
          <div className="rounded-lg bg-emerald-50 p-3 text-center text-sm text-emerald-800">
            🎉 Диало́г завершён! Dialogue completed — start it again or try another scenario.
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {hints.length > 0 && !completed && (
        <div className="flex flex-wrap gap-2 py-2">
          {hints.map((hint) => (
            <button
              key={hint}
              className="badge bg-brand-50 text-brand-700 hover:bg-brand-100"
              onClick={() => send(hint)}
            >
              💡 {hint}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 pt-2">
        {speechSupported && (
          <button
            className={`btn-secondary ${listening ? 'animate-pulse border-red-400 text-red-600' : ''}`}
            onClick={startListening}
            title="Speak Russian"
          >
            🎤
          </button>
        )}
        <input
          className="input flex-1"
          placeholder="Напиши́те по-ру́сски…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          lang="ru"
          disabled={busy || completed}
        />
        <button className="btn-primary" onClick={() => send()} disabled={busy || completed}>
          ➤
        </button>
      </div>
    </div>
  );
}
