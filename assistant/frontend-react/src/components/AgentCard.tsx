import type { AgentRosterItem } from '../ipc/types';
import { StatusBadge } from './StatusBadge';

export function AgentCard({ agent, onClick, active }: { agent: AgentRosterItem; onClick?: () => void; active?: boolean }) {
  return (
    <button
      onClick={onClick}
      title={agent.role}
      className={`w-full text-left glass p-3 transition-colors ${active ? 'border-gold/50' : 'hover:border-gold/25'}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium truncate">{agent.name}</span>
        <StatusBadge status={agent.status} label={agent.status === 'planned' ? 'planned' : `${agent.tools} tools`} />
      </div>
      <p className="mt-1 text-[11px] text-warmgray line-clamp-2 leading-snug">{agent.role}</p>
      {agent.permissions && (
        <div className="mt-2 flex gap-1.5 mono text-[9px] text-warmgray/80">
          <span className="px-1.5 py-0.5 rounded border border-hairline">mem: {agent.permissions.memory}</span>
          {agent.permissions.canPropose && (
            <span className="px-1.5 py-0.5 rounded border border-hairline">can propose</span>
          )}
        </div>
      )}
    </button>
  );
}
