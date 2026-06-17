import { useMemo } from 'react';

// Dependency-free SVG line/area chart. Good enough for sparklines, price series,
// and progress curves without pulling in a charting library (smaller, safer build).
export function Chart({
  data, height = 80, stroke = '#B8976A', fill = true, className,
}: {
  data: number[];
  height?: number;
  stroke?: string;
  fill?: boolean;
  className?: string;
}) {
  const W = 300;
  const { line, area, up } = useMemo(() => {
    if (!data || data.length < 2) return { line: '', area: '', up: true };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const span = max - min || 1;
    const dx = W / (data.length - 1);
    const pts = data.map((v, i) => [i * dx, height - ((v - min) / span) * (height - 6) - 3]);
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
    const area = `${line} L${W},${height} L0,${height} Z`;
    return { line, area, up: data[data.length - 1] >= data[0] };
  }, [data, height]);

  const color = stroke === 'auto' ? (up ? '#6FA98C' : '#C97A6A') : stroke;

  if (!line) return <div className="text-[11px] text-warmgray py-4 text-center">No series data.</div>;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" className={className} style={{ width: '100%', height }}>
      {fill && (
        <>
          <defs>
            <linearGradient id="chartfill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.22" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#chartfill)" />
        </>
      )}
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}
