// Small formatting / className helpers shared across the HUD.

/** Join class names, dropping falsy values (classnames-lite). */
export function cls(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

/** Format a number as USD currency. Accepts numbers or numeric strings. */
export function fmtMoney(value: number | string | null | undefined, currency = 'USD'): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (n == null || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: Math.abs(n) >= 1000 ? 0 : 2,
  }).format(n);
}

/** Format a ratio/percentage. Pass a fraction (0.12) by default, or a whole pct with asWhole. */
export function fmtPct(value: number | null | undefined, asWhole = false): string {
  if (value == null || Number.isNaN(value)) return '—';
  const pct = asWhole ? value : value * 100;
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

/** Tailwind text color reflecting the sign of a number (gain/loss/flat). */
export function dirColor(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) return 'text-warmgray';
  return value > 0 ? 'text-helgreen' : 'text-helred';
}

/** Human-friendly relative time from an ISO string, epoch ms, or Date. */
export function timeAgo(ts: string | number | Date | null | undefined): string {
  if (ts == null) return '—';
  const then = ts instanceof Date ? ts.getTime() : typeof ts === 'number' ? ts : Date.parse(ts);
  if (Number.isNaN(then)) return '—';
  const secs = Math.round((Date.now() - then) / 1000);
  if (secs < 0) return 'in the future';
  if (secs < 45) return 'just now';
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.round(months / 12)}y ago`;
}
