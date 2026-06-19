import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cls } from '../lib/format';

export function Card({ children, className, hover }: { children: ReactNode; className?: string; hover?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cls('glass p-4', hover && 'hover:border-gold/30 transition-colors', className)}
    >
      {children}
    </motion.div>
  );
}
