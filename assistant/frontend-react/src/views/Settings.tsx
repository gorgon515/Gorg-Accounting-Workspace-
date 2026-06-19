import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, StatusBadge } from '../components';

function Toggle({ label, defaultOn, note }: { label: string; defaultOn?: boolean; note?: string }) {
  const [on, setOn] = useState(!!defaultOn);
  return (
    <div className="flex items-center justify-between py-2 border-b border-hairline">
      <div>
        <div className="text-[12px]">{label}</div>
        {note && <div className="text-[10px] text-warmgray/70">{note}</div>}
      </div>
      <button onClick={() => setOn((v) => !v)}
        className={`w-9 h-5 rounded-full p-0.5 transition-colors ${on ? 'bg-gold/70' : 'bg-slate'}`}>
        <span className={`block w-4 h-4 rounded-full bg-ivory transition-transform ${on ? 'translate-x-4' : ''}`} />
      </button>
    </div>
  );
}

function Field({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-hairline">
      <span className="text-[12px] text-warmgray">{label}</span>
      <span className="mono text-[11px] text-ivory">{value ?? '—'}</span>
    </div>
  );
}

export function Settings() {
  const cfg = useAsync(() => helios.config(), []);
  const side = useAsync(() => helios.sidecar.status(), []);
  const b = cfg.data?.brain;

  return (
    <Page title="Settings" subtitle="models · voice · memory · agents · security · integrations">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Panel title="Models" actions={<StatusBadge status={b?.ready ? 'ready' : 'offline'} label={b?.engine || '—'} />}>
          <Field label="Engine" value={b?.engine} />
          <Field label="Model" value={b?.model} />
          <Field label="Local (on-device)" value={b?.local ? 'yes' : 'no'} />
          <p className="text-[10px] text-warmgray/70 mt-2">Engine and model are set via env (BRAIN_ENGINE, OLLAMA_MODEL, ANTHROPIC_API_KEY).</p>
        </Panel>

        <Panel title="Voice">
          <Field label="STT engine" value={cfg.data?.stt?.engine} />
          <Field label="Wake word" value={cfg.data?.wakeWord} />
          <Toggle label="Interruptible speech (barge-in)" defaultOn />
          <Toggle label="Continuous listening" note="wake-word mode" />
        </Panel>

        <Panel title="Intelligence Sidecar">
          <Field label="Status" value={side.data?.ready ? 'ready' : 'offline'} />
          <Field label="URL" value={side.data?.url} />
          <Toggle label="Autostart on launch" defaultOn note="HELIOS_SIDECAR_AUTOSTART" />
        </Panel>

        <Panel title="Agents & Memory">
          <Toggle label="Show agent routing in Assistant" defaultOn />
          <Toggle label="Proactively save memories" defaultOn />
          <Toggle label="Log every tool call (Agent Activity)" defaultOn />
        </Panel>

        <Panel title="Security">
          <Field label="Renderer isolation" value="contextIsolation on" />
          <Field label="Secrets" value="OS keychain (safeStorage)" />
          <Toggle label="Require approval for money/send actions" defaultOn note="enforced — no execute tool exists" />
        </Panel>

        <Panel title="Appearance & Notifications">
          <Field label="Theme" value="HELIOS dark (obsidian/gold)" />
          <Toggle label="Reduced motion" note="also follows OS setting" />
          <Toggle label="Desktop notifications for alerts" defaultOn />
        </Panel>
      </div>
    </Page>
  );
}
