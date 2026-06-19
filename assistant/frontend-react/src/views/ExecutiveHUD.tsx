import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, MetricCard, Button, EmptyState, Loading, VoiceVisualizer } from '../components';
import type { VoiceState } from '../components';
import { cls } from '../lib/format';

const COMMANDS = [
  'Review today\'s priorities',
  'Open portfolio dashboard',
  'Create tax research memo',
  'Show market risks',
  'Plan my CPA study',
  'Open accounting workbench',
  'Review approval queue',
  'Generate executive briefing',
];

export function ExecutiveHUD() {
  if (!helios.hasBridge()) return <EmptyState message="Open in desktop app for the Executive HUD." />;

  const voiceStatus = useAsync(() => helios.voice.status(), [], 5000);
  const presenceState = useAsync(() => helios.presence.state(), [], 5000);
  const notifStats = useAsync(() => helios.notifications.stats(), [], 5000);
  const notifications = useAsync(() => helios.notifications.list({ status: 'unread', limit: '5' }), [], 10000);
  const ambientStats = useAsync(() => helios.ambient.stats(), [], 10000);
  const llmStats = useAsync(() => helios.llmRuntime.stats(), [], 15000);
  const desktopInfo = useAsync(() => helios.desktop.systemInfo(), [], 10000);
  const briefing = useAsync(() => helios.ambient.latestBriefing(), []);

  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [briefingBusy, setBriefingBusy] = useState(false);
  const [generatedBriefing, setGeneratedBriefing] = useState<any>(null);
  const [cmdInput, setCmdInput] = useState('');
  const [cmdResult, setCmdResult] = useState('');

  const vs = voiceStatus.data ?? {};
  const ps = presenceState.data ?? {};
  const ns = notifStats.data ?? {};
  const sys = desktopInfo.data ?? {};
  const as = ambientStats.data ?? {};

  async function generateBriefing() {
    setBriefingBusy(true);
    setVoiceState('thinking');
    try {
      const b = await helios.ambient.generateBriefing({});
      setGeneratedBriefing(b);
      setVoiceState('speaking');
      setTimeout(() => setVoiceState('idle'), 3000);
    } finally { setBriefingBusy(false); }
  }

  async function runCommand(cmd: string) {
    setCmdInput(cmd);
    setCmdResult('Processing…');
    await new Promise((r) => setTimeout(r, 500));
    const responses: Record<string, string> = {
      'Review today\'s priorities': 'Retrieving your top priorities for today from tasks, approvals, and research queue.',
      'Open portfolio dashboard': 'Navigating to Portfolio Command Center.',
      'Create tax research memo': 'Opening Tax & Advisory workbench with memo template.',
      'Show market risks': 'Loading Risk Center with live market signals.',
      'Plan my CPA study': 'Opening CPA Center with study plan generator.',
      'Open accounting workbench': 'Navigating to Accounting module.',
      'Review approval queue': 'Loading all pending approvals across HELIOS.',
      'Generate executive briefing': 'Generating your personalized morning briefing.',
    };
    setCmdResult(responses[cmd] || `Executing: ${cmd}`);
    if (cmd === 'Generate executive briefing') await generateBriefing();
  }

  return (
    <Page title="Executive HUD" subtitle="flagship command interface · voice · presence · intelligence">
      <div className="grid gap-3">
        {/* Top status bar */}
        <div className="grid grid-cols-6 gap-2">
          <MetricCard label="Voice Mode" value={((vs as any).mode || 'idle').toUpperCase()} accent />
          <MetricCard label="Presence" value={((ps as any).mode || '—').toUpperCase()} />
          <MetricCard label="Unread" value={(ns as any).unread ?? 0} />
          <MetricCard label="Alerts" value={(as as any).unacknowledged_alerts ?? 0} />
          <MetricCard label="LLM Models" value={(llmStats.data as any)?.total_models ?? 0} />
          <MetricCard label="CPU" value={`${Math.round((sys as any).cpu_percent || 0)}%`} />
        </div>

        {/* Primary HUD row */}
        <div className="grid grid-cols-3 gap-3">
          {/* Voice + Command */}
          <Panel title="Voice Interface">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <VoiceVisualizer state={voiceState} />
                <div className="text-right mono text-[10px] text-warmgray">
                  <div>STT: {(vs as any).stt_engine || '—'}</div>
                  <div>TTS: {(vs as any).tts_engine || '—'}</div>
                </div>
              </div>
              <div className="flex gap-1.5">
                <Button size="sm" variant={voiceState === 'listening' ? 'gold' : 'ghost'}
                  onClick={() => setVoiceState(voiceState === 'listening' ? 'idle' : 'listening')}>
                  {voiceState === 'listening' ? '⬛ Stop' : '⏺ Listen'}
                </Button>
                <Button size="sm" variant="ghost"
                  onClick={generateBriefing}
                  disabled={briefingBusy}>
                  {briefingBusy ? 'Briefing…' : '☀ Briefing'}
                </Button>
              </div>
              <div className="border-t border-hairline pt-2">
                <div className="mono text-[9px] text-warmgray uppercase mb-1.5">Command Palette</div>
                <input
                  className="w-full bg-obsidian border border-hairline rounded px-2 py-1.5 text-xs mb-1.5"
                  placeholder="Type a command…"
                  value={cmdInput}
                  onChange={(e) => setCmdInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') runCommand(cmdInput); }}
                />
                {cmdResult && (
                  <div className="text-[11px] text-gold px-1">{cmdResult}</div>
                )}
              </div>
            </div>
          </Panel>

          {/* Presence + Adaptive */}
          <Panel title="Presence & Context">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="text-gold text-lg">
                  {(ps as any).mode === 'market' ? '▤' : (ps as any).mode === 'study' ? '∞' : '⊛'}
                </span>
                <div>
                  <div className="text-[13px] capitalize">{(ps as any).mode || 'unknown'} mode</div>
                  {(ps as any).context?.task && (
                    <div className="text-[11px] text-warmgray">{(ps as any).context.task}</div>
                  )}
                </div>
              </div>
              {(ps as any).focus?.enabled && (
                <div className="px-2.5 py-1.5 rounded border border-gold/30 bg-gold/5">
                  <div className="mono text-[10px] text-gold">FOCUS ACTIVE</div>
                  {(ps as any).focus?.goal && (
                    <div className="text-[11px] text-ivory/80">{(ps as any).focus.goal}</div>
                  )}
                </div>
              )}
              {(ps as any).calendar?.status === 'in_meeting' && (
                <div className="px-2.5 py-1.5 rounded border border-helred/30 bg-helred/5">
                  <div className="mono text-[10px] text-helred">IN MEETING</div>
                  {(ps as any).calendar?.meeting_title && (
                    <div className="text-[11px]">{(ps as any).calendar.meeting_title}</div>
                  )}
                </div>
              )}
              <div className="border-t border-hairline pt-2 grid gap-1">
                {(ps as any).adaptive && Object.entries((ps as any).adaptive || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-[11px]">
                    <span className="text-warmgray">{k.replace(/_/g, ' ')}</span>
                    <span className="text-ivory/80">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          {/* Quick Commands */}
          <Panel title="Quick Commands">
            <div className="flex flex-col gap-1.5">
              {COMMANDS.map((cmd) => (
                <button key={cmd}
                  onClick={() => runCommand(cmd)}
                  className="w-full text-left px-2.5 py-1.5 rounded border border-hairline text-[12px] text-ivory/70 hover:text-ivory hover:bg-ivory/5 hover:border-gold/30 transition-colors">
                  {cmd}
                </button>
              ))}
            </div>
          </Panel>
        </div>

        {/* Bottom row: notifications + briefing + system */}
        <div className="grid grid-cols-3 gap-3">
          <Panel title="Recent Notifications">
            {notifications.loading ? <Loading /> : (notifications.data as any[] ?? []).length === 0 ? (
              <EmptyState message="No unread notifications." />
            ) : (
              <div className="flex flex-col gap-1.5">
                {(notifications.data as any[]).slice(0, 5).map((n: any) => (
                  <div key={n.id} className={cls('flex items-start gap-2 px-2 py-1.5 rounded border',
                    n.priority === 'critical' || n.priority === 'urgent' ? 'border-helred/30' : 'border-hairline')}>
                    <span className={cls('mono text-[9px] uppercase mt-0.5',
                      n.priority === 'critical' ? 'text-helred' :
                      n.priority === 'urgent' ? 'text-helred' :
                      n.priority === 'high' ? 'text-gold' : 'text-warmgray')}>
                      {n.priority}
                    </span>
                    <div className="min-w-0">
                      <div className="text-[12px] truncate">{n.title}</div>
                      {n.body && <div className="text-[10px] text-warmgray truncate">{n.body}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Morning Briefing">
            {generatedBriefing ? (
              <div className="flex flex-col gap-2">
                <div className="mono text-[10px] text-gold">
                  Generated · {generatedBriefing.word_count} words · {Object.keys(generatedBriefing.sections || {}).length} sections
                </div>
                <div className="text-[12px] text-ivory/90 leading-relaxed max-h-40 overflow-y-auto scroll-thin">
                  {generatedBriefing.voice_text?.slice(0, 400)}
                  {generatedBriefing.voice_text?.length > 400 && '…'}
                </div>
                <Button size="sm" variant="ghost" onClick={generateBriefing} disabled={briefingBusy}>
                  Regenerate
                </Button>
              </div>
            ) : briefing.data ? (
              <div className="flex flex-col gap-2">
                <div className="mono text-[10px] text-warmgray">
                  Last: {new Date(((briefing.data as any).generated_at || 0) * 1000).toLocaleString()}
                </div>
                <div className="text-[12px] text-ivory/80 leading-relaxed max-h-36 overflow-y-auto scroll-thin">
                  {(briefing.data as any).voice_text?.slice(0, 300)}…
                </div>
                <Button size="sm" variant="gold" onClick={generateBriefing} disabled={briefingBusy}>
                  {briefingBusy ? 'Generating…' : 'New Briefing'}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <EmptyState message="No briefing generated yet." />
                <Button size="sm" variant="gold" onClick={generateBriefing} disabled={briefingBusy}>
                  {briefingBusy ? 'Generating…' : 'Generate Briefing'}
                </Button>
              </div>
            )}
          </Panel>

          <Panel title="System Health">
            <div className="flex flex-col gap-2">
              {[
                { label: 'CPU', value: Math.round((sys as any).cpu_percent || 0) },
                { label: 'Memory', value: Math.round((sys as any).memory_percent || 0) },
                { label: 'Disk', value: Math.round((sys as any).disk_percent || 0) },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div className="flex justify-between mono text-[10px] text-warmgray mb-1">
                    <span>{label}</span><span>{value}%</span>
                  </div>
                  <div className="h-1 bg-obsidian rounded overflow-hidden">
                    <div className={cls('h-full rounded transition-all',
                      value > 85 ? 'bg-helred' : value > 65 ? 'bg-gold' : 'bg-helgreen')}
                      style={{ width: `${value}%` }} />
                  </div>
                </div>
              ))}
              <div className="border-t border-hairline pt-2 grid grid-cols-2 gap-1 mono text-[10px] text-warmgray">
                <div>Reminders: {(as as any).active_reminders ?? 0}</div>
                <div>Alerts: {(as as any).unacknowledged_alerts ?? 0}</div>
                <div>Briefings: {(as as any).briefings_generated ?? 0}</div>
                <div>Platform: {(sys as any).platform || '—'}</div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </Page>
  );
}
