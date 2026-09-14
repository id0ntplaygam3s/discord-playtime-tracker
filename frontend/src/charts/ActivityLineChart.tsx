import dayjs from 'dayjs';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { TimeBucketPoint } from '../types';
import { formatDuration } from '../utils/time';

export default function ActivityLineChart({ data }: { data: TimeBucketPoint[] }) {
  const mapped = data.map((d) => ({
    ...d,
    label: dayjs(d.bucket).format('DD MMM'),
  }));

  return (
    <div className="panel">
      <h3>Activity Over Time</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={mapped}>
          <CartesianGrid strokeDasharray="4 4" stroke="#1F2937" />
          <XAxis dataKey="label" stroke="#94A3B8" />
          <YAxis stroke="#94A3B8" />
          <Tooltip formatter={(value: number) => [formatDuration(value), 'Total play time']} />
          <Line type="monotone" dataKey="total_seconds" stroke="#F97316" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
