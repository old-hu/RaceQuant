type LineChartProps = {
  values: number[];
  className?: string;
  strokeClassName?: string;
  width?: number;
  height?: number;
};

export function LineChart({
  values,
  className = "h-40 w-full overflow-visible",
  strokeClassName = "text-accent-blue",
  width = 320,
  height = 140,
}: LineChartProps) {
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(0.0001, max - min);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(1, values.length - 1)) * width;
      const y = height - ((value - min) / span) * (height - 16) - 8;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg className={className} preserveAspectRatio="none" viewBox={`0 0 ${width} ${height}`}>
      <polyline
        className={strokeClassName}
        fill="none"
        points={points}
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="3"
      />
    </svg>
  );
}
