import type { ReactNode } from 'react';
import { cls } from '../lib/format';
import { EmptyState } from './Empty';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  align?: 'left' | 'right';
  className?: string;
}

export function Table<T>({ columns, rows, empty = 'Nothing to show.', onRow }: {
  columns: Column<T>[];
  rows: T[];
  empty?: string;
  onRow?: (row: T) => void;
}) {
  if (!rows.length) return <EmptyState message={empty} />;
  return (
    <div className="overflow-x-auto scroll-thin">
      <table className="w-full text-[12px] border-collapse">
        <thead>
          <tr className="text-warmgray mono text-[10px] uppercase tracking-wider">
            {columns.map((c) => (
              <th key={c.key} className={cls('py-2 px-2 font-normal', c.align === 'right' ? 'text-right' : 'text-left')}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              onClick={() => onRow?.(row)}
              className={cls('border-t border-hairline', onRow && 'cursor-pointer hover:bg-ivory/5')}
            >
              {columns.map((c) => (
                <td key={c.key} className={cls('py-2 px-2', c.align === 'right' ? 'text-right tabular-nums' : '', c.className)}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
