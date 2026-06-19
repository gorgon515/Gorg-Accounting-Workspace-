import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading, VoiceVisualizer } from '../components';
import type { VoiceState } from '../components';
import { cls } from '../lib/format';

const MODES = ['idle', 'push_to_talk', 'always_listening'] as const;

export function VoiceCenter() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Voice Center." />;
  const status = useAsync(() => helios.voice.status(), [], 5000);
  const caps = useAsync(() => helios.voice.capabilities(), []);
  const profiles = useAsync(() => helios.voice.profiles(), []);
  const sessions = useAsync(() => helios.voice.sessions(), [], 30000);
  const stats = useAsync(() => helios.voice.stats(), [], 10000);

  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [busy, setBusy] = useState(false);
  const [ttsText, setTtsText] = useState('');
  const [ttsResult, setTtsResult] = useState<any>(null);
  const [newProfile, setNewProfile] = useState({ name: '', stt_engine: 'whisper', tts_engine: 'system', wake_word: 'helios' });
  const [profileBusy, setProfileBusy] = useState(false);

  const st = status.data ?? {};
  const s = stats.data ?? {};
  const c = caps.data ?? {};

  async function setMode(mode: string) {
    setBusy(true);
    setVoiceState(mode === 'always_listening' ? 'listening' : mode === 'push_to_talk' ? 'listening' : 'idle');
    try { await helios.voice.setMode({ mode }); status.reload(); }
    finally { setBusy(false); }
  }

  async function synthesize() {
    if (!ttsText.trim()) return;
    setBusy(true);
    setVoiceState('speaking');
    try {
      const r = await helios.voice.synthesize({ text: ttsText });
      setTtsResult(r);
    } finally {
      setBusy(false);
      setVoiceState('idle');
    }
  }

  async function simulateWake() {
    setVoiceState('listening');
    await helios.voice.wake({ keyword: 'helios', confidence: 0.98 });
    status.reload();
    setTimeout(() => setVoiceState('idle'), 1500);
  }

  async function createProfile() {
    if (!newProfile.name.trim()) return;
    setProfileBusy(true);
    try {
      await helios.voice.createProfile(newProfile);
      setNewProfile({ name: '', stt_engine: 'whisper', tts_engine: 'system', wake_word: 'helios' });
      profiles.reload();
    } finally { setProfileBusy(false); }
  }

  return (
    <Page title="Voice Center" subtitle="voice OS · speech recognition · text-to-speech · profiles"
      actions={<Button size="sm" onClick={() => { status.reload(); stats.reload(); }}>Refresh</Button>}
    >
      <div className="grid gap-3">
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Sessions" value={s.sessions ?? 0} accent />
          <MetricCard label="Turns" value={s.turns ?? 0} />
          <MetricCard label="Wake Events" value={s.wake_events ?? 0} />
          <MetricCard label="Profiles" value={s.profiles ?? 0} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Voice Status">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <VoiceVisualizer state={voiceState} />
                <span className="mono text-[10px] text-warmgray">Mode: {st.mode ?? '—'}</span>
              </div>
              <div className="flex gap-2 flex-wrap">
                {MODES.map((m) => (
                  <Button key={m} size="sm" variant={st.mode === m ? 'gold' : 'ghost'}
                    onClick={() => setMode(m)} disabled={busy}>
                    {m.replace('_', ' ')}
                  </Button>
                ))}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={simulateWake}>Simulate Wake</Button>
              </div>
              <div className="grid grid-cols-2 gap-2 mono text-[10px] text-warmgray">
                <span>STT: {st.stt_engine ?? '—'}</span>
                <span>TTS: {st.tts_engine ?? '—'}</span>
              </div>
            </div>
          </Panel>

          <Panel title="Text-to-Speech">
            <div className="flex flex-col gap-2">
              <textarea
                className="bg-obsidian border border-hairline rounded px-3 py-2 text-sm resize-none"
                rows={3}
                placeholder="Enter text to synthesize…"
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
              />
              <Button size="sm" variant="gold" onClick={synthesize} disabled={busy || !ttsText.trim()}>
                {busy ? 'Synthesizing…' : 'Synthesize'}
              </Button>
              {ttsResult && (
                <div className="mono text-[10px] text-warmgray space-y-0.5">
                  <div>Engine: {ttsResult.engine} · Voice: {ttsResult.voice}</div>
                  <div>Est. duration: {ttsResult.estimated_duration_sec}s</div>
                </div>
              )}
            </div>
          </Panel>
        </div>

        <Panel title="Voice Capabilities">
          {caps.loading ? <Loading /> : (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-1.5">STT Engines</div>
                <div className="flex flex-col gap-1">
                  {(c.stt_engines ?? []).map((e: string) => (
                    <div key={e} className={cls('flex items-center gap-2 text-[12px]',
                      st.stt_engine === e ? 'text-gold' : 'text-ivory/70')}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      {e}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-1.5">TTS Engines</div>
                <div className="flex flex-col gap-1">
                  {(c.tts_engines ?? []).map((e: string) => (
                    <div key={e} className={cls('flex items-center gap-2 text-[12px]',
                      st.tts_engine === e ? 'text-gold' : 'text-ivory/70')}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      {e}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="mono text-[9px] text-warmgray uppercase mb-1.5">Wake Words</div>
                <div className="flex flex-col gap-1">
                  {(c.wake_words ?? []).map((w: string) => (
                    <div key={w} className="text-[12px] text-ivory/70">{w}</div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Panel>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Voice Profiles">
            {profiles.loading ? <Loading /> : (
              <div className="flex flex-col gap-3">
                {(profiles.data ?? []).length === 0 ? (
                  <EmptyState message="No profiles yet. Create one below." />
                ) : (
                  <div className="flex flex-col gap-1.5">
                    {(profiles.data as any[]).map((p) => (
                      <div key={p.id} className={cls('flex items-center justify-between px-2.5 py-1.5 rounded border',
                        p.is_active ? 'border-gold/40 bg-gold/5' : 'border-hairline')}>
                        <div>
                          <div className="text-[12px]">{p.name}</div>
                          <div className="mono text-[10px] text-warmgray">{p.stt_engine} / {p.tts_engine} · {p.wake_word}</div>
                        </div>
                        {!p.is_active && (
                          <Button size="sm" variant="ghost" onClick={async () => {
                            await helios.voice.activateProfile(p.id);
                            profiles.reload();
                          }}>Activate</Button>
                        )}
                        {p.is_active && <span className="mono text-[10px] text-gold">active</span>}
                      </div>
                    ))}
                  </div>
                )}
                <div className="border-t border-hairline pt-3">
                  <div className="mono text-[9px] uppercase text-warmgray mb-2">New Profile</div>
                  <div className="flex flex-col gap-1.5">
                    <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      placeholder="Profile name" value={newProfile.name}
                      onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })} />
                    <div className="flex gap-1.5">
                      <select className="flex-1 border border-hairline bg-obsidian rounded px-2 text-xs"
                        value={newProfile.stt_engine}
                        onChange={(e) => setNewProfile({ ...newProfile, stt_engine: e.target.value })}>
                        {['whisper','faster_whisper','vosk','system'].map((e) => <option key={e}>{e}</option>)}
                      </select>
                      <select className="flex-1 border border-hairline bg-obsidian rounded px-2 text-xs"
                        value={newProfile.tts_engine}
                        onChange={(e) => setNewProfile({ ...newProfile, tts_engine: e.target.value })}>
                        {['piper','coqui','system'].map((e) => <option key={e}>{e}</option>)}
                      </select>
                    </div>
                    <input className="bg-obsidian border border-hairline rounded px-2 py-1 text-xs"
                      placeholder="Wake word (e.g. helios)" value={newProfile.wake_word}
                      onChange={(e) => setNewProfile({ ...newProfile, wake_word: e.target.value })} />
                    <Button size="sm" variant="gold" onClick={createProfile}
                      disabled={profileBusy || !newProfile.name.trim()}>
                      Create Profile
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Panel>

          <Panel title="Recent Sessions">
            {sessions.loading ? <Loading /> : (sessions.data as any[] ?? []).length === 0 ? (
              <EmptyState message="No voice sessions yet." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {(sessions.data as any[]).slice(0, 8).map((s: any) => (
                  <div key={s.id} className="flex items-center justify-between text-[12px]">
                    <span className="mono text-[10px] text-warmgray">
                      {new Date(s.started_at * 1000).toLocaleString()}
                    </span>
                    <span className="text-ivory/70">{s.turn_count} turns</span>
                    <span className={cls('mono text-[10px]', s.ended_at ? 'text-warmgray' : 'text-helgreen')}>
                      {s.ended_at ? 'ended' : 'active'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </Page>
  );
}
