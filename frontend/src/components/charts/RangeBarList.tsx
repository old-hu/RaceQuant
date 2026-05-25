import type { ReactNode } from "react";

type RangeBarItem = {
  key: string | number;
  value: number;
  leading: ReactNode;
  trailing: ReactNode;
};

type RangeBarListProps = {
  items: RangeBarItem[];
  baseline?: number;
};

export function RangeBarList({ items, baseline }: RangeBarListProps) {
  if (!items.length) return null;

  const values = baseline == null ? items.map((item) => item.value) : [baseline, ...items.map((item) => item.value)];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const width = 10 + ((item.value - min) / span) * 90;
        return (
          <div key={item.key} className="grid gap-2 sm:grid-cols-[96px_minmax(0,1fr)_96px] sm:items-center">
            <div className="text-sm text-charcoal">{item.leading}</div>
            <div className="h-3 overflow-hidden rounded-full bg-surface-deep">
              <div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} />
            </div>
            <div className="text-sm text-ink sm:text-right">{item.trailing}</div>
          </div>
        );
      })}
    </div>
  );
}
