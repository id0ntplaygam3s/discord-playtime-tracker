import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RankedPlaytime } from '../types';
import { formatDuration } from '../utils/time';

const truncate = (label: string, max = 22) => (label.length <= max ? label : `${label.slice(0, max - 1)}...`);

interface TopUsersChartProps {
  data: RankedPlaytime[];
  title?: string;
  height?: number;
}

export default function TopUsersChart({ data, title = 'Most Active Players', height = 320 }: TopUsersChartProps) {
  const yAxisWidth = Math.min(
    280,
    Math.max(
      140,
      data.reduce((max, row) => Math.max(max, Math.min(row.name.length, 36) * 7), 140)
    )
  );

  return (
    <div className="panel">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={yAxisWidth} stroke="#67E8F9" tickFormatter={(v) => truncate(String(v))} />
          <Tooltip
            formatter={(value: number) => formatDuration(value)}
            labelFormatter={(label) => String(label)}
            contentStyle={{ background: '#0b1117', border: '1px solid #1f2937' }}
          />
          <Bar dataKey="total_seconds" fill="#22D3EE" radius={[6, 6, 6, 6]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
