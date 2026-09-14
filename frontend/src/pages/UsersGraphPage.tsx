import { useEffect, useMemo, useState } from 'react';
import TopUsersChart from '../charts/TopUsersChart';
import { getTopUsers } from '../api/trackerApi';
import { RankedPlaytime } from '../types';
import { formatDuration } from '../utils/time';

export default function UsersGraphPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<RankedPlaytime[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTopUsers(guildId, 'combined', 30);
        if (!cancelled) setRows(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.response?.data?.detail || 'Failed to load users graph');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [guildId]);

  const totalSeconds = useMemo(() => rows.reduce((sum, row) => sum + row.total_seconds, 0), [rows]);
  const topUser = rows[0];

  return (
    <div className="page-grid">
      <header className="panel graph-hero graph-hero-users">
        <div>
          <h2>User Activity (Graph)</h2>
          <p className="subtle">A large comparison view of combined user activity and playtime totals.</p>
        </div>
        <div className="graph-stats">
          <div>
            <span className="subtle">Users Compared</span>
            <strong>{rows.length}</strong>
          </div>
          <div>
            <span className="subtle">Total Playtime</span>
            <strong>{formatDuration(totalSeconds)}</strong>
          </div>
          <div>
            <span className="subtle">Most Active User</span>
            <strong>{topUser ? topUser.name : 'N/A'}</strong>
          </div>
        </div>
      </header>

      {loading && <div className="panel">Loading users graph...</div>}
      {error && <div className="error-box">{error}</div>}

      {!loading && !error && (
        <TopUsersChart
          data={rows}
          title="All Users Activity Comparison"
          height={Math.max(460, Math.min(980, rows.length * 30 + 120))}
        />
      )}
    </div>
  );
}