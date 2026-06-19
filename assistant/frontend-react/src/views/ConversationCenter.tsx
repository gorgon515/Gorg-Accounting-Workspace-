import { useState, useRef, useEffect } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading } from '../components';
import { cls } from '../lib/format';

const MODES = ['chat', 'voice', 'multi_agent', 'briefing'];

export function ConversationCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Conversation Center." />;
  const threads = useAsync(() => helios.conversation.threads(), [], 10000);
  const analytics = useAsync(() => helios.conversation.analytics(), [], 10000);

  const [activeThread, setActiveThread] = useState<any>(null);
  const [threadData, setThreadData] = useState<any>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState('chat');
  const [newTitle, setNewTitle] = useState('');
  const messagesRef = useRef<HTMLDivElement>(null);

  const a = analytics.data ?? {};

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [threadData]);

  async function createThread() {
    if (!newTitle.trim()) return;
    setBusy(true);
    try {
      const t = await helios.conversation.createThread({ title: newTitle, mode, participants: ['user', 'assistant'] });
      setNewTitle('');
      setActiveThread(t);
      setThreadData(t);
      threads.reload();
    } finally { setBusy(false); }
  }

  async function loadThread(t: any) {
    setActiveThread(t);
    const data = await helios.conversation.getThread(t.id);
    setThreadData(data);
  }

  async function sendMessage() {
    if (!input.trim() || !activeThread) return;
    setBusy(true);
    const content = input;
    setInput('');
    try {
      await helios.conversation.sendMessage(activeThread.id, { role: 'user', content });
      const r = await helios.conversation.sendMessage(activeThread.id, {
        role: 'assistant', content: `[HELIOS] Received: "${content.slice(0, 60)}…"`, agent_id: 'helios'
      });
      const data = await helios.conversation.getThread(activeThread.id);
      setThreadData(data);
      threads.reload();
    } finally { setBusy(false); }
  }

  async function closeThread() {
    if (!activeThread) return;
    await helios.conversation.closeThread(activeThread.id, { summary: 'Closed by user.' });
    setActiveThread(null);
    setThreadData(null);
    threads.reload();
  }

  return (
    <Page title="Conversation Center" subtitle="multi-turn conversations · context tracking · agent participation"
      actions={<Button size="sm" onClick={() => { threads.reload(); analytics.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Total Threads" value={a.total_threads ?? 0} accent />
          <MetricCard label="Active" value={a.active_threads ?? 0} />
          <MetricCard label="Messages" value={a.total_messages ?? 0} />
          <MetricCard label="Avg Turns" value={a.avg_turns ?? '—'} />
        </div>

        <div className="grid grid-cols-3 gap-3" style={{ minHeight: 420 }}>
          <Panel title="Threads" className="col-span-1">
            <div className="flex flex-col gap-2 mb-3">
              <input className="bg-obsidian border border-hairline rounded px-2 py-1.5 text-xs"
                placeholder="New thread title…" value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') createThread(); }} />
              <div className="flex gap-1.5">
                <select className="flex-1 border border-hairline bg-obsidian rounded px-2 text-[11px]"
                  value={mode} onChange={(e) => setMode(e.target.value)}>
                  {MODES.map((m) => <option key={m}>{m}</option>)}
                </select>
                <Button size="sm" variant="gold" onClick={createThread} disabled={busy || !newTitle.trim()}>+</Button>
              </div>
            </div>
            <div className="flex flex-col gap-1.5 overflow-y-auto" style={{ maxHeight: 300 }}>
              {threads.loading ? <Loading /> : (threads.data as any[] ?? []).length === 0 ? (
                <EmptyState message="No threads yet." />
              ) : (
                (threads.data as any[]).map((t: any) => (
                  <button key={t.id}
                    onClick={() => loadThread(t)}
                    className={cls('w-full text-left px-2.5 py-1.5 rounded border text-[12px] transition-colors',
                      activeThread?.id === t.id ? 'border-gold/40 bg-gold/5 text-gold' : 'border-hairline text-ivory/70 hover:text-ivory hover:bg-ivory/5')}>
                    <div className="truncate">{t.title}</div>
                    <div className="mono text-[10px] text-warmgray">{t.mode} · {t.turn_count} turns</div>
                  </button>
                ))
              )}
            </div>
          </Panel>

          <div className="col-span-2 flex flex-col gap-2">
            {!activeThread ? (
              <div className="flex-1 flex items-center justify-center">
                <EmptyState message="Select or create a thread to start a conversation." />
              </div>
            ) : (
              <Panel title={activeThread.title}
                subtitle={`${activeThread.mode} · ${threadData?.messages?.length ?? 0} messages`}>
                <div className="flex flex-col" style={{ height: 340 }}>
                  <div ref={messagesRef} className="flex-1 overflow-y-auto scroll-thin flex flex-col gap-2 pr-1 mb-3">
                    {!(threadData?.messages?.length) ? (
                      <EmptyState message="No messages yet. Say something." />
                    ) : (
                      (threadData.messages as any[]).map((m: any) => (
                        <div key={m.id} className={cls('flex flex-col gap-0.5',
                          m.role === 'user' ? 'items-end' : 'items-start')}>
                          <div className={cls('max-w-[85%] rounded-lg px-3 py-2 text-[12px]',
                            m.role === 'user' ? 'bg-gold/15 text-ivory' : 'bg-obsidian border border-hairline text-ivory/90')}>
                            {m.content}
                          </div>
                          <div className="mono text-[10px] text-warmgray px-1">
                            {m.role}{m.agent_id ? ` (${m.agent_id})` : ''}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="flex gap-2 border-t border-hairline pt-2">
                    <input
                      className="flex-1 bg-obsidian border border-hairline rounded px-3 py-1.5 text-sm"
                      placeholder="Type a message…"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                      disabled={busy}
                    />
                    <Button size="sm" variant="gold" onClick={sendMessage} disabled={busy || !input.trim()}>Send</Button>
                    <Button size="sm" variant="ghost" onClick={closeThread}>Close</Button>
                  </div>
                </div>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </Page>
  );
}
