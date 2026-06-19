import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { cls } from '../lib/format';

type Variant = 'primary' | 'ghost' | 'danger' | 'gold';
type Size = 'sm' | 'md';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-gold/15 text-gold border-gold/40 hover:bg-gold/25',
  ghost: 'bg-transparent text-ivory/80 border-hairline hover:bg-ivory/5',
  danger: 'bg-helred/10 text-helred border-helred/40 hover:bg-helred/20',
  gold: 'bg-gold text-obsidian border-gold hover:opacity-90',
};

export function Button({
  children, variant = 'ghost', size = 'md', onClick, type = 'button', disabled, title, className,
}: {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  onClick?: () => void;
  type?: 'button' | 'submit';
  disabled?: boolean;
  title?: string;
  className?: string;
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={cls(
        'inline-flex items-center justify-center gap-1.5 rounded-lg border font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
        size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-sm',
        VARIANTS[variant],
        className,
      )}
    >
      {children}
    </motion.button>
  );
}
