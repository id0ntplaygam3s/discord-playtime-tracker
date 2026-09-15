import dayjs from 'dayjs';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { TimeBucketPoint } from '../types';
import { formatDuration } from '../utils/time';

interface ActivityLineChartProps {
  data: TimeBucketPoint[];
  title?: string;
  height?: number;
  frameless?: boolean;
  showDateAxis?: boolean;
}

export default function ActivityLineChart({ data, title = 'Activity Over Time', height = 280, frameless = false, showDateAxis = true }: ActivityLineChartProps) {
  const mapped = data.map((d) => ({
    ...d,
    label: dayjs(d.bucket).format('DD MMM'),
  }));

  const chart = (
    <>
      {title ? <h3>{title}</h3> : null}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={mapped}>
          <CartesianGrid strokeDasharray="4 4" stroke="#1F2937" />
          <XAxis dataKey="label" stroke="#94A3B8" hide={!showDateAxis} />
          <YAxis stroke="#94A3B8" width={88} tickFormatter={(value) => formatDuration(Number(value || 0))} />
          <Tooltip formatter={(value: number) => [formatDuration(value), 'Total play time']} />
          <Line type="monotone" dataKey="total_seconds" stroke="#F97316" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </>
  );

  if (frameless) return chart;
  return <div className="panel panel-chart">{chart}</div>;
}
