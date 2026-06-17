import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Button } from './Button';

export function Drawer({ open, onClose, title, children, side = 'right' }: {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  side?: 'left' | 'right';
}) {
  const x = side === 'right' ? '100%' : '-100%';
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.aside
            className={`absolute top-0 ${side === 'right' ? 'right-0' : 'left-0'} h-full w-[min(420px,90vw)] glass rounded-none shadow-hud flex flex-col`}
            initial={{ x }}
            animate={{ x: 0 }}
            exit={{ x }}
            transition={{ type: 'tween', duration: 0.25 }}
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between px-4 py-3 border-b border-hairline">
              <h3 className="text-sm font-medium">{title}</h3>
              <Button size="sm" onClick={onClose}>✕</Button>
            </header>
            <div className="p-4 overflow-y-auto scroll-thin">{children}</div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
