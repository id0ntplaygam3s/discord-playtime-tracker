import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RankedPlaytime } from '../types';
import { formatDuration } from '../utils/time';

const truncate = (label: string, max = 22) => (label.length <= max ? label : `${label.slice(0, max - 1)}...`);
const formatLabelDuration = (value: unknown) => formatDuration(Number(value || 0));

interface TopUsersChartProps {
  data: RankedPlaytime[];
  title?: string;
  height?: number;
  showValues?: boolean;
  barColor?: string;
  rowColorsByName?: Record<string, string>;
  frameless?: boolean;
}

export default function TopUsersChart({
  data,
  title = 'Most Active Players',
  height = 320,
  showValues = false,
  barColor = '#22D3EE',
  rowColorsByName,
  frameless = false,
}: TopUsersChartProps) {
  const yAxisWidth = Math.min(
    280,
    Math.max(
      140,
      data.reduce((max, row) => Math.max(max, Math.min(row.name.length, 36) * 7), 140)
    )
  );

  const chart = (
    <>
      {title ? <h3>{title}</h3> : null}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={yAxisWidth} stroke="#67E8F9" tickFormatter={(v) => truncate(String(v))} />
          <Tooltip
            formatter={(value: number) => [formatDuration(value), 'Total play time']}
            labelFormatter={(label) => String(label)}
            contentStyle={{ background: '#0b1117', border: '1px solid #1f2937' }}
          />
          <Bar dataKey="total_seconds" fill={barColor} radius={[6, 6, 6, 6]}>
            {data.map((row) => (
              <Cell key={`user-${row.id}`} fill={rowColorsByName?.[row.name] || barColor} />
            ))}
            {showValues && (
              <LabelList dataKey="total_seconds" position="right" formatter={formatLabelDuration} fill="#cbd5e1" />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>
  );

  if (frameless) return chart;
  return <div className="panel">{chart}</div>;
}
