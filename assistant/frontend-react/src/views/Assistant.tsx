import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Page } from './_page';
import { helios } from '../ipc/client';
import { Button, Panel, VoiceVisualizer, StatusBadge, EmptyState } from '../components';
import type { VoiceState } from '../components';
import type { RouteResult } from '../ipc/types';
import { cls } from '../lib/format';

interface Msg { role: 'user' | 'assistant'; text: string }
interface ToolEvent { name: string; ok: boolean; error?: string }

export function Assistant() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [sending, setSending] = useState(false);
  const [voice, setVoice] = useState<VoiceState>('idle');
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const scroller = useRef<HTMLDivElement>(null);

  const scroll = () => requestAnimationFrame(() => scroller.current?.scrollTo({ top: 1e9, behavior: 'smooth' }));

  async function send(text: string) {
    const q = text.trim();
    if (!q || sending) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: q }]);
    setSending(true);
    setVoice('thinking');
    scroll();

    // Show which specialist HELIOS routes this to (and why) before answering.
    helios.agents.route(q).then(setRoute).catch(() => setRoute(null));

    try {
      const res: any = await helios.ask(q, history);
      setHistory(res.history || history);
      setTools((res.toolEvents || []).map((t: any) => ({ name: t.name, ok: t.ok, error: t.error })));
      setMsgs((m) => [...m, { role: 'assistant', text: res.text || '(no response)' }]);
      setVoice('speaking');
      setTimeout(() => setVoice('idle'), 1400);
    } catch (err: any) {
      setMsgs((m) => [...m, { role: 'assistant', text: offlineNote(err?.message) }]);
      setVoice('idle');
    } finally {
      setSending(false);
      scroll();
    }
  }

  // Push-to-talk using the browser SpeechRecognition, when available.
  function mic() {
    const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SR) {
      setMsgs((m) => [...m, { role: 'assistant', text: 'Voice capture runs in the desktop build (on-device Whisper).' }]);
      return;
    }
    const rec = new SR();
    rec.lang = 'en-US';
    setVoice('listening');
    rec.onresult = (e: any) => { const t = e.results[0][0].transcript; setInput(t); send(t); };
    rec.onerror = () => setVoice('idle');
    rec.onend = () => setVoice((v) => (v === 'listening' ? 'idle' : v));
    rec.start();
  }

  return (
    <Page
      title="Assistant"
      subtitle="Conversational interface · agent + tool visibility"
      actions={<VoiceVisualizer state={voice} />}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-3 h-[calc(100%-3.5rem)]">
        <Panel title="Conversation" className="h-full" bodyClass="flex flex-col h-full p-0">
          <div ref={scroller} className="flex-1 overflow-y-auto scroll-thin p-4 flex flex-col gap-2.5">
            {!msgs.length && (
              <EmptyState message='Ask anything — e.g. "analyze NVDA", "explain ASC 606", "teach me 5 Spanish words".' />
            )}
            {msgs.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className={cls('max-w-[85%] rounded-xl px-3.5 py-2 text-[13px] leading-relaxed',
                  m.role === 'user'
                    ? 'self-end bg-gold/15 border border-gold/30'
                    : 'self-start bg-obsidian/60 border border-hairline')}
              >
                {m.text}
              </motion.div>
            ))}
            {sending && <div className="self-start text-warmgray text-[12px] mono">thinking…</div>}
          </div>
          <form
            className="flex gap-2 p-3 border-t border-hairline"
            onSubmit={(e) => { e.preventDefault(); send(input); }}
          >
            <Button type="button" onClick={mic} title="Push to talk">🎤</Button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message HELIOS…"
              className="flex-1 bg-obsidian/60 border border-hairline rounded-lg px-3 py-2 text-[13px] outline-none focus:border-gold/40"
            />
            <Button type="submit" variant="gold" disabled={sending}>Send</Button>
          </form>
        </Panel>

        <div className="flex flex-col gap-3 min-h-0">
          <Panel title="Active agent" subtitle="who answered & why">
            {route ? (
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">{route.name}</span>
                  <StatusBadge status="online" label={route.confidence} />
                </div>
                <p className="text-[11px] text-warmgray mt-1.5">
                  Routed by relevance score {route.score}.
                  {route.alternates?.length ? ` Alternates: ${route.alternates.join(', ')}.` : ''}
                </p>
              </div>
            ) : <EmptyState message="Ask something to see routing." />}
          </Panel>

          <Panel title="Tools used" className="flex-1" scroll>
            {tools.length ? (
              <ul className="flex flex-col gap-1.5">
                {tools.map((t, i) => (
                  <li key={i} className="flex items-center gap-2 text-[12px]">
                    <span className={cls('w-1.5 h-1.5 rounded-full', t.ok ? 'bg-helgreen' : 'bg-helred')} />
                    <span className="mono">{t.name}</span>
                    {!t.ok && t.error && <span className="text-helred text-[10px] truncate">{t.error}</span>}
                  </li>
                ))}
              </ul>
            ) : <EmptyState message="No tools called yet." />}
          </Panel>
        </div>
      </div>
    </Page>
  );
}

function offlineNote(msg?: string): string {
  if (msg && /bridge unavailable/i.test(msg)) {
    return 'The brain answers inside the HELIOS desktop app (local Ollama or Claude). This is the UI preview.';
  }
  return `Error: ${msg || 'unknown'}`;
}
