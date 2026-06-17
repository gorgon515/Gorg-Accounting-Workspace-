import { useEffect, useState } from 'react';
import { useAsync } from '../hooks/useAsync';
import { helios } from '../ipc/client';
import { StatusBadge } from '../components';
import { ROUTE_BY_ID } from '../routes';
import { useNav } from '../router';

export function Topbar() {
  const { active } = useNav();
  const cfg = useAsync(() => helios.config(), []);
  const side = useAsync(() => helios.sidecar.status(), [], 15000);
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const brainReady = cfg.data?.brain?.ready;
  const title = ROUTE_BY_ID[active]?.label ?? 'HELIOS';

  return (
    <header className="h-12 shrink-0 flex items-center justify-between px-5 border-b border-hairline">
      <div className="flex items-center gap-3">
        <span className="text-[13px] tracking-wide text-ivory">{title}</span>
        <span className="w-px h-4 bg-hairline" />
        <span className="mono text-[10px] text-warmgray">{clock.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
      </div>
      <div className="flex items-center gap-4">
        <StatusBadge status={brainReady ? 'online' : 'offline'}
          label={brainReady ? `brain · ${cfg.data?.brain?.local ? 'local' : 'cloud'}` : 'brain offline'} />
        <StatusBadge status={side.data?.ready ? 'online' : 'idle'} label={side.data?.ready ? 'sidecar' : 'sidecar idle'} />
        <span className="mono text-[11px] text-gold tabular-nums">{clock.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    </header>
  );
}
