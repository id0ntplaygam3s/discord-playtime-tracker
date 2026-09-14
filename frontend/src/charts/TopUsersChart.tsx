import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RankedPlaytime } from '../types';
import { formatDuration } from '../utils/time';

export default function TopUsersChart({ data }: { data: RankedPlaytime[] }) {
  return (
    <div className="panel">
      <h3>Most Active Players</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 48, bottom: 8 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={120} stroke="#67E8F9" />
          <Tooltip formatter={(value: number) => formatDuration(value)} />
          <Bar dataKey="total_seconds" fill="#22D3EE" radius={[6, 6, 6, 6]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
