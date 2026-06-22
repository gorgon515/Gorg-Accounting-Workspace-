import { useState } from 'react';
import { Page } from './_page';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { Panel, Button, Loading } from '../components';
import { cls } from '../lib/format';

// Integrations — enter and persist the live-data / brokerage / TTS API keys.
// Keys are written to ~/.helios/config.json by the sidecar and applied live, so
// a packaged desktop app picks them up regardless of how it was launched.
const FIELDS: { key: string; label: string; group: string; secret: boolean; placeholder: string; help?: string }[] = [
  { key: 'TRADINGVIEW_RAPIDAPI_KEY', label: 'TradingView RapidAPI Key', group: 'TradingView', secret: true, placeholder: 'x-rapidapi-key', help: 'From your RapidAPI dashboard for the TradingView Data API.' },
  { key: 'ELEVENLABS_API_KEY', label: 'ElevenLabs API Key', group: 'ElevenLabs', secret: true, placeholder: 'sk_…', help: 'ElevenLabs → Profile → API Keys.' },
  { key: 'ROBINHOOD_USERNAME', label: 'Robinhood Username / Email', group: 'Robinhood', secret: false, placeholder: 'you@example.com' },
  { key: 'ROBINHOOD_PASSWORD', label: 'Robinhood Password', group: 'Robinhood', secret: true, placeholder: '••••••••' },
  { key: 'ROBINHOOD_MFA_CODE', label: 'Robinhood MFA Secret (optional)', group: 'Robinhood', secret: true, placeholder: 'TOTP secret', help: 'Optional — the authenticator secret used to auto-generate 2FA codes.' },
];

const GROUPS = ['TradingView', 'ElevenLabs', 'Robinhood'];

export function Integrations() {
  const keys = useAsync(() => helios.settings.getKeys(), []);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const status: Record<string, any> = keys.data?.status ?? {};
  const configFile: string = keys.data?.config_file ?? '~/.helios/config.json';

  async function save() {
    setSaving(true);
    try {
      // Only send fields the user actually typed into (non-empty draft entries,
      // or explicit clears). Untouched fields are left as-is.
      const payload: Record<string, string> = {};
      for (const [k, v] of Object.entries(draft)) {
        if (v !== undefined) payload[k] = v;
      }
      if (Object.keys(payload).length === 0) { setSaving(false); return; }
      await helios.settings.setKeys(payload);
      setDraft({});
      setSavedAt(new Date().toLocaleTimeString());
      keys.reload();
    } finally { setSaving(false); }
  }

  const dirty = Object.values(draft).some((v) => v !== undefined && v !== '');

  return (
    <Page title="Integrations" subtitle="API keys for TradingView · ElevenLabs · Robinhood"
      actions={
        <Button size="sm" variant="gold" onClick={save} disabled={!dirty || saving}>
          {saving ? 'Saving…' : 'Save Keys'}
        </Button>
      }>
      <div className="grid gap-3">
        <div className="px-3 py-2.5 rounded border border-hairline bg-ivory/5">
          <p className="text-[12px] text-ivory/80">
            Keys are stored locally in <span className="mono text-gold">{configFile}</span> and applied immediately —
            no restart needed. They never leave your machine.
          </p>
          {savedAt && <p className="mono text-[10px] text-helgreen mt-1">Saved at {savedAt}.</p>}
        </div>

        {keys.loading ? <Loading /> : GROUPS.map((group) => {
          const fields = FIELDS.filter((f) => f.group === group);
          const configured = fields
            .filter((f) => f.key !== 'ROBINHOOD_MFA_CODE')
            .every((f) => status[f.key]?.configured);
          return (
            <Panel key={group} title={group}
              subtitle={configured ? 'configured' : 'not configured'}
              actions={
                <span className={cls('mono text-[10px] px-2 py-0.5 rounded',
                  configured ? 'text-helgreen bg-helgreen/10' : 'text-warmgray bg-ivory/5')}>
                  {configured ? '● live' : '○ inactive'}
                </span>
              }>
              <div className="grid gap-2.5">
                {fields.map((f) => {
                  const st = status[f.key] ?? {};
                  return (
                    <div key={f.key} className="grid gap-1">
                      <div className="flex items-center gap-2">
                        <label className="text-[11px] text-ivory/80">{f.label}</label>
                        {st.configured && (
                          <span className="mono text-[9px] text-helgreen">
                            set{f.secret && st.hint ? ` · ${st.hint}` : ''}
                          </span>
                        )}
                      </div>
                      <input
                        type={f.secret ? 'password' : 'text'}
                        className="w-full bg-obsidian border border-hairline rounded px-2.5 py-1.5 text-[12px] mono focus:border-gold/40 outline-none"
                        placeholder={st.configured ? '•••••• (saved — type to replace)' : f.placeholder}
                        value={draft[f.key] ?? ''}
                        onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                      />
                      {f.help && <p className="text-[10px] text-warmgray">{f.help}</p>}
                    </div>
                  );
                })}
              </div>
            </Panel>
          );
        })}

        <Panel title="How keys reach the app">
          <ul className="grid gap-1.5 text-[11px] text-ivory/70">
            <li className="flex gap-1.5"><span className="text-gold">•</span>
              Saved here, keys are written to <span className="mono">~/.helios/config.json</span> and loaded by the
              backend on every launch — so a double-clicked desktop app sees them even though it can't read your shell's
              environment variables.</li>
            <li className="flex gap-1.5"><span className="text-gold">•</span>
              You can also set them as OS environment variables; explicit env vars take precedence over this file.</li>
            <li className="flex gap-1.5"><span className="text-gold">•</span>
              Robinhood orders always require explicit in-app approval before execution — keys alone never auto-trade.</li>
          </ul>
        </Panel>
      </div>
    </Page>
  );
}
