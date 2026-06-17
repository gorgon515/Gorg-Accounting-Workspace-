import { motion } from 'framer-motion';
import { cls } from '../lib/format';

export type VoiceState = 'idle' | 'listening' | 'thinking' | 'speaking';

const COLOR: Record<VoiceState, string> = {
  idle: '#8C8880',
  listening: '#6FA98C',
  thinking: '#B8976A',
  speaking: '#F2EDE4',
};

const LABEL: Record<VoiceState, string> = {
  idle: 'Idle',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Speaking',
};

// Animated equalizer that reflects the voice/agent state. Bars are still when
// idle and animate with different cadences per state.
export function VoiceVisualizer({ state = 'idle', size = 'md' }: { state?: VoiceState; size?: 'sm' | 'md' }) {
  const bars = 5;
  const active = state !== 'idle';
  const color = COLOR[state];
  const h = size === 'sm' ? 18 : 28;

  return (
    <div className="inline-flex items-center gap-2">
      <div className="flex items-end gap-[3px]" style={{ height: h }} aria-label={`voice ${state}`}>
        {Array.from({ length: bars }).map((_, i) => (
          <motion.span
            key={i}
            style={{ background: color, width: size === 'sm' ? 2.5 : 3.5, borderRadius: 4 }}
            animate={
              active
                ? { height: [h * 0.25, h * (0.5 + (i % 3) * 0.25), h * 0.25] }
                : { height: h * 0.22 }
            }
            transition={
              active
                ? { duration: state === 'thinking' ? 0.5 : 0.8, repeat: Infinity, delay: i * 0.08, ease: 'easeInOut' }
                : { duration: 0.2 }
            }
          />
        ))}
      </div>
      <span className={cls('mono text-[10px] uppercase tracking-wider', active ? 'text-ivory' : 'text-warmgray')}>
        {LABEL[state]}
      </span>
    </div>
  );
}
