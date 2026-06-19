import { ROUTES, type RouteGroup } from '../routes';
import { useNav } from '../router';
import { cls } from '../lib/format';

const GROUPS: RouteGroup[] = ['Core', 'Strategy', 'Finance', 'Knowledge', 'Operations', 'Learning', 'System'];

export function Sidebar() {
  const { active, navigate } = useNav();
  return (
    <nav className="w-[208px] shrink-0 h-full glass rounded-none border-l-0 border-t-0 border-b-0 flex flex-col">
      <div className="px-4 py-4 border-b border-hairline">
        <div className="flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-md bg-gold/20 border border-gold/40 flex items-center justify-center text-gold text-sm">☀</span>
          <div>
            <div className="mono text-[13px] tracking-[0.2em] text-ivory">HELIOS</div>
            <div className="mono text-[8px] tracking-[0.2em] text-warmgray">COMMAND CENTER</div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scroll-thin py-2">
        {GROUPS.map((g) => (
          <div key={g} className="mb-1.5">
            <div className="px-4 py-1 mono text-[9px] uppercase tracking-wider text-warmgray/60">{g}</div>
            {ROUTES.filter((r) => r.group === g).map((r) => (
              <button
                key={r.id}
                onClick={() => navigate(r.id)}
                className={cls(
                  'w-full flex items-center gap-2.5 px-4 py-1.5 text-[12.5px] transition-colors relative',
                  active === r.id ? 'text-gold bg-gold/10' : 'text-ivory/70 hover:text-ivory hover:bg-ivory/5',
                )}
              >
                {active === r.id && <span className="absolute left-0 top-1 bottom-1 w-0.5 bg-gold rounded-r" />}
                <span className="w-4 text-center opacity-80">{r.icon}</span>
                {r.label}
              </button>
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}
