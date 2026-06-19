import type { ReactNode } from 'react';
import { motion } from 'framer-motion';

// Standard page scaffold: animated, scrollable workspace with a header.
export function Page({ title, subtitle, actions, children }: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="h-full overflow-y-auto scroll-thin"
    >
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-lg font-light tracking-wide">{title}</h1>
          {subtitle && <p className="mono text-[11px] text-warmgray mt-0.5">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children}
    </motion.div>
  );
}

export const grid = 'grid gap-3';
