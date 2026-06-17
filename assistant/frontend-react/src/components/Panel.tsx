import type { ReactNode } from 'react';
import { cls } from '../lib/format';

// A titled section surface with an optional action slot and a scrollable body.
export function Panel({
  title, subtitle, actions, children, className, bodyClass, scroll,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
  scroll?: boolean;
}) {
  return (
    <section className={cls('glass flex flex-col min-h-0', className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-hairline">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-medium tracking-wide truncate">{title}</h2>}
            {subtitle && <p className="mono text-[10px] text-warmgray mt-0.5 truncate">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-1.5 shrink-0">{actions}</div>}
        </header>
      )}
      <div className={cls('p-4 min-h-0', scroll && 'overflow-y-auto scroll-thin', bodyClass)}>{children}</div>
    </section>
  );
}
