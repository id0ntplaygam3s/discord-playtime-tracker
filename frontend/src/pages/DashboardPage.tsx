import { useMemo, useState } from 'react';
import ActivityLineChart from '../charts/ActivityLineChart';
import TopGamesChart from '../charts/TopGamesChart';
import TopUsersChart from '../charts/TopUsersChart';
import CurrentSessions from '../components/CurrentSessions';
import StatCard from '../components/StatCard';
import { useDashboardData } from '../hooks/useDashboardData';
import { SourceFilter } from '../types';
import { formatDuration } from '../utils/time';

export default function DashboardPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [source, setSource] = useState<SourceFilter>('combined');
  const { overview, games, users, daily, active, loading, error } = useDashboardData(guildId, source);

  const totalDisplay = useMemo(() => {
    if (!overview) return '0h';
    return formatDuration(overview.total_combined_seconds);
  }, [overview]);

  if (loading) return <div className="panel">Loading dashboard...</div>;
  if (error) return <div className="panel error-box">{error}</div>;
  if (!overview) return <div className="panel">No data available.</div>;

  return (
    <div className="page-grid">
      <header className="top-row">
        <div>
          <h2>Discord Game Activity</h2>
          <p className="subtle">Observed sessions + historical + adjustments</p>
        </div>
        <div className="filters">
          <label>Data source</label>
          <select value={source} onChange={(e) => setSource(e.target.value as SourceFilter)}>
            <option value="combined">Combined</option>
            <option value="automatic">Automatic</option>
            <option value="historical">Historical</option>
            <option value="adjustments">Adjustments</option>
          </select>
        </div>
      </header>

      <section className="stat-grid">
        <StatCard label="Total Combined" value={totalDisplay} accent="red" />
        <StatCard label="Tracked Users" value={String(overview.tracked_users)} accent="blue" />
        <StatCard label="Games" value={String(overview.games)} accent="green" />
        <StatCard label="Playing Now" value={String(overview.currently_playing)} accent="blue" />
      </section>

      <section className="two-col">
        <TopGamesChart data={games} />
        <TopUsersChart data={users} />
      </section>

      <section className="two-col">
        <ActivityLineChart data={daily} />
        <CurrentSessions sessions={active} />
      </section>
    </div>
  );
}
