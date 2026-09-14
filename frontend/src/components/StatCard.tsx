interface Props {
  label: string;
  value: string;
  accent?: 'red' | 'blue' | 'green';
}

export default function StatCard({ label, value, accent = 'blue' }: Props) {
  return (
    <div className={`stat-card accent-${accent}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
